"""Diablo II: Resurrected compiled shaders (`hd/shaders/*.bin`, 162 files in build 3.4.95041).

A file is one shader in every variant the game needs: a list of compile-time
switches and one Direct3D 11 program (DXBC, shader model 5.0) per combination.
Nested chunks, little endian; every chunk starts with the same 28 bytes:

  char[4] tag, u32 (the tag again, or a number), u32 count, u32, u32 header size,
  u32 offset of the data (from the chunk start), u32 size of the whole chunk

  SHAD                      the file
    TXT[   count strings    u32 offsets, then zero-ended text: switch names and their values
    SYM[   count switches
      SYM   one switch      second word = string number of its name; data = string numbers of its values
    SHMD  (second word 4)
      PRM[ count programs   u32 offsets (from the data start), then one BTCD each.
                            count = the product of the switches' value counts; program number =
                            value index of the first switch + its count x (value index of the second
                            + ...). Checked on the count in all 162 files; the order was read off
                            vs_models_v (program 1 is the one with vertex colours and no skinning).
        BTCD  one program   header 36 bytes, then 14 x u32 (masks of what the program uses; not
                            decoded), u32 size of the code, u32 4, then the DXBC container

What the model pixel shader (ps_models_p) does with a normal map, read from its
disassembly on 2026-11-26: x = alpha * 2 - 1, y = green * 2 - 1, and
  normal = x * T + y * (T.w * cross(T, N)) + N
with N and T the vertex normal and tangent. The models store T.w so that
cross(N, T) * T.w runs along +v (down the picture), so green = +1 leans the
normal UP the picture: the maps are "green up" (OpenGL style), which is also
what the stock maps measure as (see HdTexture.py). For back faces N is negated
and T.w is multiplied by a per-object sign first.

usage:
  HdShader.py info    <file> [--game <D2R folder>]
  HdShader.py extract <file> <out folder> [--game <D2R folder>]        one .dxbc per program
  HdShader.py disasm  <file> <out.asm> [--set NAME=VALUE ...] [--game <D2R folder>]
`disasm` needs Windows (d3dcompiler_47.dll); switches not named with --set take their first value.
"""
import argparse
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from HdPhysics import load  # noqa: E402


def _chunk(data, at):
    tag, second, count, _, head, body, size = struct.unpack_from('<4sI5I', data, at)
    return tag, second, count, head, body, size


def read(data):
    """-> {'switches': [(name, [values])], 'programs': [DXBC bytes], 'usage': [14 u32 per program]}"""
    if data[:8] != b'SHADSHAD':
        raise ValueError('not a shader file')
    at = _chunk(data, 0)[3]
    tag, _, count, head, body, size = _chunk(data, at)
    if tag != b'TXT[':
        raise ValueError('no TXT[ chunk')
    offsets = struct.unpack_from(f'<{count}I', data, at + head)
    text = [data[at + body + o:data.index(b'\0', at + body + o)].decode('latin1') for o in offsets]
    at += size
    tag, _, count, head, body, size = _chunk(data, at)
    if tag != b'SYM[':
        raise ValueError('no SYM[ chunk')
    switches, p = [], at + body
    for _ in range(count):
        _, name, values, _, sbody, ssize = _chunk(data, p)
        switches.append((text[name], [text[v] for v in struct.unpack_from(f'<{values}I', data, p + sbody)]))
        p += ssize
    at += size
    tag, _, _, head, _, _ = _chunk(data, at)
    if tag != b'SHMD':
        raise ValueError('no SHMD chunk')
    at += head
    tag, _, count, head, body, _ = _chunk(data, at)
    if tag != b'PRM[':
        raise ValueError('no PRM[ chunk')
    programs, usage = [], []
    for offset in struct.unpack_from(f'<{count}I', data, at + head):
        p = at + body + offset
        if data[p:p + 4] != b'BTCD':
            raise ValueError('no BTCD chunk')
        words = struct.unpack_from('<16I', data, p + 28)
        start = p + 28 + 60 + words[15]
        code = data[start:start + words[14]]
        if code[:4] != b'DXBC' or struct.unpack_from('<I', code, 24)[0] != len(code):
            raise ValueError('a program is not a whole DXBC container')
        programs.append(code)
        usage.append(words[:14])
    return {'switches': switches, 'programs': programs, 'usage': usage}


def settings(switches, index):
    """The value of every switch for program number `index`."""
    out = {}
    for name, values in switches:
        out[name] = values[index % len(values)]
        index //= len(values)
    return out


def program_number(switches, chosen):
    index, step = 0, 1
    for name, values in switches:
        value = chosen.get(name, values[0])
        if value not in values:
            raise SystemExit(f'{name} has no value {value} (it has {", ".join(values)})')
        index += values.index(value) * step
        step *= len(values)
    unknown = set(chosen) - {name for name, _ in switches}
    if unknown:
        raise SystemExit('no such switch: ' + ', '.join(sorted(unknown)))
    return index


def disassemble(code):
    import ctypes
    compiler = ctypes.WinDLL('d3dcompiler_47.dll')
    blob = ctypes.c_void_p()
    result = compiler.D3DDisassemble(ctypes.c_char_p(code), ctypes.c_size_t(len(code)), 0, None, ctypes.byref(blob))
    if result != 0:
        raise RuntimeError('D3DDisassemble failed: %08X' % (result & 0xFFFFFFFF))
    table = ctypes.cast(ctypes.cast(blob, ctypes.POINTER(ctypes.c_void_p))[0], ctypes.POINTER(ctypes.c_void_p))
    pointer = ctypes.WINFUNCTYPE(ctypes.c_void_p, ctypes.c_void_p)(table[3])(blob)
    size = ctypes.WINFUNCTYPE(ctypes.c_size_t, ctypes.c_void_p)(table[4])(blob)
    text = ctypes.string_at(pointer, size).rstrip(b'\0').decode('latin1')
    ctypes.WINFUNCTYPE(ctypes.c_ulong, ctypes.c_void_p)(table[2])(blob)
    return text


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('command', choices=['info', 'extract', 'disasm'])
    ap.add_argument('args', nargs='+')
    ap.add_argument('--game', default=os.environ.get('D2R_PATH'))
    ap.add_argument('--set', action='append', default=[], metavar='NAME=VALUE')
    a = ap.parse_args()
    shader = read(load(a.args[0], a.game))
    switches, programs = shader['switches'], shader['programs']
    if a.command == 'info':
        sizes = [len(p) for p in programs]
        print(f'{len(programs)} program(s), {min(sizes)} to {max(sizes)} bytes')
        for name, values in switches:
            print(f'  {name}: {", ".join(values)}')
    elif a.command == 'extract':
        if len(a.args) != 2:
            raise SystemExit('extract needs <file> <out folder>')
        os.makedirs(a.args[1], exist_ok=True)
        for k, code in enumerate(programs):
            label = '_'.join(f'{n}{v}' for n, v in settings(switches, k).items())
            with open(os.path.join(a.args[1], f'{k:04d}{"_" + label if label else ""}.dxbc'), 'wb') as f:
                f.write(code)
        print(f'{a.args[1]}: {len(programs)} files')
    else:
        if len(a.args) != 2:
            raise SystemExit('disasm needs <file> <out.asm>')
        chosen = dict(item.split('=', 1) for item in a.set)
        k = program_number(switches, chosen)
        text = disassemble(programs[k])
        with open(a.args[1], 'w', encoding='utf-8', newline='\n') as f:
            f.write(f'// program {k}: {settings(switches, k)}\n' + text)
        print(f'{a.args[1]}: program {k}, {len(text.splitlines())} lines')


if __name__ == '__main__':
    main()
