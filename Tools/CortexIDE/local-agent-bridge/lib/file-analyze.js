"use strict";

// Lets the agent "see" files that are not plain text, without native dependencies (the VSIX ships
// without node_modules):
// - detect():        magic-byte file type detection (the libmagic part)
// - imageInfo():     dimensions / depth of PNG, JPEG, GIF, WebP, BMP, TGA, DDS, ICO, TIFF, PSD
// - prepareImage():  turns an image into what a vision model takes (PNG/JPEG/GIF/WebP, base64,
//                    long edge capped). BMP/TGA/DDS are decoded here; oversized or other formats
//                    are resized with System.Drawing through PowerShell (Windows)
// - analyzeFile():   structured text for binaries instead of raw bytes: PE imports/exports,
//                    .NET metadata (assembly, references, types, methods, fields: the dnlib part),
//                    ZIP/TAR/GZ listings and entry extraction, PDF text, MPQ/BSA/Unity headers,
//                    and a hex + strings fallback
// - findImageRefs(): image paths / URLs mentioned in a prompt, to attach them automatically

const fs = require("fs");
const os = require("os");
const path = require("path");
const zlib = require("zlib");
const { spawn } = require("child_process");

/** Formats every vision API takes as-is. */
const API_MIMES = new Set(["image/png", "image/jpeg", "image/gif", "image/webp"]);
/** 5 MB base64 is Claude's per-image limit; raw bytes are 3/4 of that. */
const MAX_IMAGE_BYTES = Math.floor((5 * 1024 * 1024 * 3) / 4) - 4096;
/** Long edge sent to the model: Claude downsizes anything larger anyway, local VL models pay per pixel. */
const DEFAULT_MAX_EDGE = 1568;
const MAX_READ = 128 * 1024 * 1024;
const IMAGE_EXT = /\.(png|jpe?g|gif|webp|bmp|tga|dds|tiff?|ico)$/i;
const IMAGE_EXT_SRC = "png|jpe?g|gif|webp|bmp|tga|dds|tiff?|ico";

// ---------------------------------------------------------------- detection

function ascii(buf, at, n) {
  return at + n <= buf.length ? buf.toString("latin1", at, at + n) : "";
}

/**
 * What kind of file the bytes are. `name` (file name) only breaks ties for formats without magic
 * bytes (TGA, ICO, plain text extensions).
 * @returns {{kind:string, format:string, mime:string, label:string}}
 */
function detect(buf, name = "") {
  const ext = path.extname(String(name || "")).toLowerCase();
  const b = buf;
  const r = (kind, format, mime, label) => ({ kind, format, mime: mime || "application/octet-stream", label: label || format.toUpperCase() });
  if (!b || !b.length) return r("empty", "empty", "", "empty file");
  const u32be = (o) => (o + 4 <= b.length ? b.readUInt32BE(o) : -1);
  if (u32be(0) === 0x89504e47) return r("image", "png", "image/png", "PNG image");
  if (b[0] === 0xff && b[1] === 0xd8 && b[2] === 0xff) return r("image", "jpeg", "image/jpeg", "JPEG image");
  if (ascii(b, 0, 6) === "GIF87a" || ascii(b, 0, 6) === "GIF89a") return r("image", "gif", "image/gif", "GIF image");
  if (ascii(b, 0, 4) === "RIFF") {
    const t = ascii(b, 8, 4);
    if (t === "WEBP") return r("image", "webp", "image/webp", "WebP image");
    if (t === "WAVE") return r("audio", "wav", "audio/wav", "WAV audio");
    if (t === "AVI ") return r("video", "avi", "video/x-msvideo", "AVI video");
  }
  if (ascii(b, 0, 2) === "BM" && b.length > 30 && (ext === ".bmp" || ext === ".dib" || b.readUInt32LE(2) === b.length || [12, 40, 52, 56, 108, 124].includes(b.readUInt32LE(14)))) {
    return r("image", "bmp", "image/bmp", "BMP image");
  }
  if (ascii(b, 0, 4) === "DDS ") return r("image", "dds", "image/vnd-ms.dds", "DirectDraw Surface texture");
  if ((ascii(b, 0, 4) === "II*\u0000") || (ascii(b, 0, 4) === "MM\u0000*")) return r("image", "tiff", "image/tiff", "TIFF image");
  if (ascii(b, 0, 4) === "8BPS") return r("image", "psd", "image/vnd.adobe.photoshop", "Photoshop document");
  if (b.length > 6 && b.readUInt32LE(0) === 0x00010000 && ext === ".ico") return r("image", "ico", "image/x-icon", "Windows icon");
  if (b.length > 6 && b.readUInt16LE(0) === 0 && b.readUInt16LE(2) === 1 && b.readUInt16LE(4) > 0 && b.readUInt16LE(4) < 64 && ext !== ".ttf") {
    if (ext === ".ico" || ext === "") return r("image", "ico", "image/x-icon", "Windows icon");
  }
  if (ascii(b, 0, 5) === "%PDF-") return r("pdf", "pdf", "application/pdf", "PDF document " + ascii(b, 5, 3));
  if (ascii(b, 0, 4) === "PK\u0003\u0004" || ascii(b, 0, 4) === "PK\u0005\u0006") return r("archive", "zip", "application/zip", "ZIP archive");
  if (u32be(0) === 0x377abcaf && b[4] === 0x27 && b[5] === 0x1c) return r("archive", "7z", "application/x-7z-compressed", "7-Zip archive");
  if (ascii(b, 0, 4) === "Rar!") return r("archive", "rar", "application/vnd.rar", "RAR archive");
  if (b[0] === 0x1f && b[1] === 0x8b) return r("archive", "gzip", "application/gzip", "gzip data");
  if (u32be(0) === 0xfd377a58) return r("archive", "xz", "application/x-xz", "xz data");
  if (ascii(b, 0, 3) === "BZh") return r("archive", "bzip2", "application/x-bzip2", "bzip2 data");
  if (u32be(0) === 0x28b52ffd) return r("archive", "zstd", "application/zstd", "Zstandard data");
  if (ascii(b, 0, 4) === "MSCF") return r("archive", "cab", "application/vnd.ms-cab-compressed", "Microsoft Cabinet archive");
  if (ascii(b, 0x8001, 5) === "CD001") return r("archive", "iso", "application/x-iso9660-image", "ISO 9660 disc image");
  if (u32be(0) === 0xd0cf11e0 && u32be(4) === 0xa1b11ae1) {
    if (ext === ".msi" || ext === ".msp") return r("archive", "msi", "application/x-msi", "Windows Installer package");
    return r("data", "ole", "application/x-ole-storage", "OLE compound file (old Office document, MSI, ...)");
  }
  if (ascii(b, 257, 5) === "ustar") return r("archive", "tar", "application/x-tar", "TAR archive");
  if (ascii(b, 0, 4) === "MPQ\u001a" || ascii(b, 0, 4) === "MPQ\u001b") return r("archive", "mpq", "", "Blizzard MPQ archive");
  if (ascii(b, 0, 4) === "BSA\u0000") return r("archive", "bsa", "", "Bethesda BSA archive");
  if (ascii(b, 0, 4) === "BTDX") return r("archive", "ba2", "", "Bethesda BA2 archive");
  if (ascii(b, 0, 4) === "TES4" || ascii(b, 0, 4) === "TES3") return r("data", "tesplugin", "", "Bethesda plugin (" + ascii(b, 0, 4) + ")");
  if (ascii(b, 0, 7) === "UnityFS" || ascii(b, 0, 8) === "UnityWeb" || ascii(b, 0, 8) === "UnityRaw") return r("data", "unitybundle", "", "Unity asset bundle");
  if (ascii(b, 0, 2) === "MZ") return r("exe", "pe", "application/vnd.microsoft.portable-executable", "Windows PE executable");
  if (u32be(0) === 0x7f454c46) return r("exe", "elf", "application/x-elf", "ELF executable");
  if (u32be(0) === 0xcafebabe) {
    return b.length > 8 && b.readUInt16BE(6) >= 45 ? r("exe", "javaclass", "application/java-vm", "Java class file") : r("exe", "macho", "", "Mach-O universal binary");
  }
  if ([0xcffaedfe, 0xcefaedfe, 0xfeedfacf, 0xfeedface].includes(u32be(0))) return r("exe", "macho", "", "Mach-O executable");
  if (ascii(b, 0, 4) === "\u0000asm") return r("exe", "wasm", "application/wasm", "WebAssembly module");
  if (ascii(b, 0, 4) === "\u001bLua") return r("exe", "luac", "", "Lua bytecode");
  if (ascii(b, 0, 16) === "SQLite format 3\u0000") return r("data", "sqlite", "application/vnd.sqlite3", "SQLite database");
  if (ascii(b, 0, 4) === "OggS") return r("audio", "ogg", "audio/ogg", "Ogg media");
  if (ascii(b, 0, 4) === "fLaC") return r("audio", "flac", "audio/flac", "FLAC audio");
  if (ascii(b, 0, 3) === "ID3" || (b[0] === 0xff && (b[1] & 0xe0) === 0xe0 && ext === ".mp3")) return r("audio", "mp3", "audio/mpeg", "MP3 audio");
  if (ascii(b, 4, 4) === "ftyp") {
    const brand = ascii(b, 8, 4);
    if (/^(avif|avis)$/.test(brand)) return r("image", "avif", "image/avif", "AVIF image");
    if (/^(heic|heix|mif1|msf1)$/.test(brand)) return r("image", "heic", "image/heic", "HEIF image");
    return r("video", "mp4", "video/mp4", "MP4/QuickTime media (" + brand.trim() + ")");
  }
  if (ascii(b, 0, 4) === "wOFF" || ascii(b, 0, 4) === "wOF2") return r("font", "woff", "font/woff", "WOFF font");
  if (ascii(b, 0, 4) === "OTTO" || (u32be(0) === 0x00010000 && /\.(ttf|otf)$/.test(ext))) return r("font", "ttf", "font/ttf", "TrueType/OpenType font");
  if (ext === ".tga" && b.length > 18 && [1, 2, 3, 9, 10, 11].includes(b[2])) return r("image", "tga", "image/x-tga", "Targa image");
  // Text: a BOM, or no NUL bytes and mostly printable in the first 8 KB.
  if ((b[0] === 0xff && b[1] === 0xfe) || (b[0] === 0xfe && b[1] === 0xff)) return r("text", "utf16", "text/plain", "UTF-16 text");
  const head = b.subarray(0, 8192);
  if (!head.includes(0)) {
    let odd = 0;
    for (const c of head) if (c < 9 || (c > 13 && c < 32) || c === 127) odd++;
    if (odd <= head.length * 0.02) return r("text", "text", "text/plain", "text");
  }
  if (looksUtf16le(head)) return r("text", "utf16", "text/plain", "UTF-16 text (no BOM)");
  return r("binary", "unknown", "", "unrecognised binary data");
}

function looksUtf16le(b) {
  if (b.length < 16) return false;
  let zeros = 0;
  let pairs = 0;
  for (let i = 1; i < b.length; i += 2) {
    pairs++;
    if (b[i] === 0 && b[i - 1] >= 9 && b[i - 1] < 127) zeros++;
  }
  return zeros > pairs * 0.9;
}

/** Text of a file that may be UTF-16 (with or without BOM) or UTF-8. */
function decodeText(buf) {
  if (buf[0] === 0xff && buf[1] === 0xfe) return buf.subarray(2).toString("utf16le");
  if (buf[0] === 0xfe && buf[1] === 0xff) {
    const sw = Buffer.from(buf.subarray(2, 2 + ((buf.length - 2) & ~1)));
    sw.swap16();
    return sw.toString("utf16le");
  }
  if (looksUtf16le(buf.subarray(0, 8192))) return buf.toString("utf16le");
  const t = buf.toString("utf8");
  return t.charCodeAt(0) === 0xfeff ? t.slice(1) : t;
}

// ---------------------------------------------------------------- image metadata

/** @returns {{width:number,height:number,detail:string}|null} */
function imageInfo(buf, format) {
  try {
    const b = buf;
    switch (format) {
      case "png": {
        const ct = { 0: "grayscale", 2: "RGB", 3: "palette", 4: "grayscale+alpha", 6: "RGBA" }[b[25]] || "type " + b[25];
        const anim = b.includes(Buffer.from("acTL")) ? ", animated (APNG)" : "";
        return { width: b.readUInt32BE(16), height: b.readUInt32BE(20), detail: b[24] + "-bit " + ct + (b[28] ? ", interlaced" : "") + anim };
      }
      case "jpeg": {
        let i = 2;
        let exif = false;
        while (i + 9 < b.length) {
          if (b[i] !== 0xff) {
            i++;
            continue;
          }
          const m = b[i + 1];
          if (m === 0xd8 || m === 0x01 || (m >= 0xd0 && m <= 0xd7) || m === 0xff) {
            i += m === 0xff ? 1 : 2;
            continue;
          }
          const len = b.readUInt16BE(i + 2);
          if (m === 0xe1 && ascii(b, i + 4, 4) === "Exif") exif = true;
          if (m >= 0xc0 && m <= 0xcf && m !== 0xc4 && m !== 0xc8 && m !== 0xcc) {
            const comps = b[i + 9];
            return { width: b.readUInt16BE(i + 7), height: b.readUInt16BE(i + 5), detail: (comps === 1 ? "grayscale" : comps === 4 ? "CMYK" : "colour") + (m === 0xc2 ? ", progressive" : "") + (exif ? ", EXIF" : "") };
          }
          i += 2 + len;
        }
        return null;
      }
      case "gif":
        return { width: b.readUInt16LE(6), height: b.readUInt16LE(8), detail: b.includes(Buffer.from("NETSCAPE2.0")) ? "animated" : "still" };
      case "bmp": {
        const dib = b.readUInt32LE(14);
        if (dib === 12) return { width: b.readUInt16LE(18), height: b.readUInt16LE(20), detail: b.readUInt16LE(24) + "-bit (OS/2)" };
        return { width: b.readInt32LE(18), height: Math.abs(b.readInt32LE(22)), detail: b.readUInt16LE(28) + "-bit" + (b.readUInt32LE(30) ? ", compression " + b.readUInt32LE(30) : "") };
      }
      case "webp": {
        const c = ascii(b, 12, 4);
        if (c === "VP8 ") return { width: b.readUInt16LE(26) & 0x3fff, height: b.readUInt16LE(28) & 0x3fff, detail: "lossy" };
        if (c === "VP8L") {
          const v = b.readUInt32LE(21);
          return { width: (v & 0x3fff) + 1, height: ((v >>> 14) & 0x3fff) + 1, detail: "lossless" };
        }
        if (c === "VP8X") {
          const f = b[20];
          return { width: 1 + b.readUIntLE(24, 3), height: 1 + b.readUIntLE(27, 3), detail: "extended" + (f & 0x10 ? ", alpha" : "") + (f & 0x02 ? ", animated" : "") };
        }
        return null;
      }
      case "tga":
        return { width: b.readUInt16LE(12), height: b.readUInt16LE(14), detail: b[16] + "-bit, type " + b[2] + ([9, 10, 11].includes(b[2]) ? " (RLE)" : "") };
      case "dds": {
        const four = ascii(b, 84, 4).replace(/\u0000/g, "");
        const dx10 = four === "DX10" ? DXGI[b.readUInt32LE(128)] || "DXGI " + b.readUInt32LE(128) : "";
        const fmt = dx10 || four || b.readUInt32LE(88) + "-bit uncompressed";
        return { width: b.readUInt32LE(16), height: b.readUInt32LE(12), detail: fmt + ", " + Math.max(1, b.readUInt32LE(28)) + " mip level(s)" };
      }
      case "ico": {
        const n = b.readUInt16LE(4);
        const sizes = [];
        for (let k = 0; k < n && 6 + k * 16 + 16 <= b.length; k++) sizes.push((b[6 + k * 16] || 256) + "x" + (b[7 + k * 16] || 256));
        const big = sizes.map((s) => s.split("x").map(Number)).sort((x, y) => y[0] - x[0])[0] || [0, 0];
        return { width: big[0], height: big[1], detail: n + " image(s): " + sizes.join(", ") };
      }
      case "tiff": {
        const le = ascii(b, 0, 2) === "II";
        const r16 = (o) => (le ? b.readUInt16LE(o) : b.readUInt16BE(o));
        const r32 = (o) => (le ? b.readUInt32LE(o) : b.readUInt32BE(o));
        const ifd = r32(4);
        const n = r16(ifd);
        let w = 0;
        let h = 0;
        for (let k = 0; k < n; k++) {
          const e = ifd + 2 + k * 12;
          const tag = r16(e);
          const v = r16(e + 2) === 3 ? r16(e + 8) : r32(e + 8);
          if (tag === 256) w = v;
          if (tag === 257) h = v;
        }
        return { width: w, height: h, detail: le ? "little-endian" : "big-endian" };
      }
      case "psd":
        return { width: b.readUInt32BE(18), height: b.readUInt32BE(14), detail: b.readUInt16BE(12) + " channels, " + b.readUInt16BE(22) + "-bit" };
      default:
        return null;
    }
  } catch {
    return null;
  }
}

const DXGI = { 2: "R32G32B32A32_FLOAT", 10: "R16G16B16A16_FLOAT", 28: "R8G8B8A8_UNORM", 29: "R8G8B8A8_UNORM_SRGB", 71: "BC1", 72: "BC1_SRGB", 74: "BC2", 75: "BC2_SRGB", 77: "BC3", 78: "BC3_SRGB", 80: "BC4", 83: "BC5", 87: "B8G8R8A8_UNORM", 91: "B8G8R8A8_UNORM_SRGB", 95: "BC6H_UF16", 98: "BC7", 99: "BC7_SRGB" };

// ---------------------------------------------------------------- pixel decoders (→ RGBA)

/** @returns {{width:number,height:number,rgba:Buffer}} */
function decodeBmp(b) {
  const off = b.readUInt32LE(10);
  const dib = b.readUInt32LE(14);
  if (dib < 40) throw new Error("OS/2 BMP headers are not supported");
  const w = b.readInt32LE(18);
  const hRaw = b.readInt32LE(22);
  const h = Math.abs(hRaw);
  const bpp = b.readUInt16LE(28);
  const comp = b.readUInt32LE(30);
  if (comp !== 0 && comp !== 3) throw new Error("compressed BMP (type " + comp + ") is not supported");
  if (![1, 4, 8, 24, 32].includes(bpp)) throw new Error(bpp + "-bit BMP is not supported");
  checkDims(w, h);
  const stride = ((bpp * w + 31) >>> 5) * 4;
  const palette = [];
  if (bpp <= 8) {
    const n = b.readUInt32LE(46) || 1 << bpp;
    const p0 = 14 + dib;
    for (let k = 0; k < n; k++) palette.push([b[p0 + k * 4 + 2], b[p0 + k * 4 + 1], b[p0 + k * 4]]);
  }
  const out = Buffer.alloc(w * h * 4);
  let anyAlpha = false;
  for (let y = 0; y < h; y++) {
    const row = off + (hRaw > 0 ? h - 1 - y : y) * stride;
    for (let x = 0; x < w; x++) {
      const o = (y * w + x) * 4;
      if (bpp === 24 || bpp === 32) {
        const p = row + x * (bpp / 8);
        out[o] = b[p + 2];
        out[o + 1] = b[p + 1];
        out[o + 2] = b[p];
        out[o + 3] = bpp === 32 ? b[p + 3] : 255;
        if (bpp === 32 && b[p + 3]) anyAlpha = true;
      } else {
        const bit = x * bpp;
        const byte = b[row + (bit >>> 3)];
        const idx = (byte >>> (8 - bpp - (bit & 7))) & ((1 << bpp) - 1);
        const c = palette[idx] || [0, 0, 0];
        out[o] = c[0];
        out[o + 1] = c[1];
        out[o + 2] = c[2];
        out[o + 3] = 255;
      }
    }
  }
  if (bpp === 32 && !anyAlpha) for (let i = 3; i < out.length; i += 4) out[i] = 255; // BGRX
  return { width: w, height: h, rgba: out };
}

function decodeTga(b) {
  const idLen = b[0];
  const cmapType = b[1];
  const type = b[2];
  const cmapLen = b.readUInt16LE(5);
  const cmapBits = b[7];
  const w = b.readUInt16LE(12);
  const h = b.readUInt16LE(14);
  const bpp = b[16];
  const desc = b[17];
  if (![2, 3, 10, 11].includes(type)) throw new Error("colour-mapped TGA (type " + type + ") is not supported");
  checkDims(w, h);
  const px = bpp >>> 3;
  let p = 18 + idLen + (cmapType ? cmapLen * Math.ceil(cmapBits / 8) : 0);
  const n = w * h;
  const pixels = Buffer.alloc(n * 4);
  const put = (i, s) => {
    const o = i * 4;
    if (px === 1) {
      pixels[o] = pixels[o + 1] = pixels[o + 2] = b[s];
      pixels[o + 3] = 255;
    } else if (px === 2) {
      const v = b.readUInt16LE(s);
      pixels[o] = ((v >>> 10) & 31) * 8.226;
      pixels[o + 1] = ((v >>> 5) & 31) * 8.226;
      pixels[o + 2] = (v & 31) * 8.226;
      pixels[o + 3] = 255;
    } else {
      pixels[o] = b[s + 2];
      pixels[o + 1] = b[s + 1];
      pixels[o + 2] = b[s];
      pixels[o + 3] = px === 4 ? b[s + 3] : 255;
    }
  };
  if (type === 2 || type === 3) {
    for (let i = 0; i < n; i++) put(i, p + i * px);
  } else {
    let i = 0;
    while (i < n && p < b.length) {
      const hdr = b[p++];
      const count = (hdr & 0x7f) + 1;
      if (hdr & 0x80) {
        for (let k = 0; k < count && i < n; k++) put(i++, p);
        p += px;
      } else {
        for (let k = 0; k < count && i < n; k++, p += px) put(i++, p);
      }
    }
  }
  // Default origin is bottom-left; bit 5 = top-left, bit 4 = right-to-left.
  const out = Buffer.alloc(n * 4);
  const top = desc & 0x20;
  const right = desc & 0x10;
  for (let y = 0; y < h; y++) {
    for (let x = 0; x < w; x++) {
      const sy = top ? y : h - 1 - y;
      const sx = right ? w - 1 - x : x;
      pixels.copy(out, (y * w + x) * 4, (sy * w + sx) * 4, (sy * w + sx) * 4 + 4);
    }
  }
  return { width: w, height: h, rgba: out };
}

function rgb565(v) {
  return [((v >>> 11) & 31) * 255 / 31, ((v >>> 5) & 63) * 255 / 63, (v & 31) * 255 / 31];
}

/** Colour part of a BC1/2/3 block → 16 RGBA pixels written into out. */
function bcColor(b, p, out, w, h, bx, by, bc1) {
  const c0 = b.readUInt16LE(p);
  const c1 = b.readUInt16LE(p + 2);
  const a = rgb565(c0);
  const c = rgb565(c1);
  const pal = [[...a, 255], [...c, 255]];
  if (!bc1 || c0 > c1) {
    pal.push([(2 * a[0] + c[0]) / 3, (2 * a[1] + c[1]) / 3, (2 * a[2] + c[2]) / 3, 255]);
    pal.push([(a[0] + 2 * c[0]) / 3, (a[1] + 2 * c[1]) / 3, (a[2] + 2 * c[2]) / 3, 255]);
  } else {
    pal.push([(a[0] + c[0]) / 2, (a[1] + c[1]) / 2, (a[2] + c[2]) / 2, 255]);
    pal.push([0, 0, 0, 0]);
  }
  const bits = b.readUInt32LE(p + 4);
  for (let k = 0; k < 16; k++) {
    const x = bx + (k & 3);
    const y = by + (k >>> 2);
    if (x >= w || y >= h) continue;
    const col = pal[(bits >>> (2 * k)) & 3];
    const o = (y * w + x) * 4;
    out[o] = col[0];
    out[o + 1] = col[1];
    out[o + 2] = col[2];
    out[o + 3] = col[3];
  }
}

function decodeDds(b) {
  const h = b.readUInt32LE(12);
  const w = b.readUInt32LE(16);
  checkDims(w, h);
  const pfFlags = b.readUInt32LE(80);
  let four = ascii(b, 84, 4);
  let data = 128;
  if (four === "DX10") {
    const f = b.readUInt32LE(128);
    data = 148;
    four = { 71: "DXT1", 72: "DXT1", 74: "DXT3", 75: "DXT3", 77: "DXT5", 78: "DXT5", 28: "RGBA", 29: "RGBA", 87: "BGRA", 91: "BGRA" }[f] || "DXGI " + (DXGI[f] || f);
  }
  const out = Buffer.alloc(w * h * 4);
  if (four === "DXT1" || four === "DXT3" || four === "DXT5") {
    const size = four === "DXT1" ? 8 : 16;
    let p = data;
    for (let by = 0; by < h; by += 4) {
      for (let bx = 0; bx < w; bx += 4, p += size) {
        if (p + size > b.length) throw new Error("truncated DDS data");
        if (four === "DXT1") {
          bcColor(b, p, out, w, h, bx, by, true);
          continue;
        }
        bcColor(b, p + 8, out, w, h, bx, by, false);
        const alpha = new Array(16);
        if (four === "DXT3") {
          for (let k = 0; k < 16; k++) alpha[k] = ((b[p + (k >>> 1)] >>> ((k & 1) * 4)) & 15) * 17;
        } else {
          const a0 = b[p];
          const a1 = b[p + 1];
          const pal = [a0, a1];
          if (a0 > a1) for (let i = 1; i < 7; i++) pal.push(((7 - i) * a0 + i * a1) / 7);
          else {
            for (let i = 1; i < 5; i++) pal.push(((5 - i) * a0 + i * a1) / 5);
            pal.push(0, 255);
          }
          let bits = 0n;
          for (let i = 0; i < 6; i++) bits |= BigInt(b[p + 2 + i]) << BigInt(8 * i);
          for (let k = 0; k < 16; k++) alpha[k] = pal[Number((bits >> BigInt(3 * k)) & 7n)];
        }
        for (let k = 0; k < 16; k++) {
          const x = bx + (k & 3);
          const y = by + (k >>> 2);
          if (x < w && y < h) out[(y * w + x) * 4 + 3] = alpha[k];
        }
      }
    }
    return { width: w, height: h, rgba: out };
  }
  const uncompressed = four === "RGBA" || four === "BGRA" || (pfFlags & 0x40) !== 0;
  if (!uncompressed) throw new Error("DDS format " + (four.replace(/\u0000/g, "") || "?") + " cannot be decoded here (BC1-BC3 and uncompressed RGB(A) can)");
  const bits = four === "RGBA" || four === "BGRA" ? 32 : b.readUInt32LE(88);
  const masks = four === "RGBA" ? [0xff, 0xff00, 0xff0000, 0xff000000] : four === "BGRA" ? [0xff0000, 0xff00, 0xff, 0xff000000] : [b.readUInt32LE(92), b.readUInt32LE(96), b.readUInt32LE(100), pfFlags & 1 ? b.readUInt32LE(104) : 0];
  const px = bits >>> 3;
  const chan = (v, m) => {
    if (!m) return 255;
    let s = 0;
    while (!((m >>> s) & 1)) s++;
    const max = m >>> s;
    return Math.round((((v & m) >>> s) * 255) / max);
  };
  for (let i = 0; i < w * h; i++) {
    const p = data + i * px;
    if (p + px > b.length) throw new Error("truncated DDS data");
    const v = px === 4 ? b.readUInt32LE(p) : px === 3 ? b.readUIntLE(p, 3) : b.readUInt16LE(p);
    out[i * 4] = chan(v, masks[0] >>> 0);
    out[i * 4 + 1] = chan(v, masks[1] >>> 0);
    out[i * 4 + 2] = chan(v, masks[2] >>> 0);
    out[i * 4 + 3] = chan(v, masks[3] >>> 0);
  }
  return { width: w, height: h, rgba: out };
}

function checkDims(w, h) {
  if (!(w > 0 && h > 0) || w * h > 64 * 1024 * 1024) throw new Error("unsupported image size " + w + "x" + h);
}

/** Area-average downscale so the long edge is at most maxEdge. */
function downscale(img, maxEdge) {
  const { width: w, height: h, rgba } = img;
  const s = maxEdge / Math.max(w, h);
  if (s >= 1) return img;
  const nw = Math.max(1, Math.round(w * s));
  const nh = Math.max(1, Math.round(h * s));
  const out = Buffer.alloc(nw * nh * 4);
  for (let y = 0; y < nh; y++) {
    const y0 = Math.floor((y * h) / nh);
    const y1 = Math.max(y0 + 1, Math.floor(((y + 1) * h) / nh));
    for (let x = 0; x < nw; x++) {
      const x0 = Math.floor((x * w) / nw);
      const x1 = Math.max(x0 + 1, Math.floor(((x + 1) * w) / nw));
      let r = 0;
      let g = 0;
      let bl = 0;
      let a = 0;
      let n = 0;
      for (let yy = y0; yy < y1; yy++) {
        for (let xx = x0; xx < x1; xx++) {
          const o = (yy * w + xx) * 4;
          r += rgba[o];
          g += rgba[o + 1];
          bl += rgba[o + 2];
          a += rgba[o + 3];
          n++;
        }
      }
      const o = (y * nw + x) * 4;
      out[o] = r / n;
      out[o + 1] = g / n;
      out[o + 2] = bl / n;
      out[o + 3] = a / n;
    }
  }
  return { width: nw, height: nh, rgba: out };
}

const CRC_TABLE = (() => {
  const t = new Uint32Array(256);
  for (let n = 0; n < 256; n++) {
    let c = n;
    for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
    t[n] = c >>> 0;
  }
  return t;
})();

function crc32(buf) {
  let c = 0xffffffff;
  for (let i = 0; i < buf.length; i++) c = CRC_TABLE[(c ^ buf[i]) & 0xff] ^ (c >>> 8);
  return (c ^ 0xffffffff) >>> 0;
}

function pngChunk(type, data) {
  const len = Buffer.alloc(4);
  len.writeUInt32BE(data.length);
  const td = Buffer.concat([Buffer.from(type, "latin1"), data]);
  const crc = Buffer.alloc(4);
  crc.writeUInt32BE(crc32(td));
  return Buffer.concat([len, td, crc]);
}

/** RGBA → PNG file bytes. */
function encodePng(width, height, rgba) {
  const raw = Buffer.alloc((width * 4 + 1) * height);
  for (let y = 0; y < height; y++) {
    raw[y * (width * 4 + 1)] = 0;
    Buffer.from(rgba.buffer, rgba.byteOffset, rgba.length).copy(raw, y * (width * 4 + 1) + 1, y * width * 4, (y + 1) * width * 4);
  }
  const ihdr = Buffer.alloc(13);
  ihdr.writeUInt32BE(width, 0);
  ihdr.writeUInt32BE(height, 4);
  ihdr[8] = 8;
  ihdr[9] = 6;
  return Buffer.concat([
    Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]),
    pngChunk("IHDR", ihdr),
    pngChunk("IDAT", zlib.deflateSync(raw, { level: 6 })),
    pngChunk("IEND", Buffer.alloc(0)),
  ]);
}

// ---------------------------------------------------------------- image preparation

/** Resize / convert with System.Drawing (Windows PowerShell). Resolves the new bytes, or null. */
function psResize(file, maxEdge, format) {
  if (process.platform !== "win32") return Promise.resolve(null);
  const out = path.join(os.tmpdir(), "cortexide-img-" + process.pid + "-" + Date.now() + "-" + Math.random().toString(36).slice(2) + (format === "jpeg" ? ".jpg" : ".png"));
  const script = [
    "$ErrorActionPreference='Stop'",
    "Add-Type -AssemblyName System.Drawing",
    "$src=[System.Drawing.Image]::FromFile($env:CIX_IN)",
    "try {",
    "$w=$src.Width; $h=$src.Height; $e=[double]$env:CIX_EDGE",
    "$s=[Math]::Min(1.0, $e / [Math]::Max($w,$h))",
    "$nw=[Math]::Max(1,[int][Math]::Round($w*$s)); $nh=[Math]::Max(1,[int][Math]::Round($h*$s))",
    "$bmp=New-Object System.Drawing.Bitmap $nw,$nh",
    "$g=[System.Drawing.Graphics]::FromImage($bmp)",
    "$g.InterpolationMode='HighQualityBicubic'; $g.PixelOffsetMode='HighQuality'; $g.SmoothingMode='HighQuality'",
    "if ($env:CIX_FMT -eq 'jpeg') { $g.Clear([System.Drawing.Color]::White) }",
    "$g.DrawImage($src,0,0,$nw,$nh); $g.Dispose()",
    "if ($env:CIX_FMT -eq 'jpeg') {",
    "  $codec=[System.Drawing.Imaging.ImageCodecInfo]::GetImageEncoders() | Where-Object { $_.MimeType -eq 'image/jpeg' }",
    "  $p=New-Object System.Drawing.Imaging.EncoderParameters 1",
    "  $p.Param[0]=New-Object System.Drawing.Imaging.EncoderParameter([System.Drawing.Imaging.Encoder]::Quality,[long]85)",
    "  $bmp.Save($env:CIX_OUT,$codec,$p)",
    "} else { $bmp.Save($env:CIX_OUT,[System.Drawing.Imaging.ImageFormat]::Png) }",
    "$bmp.Dispose()",
    "} finally { $src.Dispose() }",
  ].join("\n");
  return new Promise((resolve) => {
    let child;
    try {
      child = spawn("powershell.exe", ["-NoLogo", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-EncodedCommand", Buffer.from(script, "utf16le").toString("base64")], {
        windowsHide: true,
        env: { ...process.env, CIX_IN: file, CIX_OUT: out, CIX_EDGE: String(maxEdge), CIX_FMT: format },
      });
    } catch {
      resolve(null);
      return;
    }
    const timer = setTimeout(() => child.kill(), 30000);
    child.on("error", () => {
      clearTimeout(timer);
      resolve(null);
    });
    child.on("close", () => {
      clearTimeout(timer);
      try {
        const data = fs.readFileSync(out);
        fs.rmSync(out, { force: true });
        resolve(data.length ? data : null);
      } catch {
        resolve(null);
      }
    });
  });
}

function readCapped(abs, cap = MAX_READ) {
  const size = fs.statSync(abs).size;
  if (size > cap) throw new Error(abs + " is " + fmtBytes(size) + "; only files up to " + fmtBytes(cap) + " are analysed in full");
  return fs.readFileSync(abs);
}

function fmtBytes(n) {
  if (n < 1024) return n + " B";
  if (n < 1024 * 1024) return (n / 1024).toFixed(1) + " KB";
  if (n < 1024 * 1024 * 1024) return (n / 1024 / 1024).toFixed(1) + " MB";
  return (n / 1024 / 1024 / 1024).toFixed(2) + " GB";
}

/**
 * Turn an image file (or its bytes) into what a vision model takes.
 * @param {string|Buffer} src absolute path, or the bytes (then pass name)
 * @returns {Promise<{mime:string,data:string,width:number,height:number,origWidth:number,origHeight:number,bytes:number,format:string,detail:string,note:string,path:string}>}
 */
async function prepareImage(src, { name = "", maxEdge = DEFAULT_MAX_EDGE, maxBytes = MAX_IMAGE_BYTES } = {}) {
  const isPath = typeof src === "string";
  const buf = isPath ? readCapped(src, 64 * 1024 * 1024) : src;
  const label = isPath ? src : name || "image";
  const det = detect(buf, isPath ? src : name);
  if (det.kind !== "image") throw new Error(label + " is not an image (" + det.label + ")");
  const info = imageInfo(buf, det.format) || { width: 0, height: 0, detail: "" };
  const base = { origWidth: info.width, origHeight: info.height, format: det.format, detail: info.detail, path: isPath ? src : name };
  const done = (bytes, mime, w, h, note) => ({ ...base, mime, data: bytes.toString("base64"), width: w, height: h, bytes: bytes.length, note: note || "" });

  if (det.format === "bmp" || det.format === "tga" || det.format === "dds") {
    let img = null;
    try {
      img = det.format === "bmp" ? decodeBmp(buf) : det.format === "tga" ? decodeTga(buf) : decodeDds(buf);
    } catch (e) {
      if (det.format !== "bmp") throw new Error(label + ": " + e.message);
      // Odd BMP variants (RLE, 16-bit): System.Drawing below reads them.
    }
    if (img) {
      const small = downscale(img, maxEdge);
      const png = encodePng(small.width, small.height, small.rgba);
      return done(png, "image/png", small.width, small.height, "converted " + det.format.toUpperCase() + " to PNG" + (small.width !== img.width ? ", scaled from " + img.width + "x" + img.height : ""));
    }
  }
  const fits = info.width && info.height && Math.max(info.width, info.height) <= maxEdge && buf.length <= maxBytes;
  if (API_MIMES.has(det.mime) && fits) return done(buf, det.mime, info.width, info.height, "");
  // Too large, or a format the APIs refuse (TIFF, ICO): resize/convert with System.Drawing.
  if (["png", "jpeg", "gif", "tiff", "ico", "bmp"].includes(det.format)) {
    let file = isPath ? src : "";
    let tmp = "";
    if (!file) {
      tmp = path.join(os.tmpdir(), "cortexide-src-" + process.pid + "-" + Date.now() + "." + det.format);
      fs.writeFileSync(tmp, buf);
      file = tmp;
    }
    try {
      const fmt = det.format === "jpeg" ? "jpeg" : "png";
      let out = await psResize(file, maxEdge, fmt);
      if (out && out.length > maxBytes && fmt === "png") out = await psResize(file, maxEdge, "jpeg");
      if (out && out.length <= maxBytes) {
        const d = detect(out);
        const i2 = imageInfo(out, d.format) || {};
        return done(out, d.mime, i2.width || 0, i2.height || 0, "scaled from " + info.width + "x" + info.height + (d.format !== det.format ? " and converted to " + d.format.toUpperCase() : ""));
      }
    } finally {
      if (tmp) fs.rmSync(tmp, { force: true });
    }
  }
  if (API_MIMES.has(det.mime) && buf.length <= maxBytes) return done(buf, det.mime, info.width, info.height, "sent at full size (could not resize here)");
  throw new Error(label + ": " + det.label + " " + (info.width ? info.width + "x" + info.height + " " : "") + "(" + fmtBytes(buf.length) + ") cannot be converted for the model here");
}

/** Rough prompt cost of one image (Claude: width*height/750, capped by its own resize). */
function imageTokens(img) {
  const w = (img && img.width) || 0;
  const h = (img && img.height) || 0;
  return w && h ? Math.min(1600, Math.ceil((w * h) / 750)) + 20 : 800;
}

// ---------------------------------------------------------------- PE / .NET

function cstr(b, at, max = 512) {
  if (at < 0 || at >= b.length) return "";
  let e = at;
  while (e < b.length && e - at < max && b[e] !== 0) e++;
  return b.toString("utf8", at, e);
}

const MACHINES = { 0x14c: "x86", 0x8664: "x64", 0xaa64: "ARM64", 0x1c4: "ARM", 0x200: "IA-64" };
const SUBSYSTEMS = { 1: "native", 2: "Windows GUI", 3: "console", 9: "Windows CE", 10: "EFI application", 14: "Xbox" };

function parsePe(b) {
  const e = b.readUInt32LE(0x3c);
  if (e + 24 > b.length || b.readUInt32LE(e) !== 0x4550) return null;
  const nsec = b.readUInt16LE(e + 6);
  const optSize = b.readUInt16LE(e + 20);
  const opt = e + 24;
  const is64 = b.readUInt16LE(opt) === 0x20b;
  const ndd = Math.min(16, b.readUInt32LE(opt + (is64 ? 108 : 92)));
  const dirs = [];
  for (let i = 0; i < ndd; i++) {
    const o = opt + (is64 ? 112 : 96) + i * 8;
    dirs.push({ rva: b.readUInt32LE(o), size: b.readUInt32LE(o + 4) });
  }
  const sections = [];
  for (let i = 0; i < nsec; i++) {
    const s = opt + optSize + i * 40;
    if (s + 40 > b.length) break;
    sections.push({ name: b.toString("latin1", s, s + 8).replace(/\u0000+$/, ""), vsize: b.readUInt32LE(s + 8), va: b.readUInt32LE(s + 12), rawSize: b.readUInt32LE(s + 16), raw: b.readUInt32LE(s + 20) });
  }
  const off = (rva) => {
    for (const s of sections) if (rva >= s.va && rva < s.va + Math.max(s.vsize, s.rawSize)) return s.raw + rva - s.va;
    return rva < (sections[0] ? sections[0].raw : b.length) ? rva : -1;
  };
  return {
    machine: MACHINES[b.readUInt16LE(e + 4)] || "machine 0x" + b.readUInt16LE(e + 4).toString(16),
    time: b.readUInt32LE(e + 8),
    dll: (b.readUInt16LE(e + 22) & 0x2000) !== 0,
    is64,
    subsystem: SUBSYSTEMS[b.readUInt16LE(opt + 68)] || "subsystem " + b.readUInt16LE(opt + 68),
    dirs,
    sections,
    off,
  };
}

function peImports(b, pe, maxDlls = 60, maxFns = 25) {
  const d = pe.dirs[1];
  const out = [];
  if (!d || !d.rva) return out;
  let p = pe.off(d.rva);
  for (let n = 0; p > 0 && p + 20 <= b.length && n < 400; n++, p += 20) {
    const oft = b.readUInt32LE(p);
    const nameRva = b.readUInt32LE(p + 12);
    const ft = b.readUInt32LE(p + 16);
    if (!oft && !nameRva && !ft) break;
    const dll = cstr(b, pe.off(nameRva));
    const fns = [];
    let t = pe.off(oft || ft);
    let total = 0;
    const step = pe.is64 ? 8 : 4;
    for (let k = 0; t > 0 && t + step <= b.length && k < 5000; k++, t += step) {
      const v = pe.is64 ? b.readBigUInt64LE(t) : BigInt(b.readUInt32LE(t));
      if (v === 0n) break;
      total++;
      if (fns.length >= maxFns) continue;
      const ordinal = pe.is64 ? v >> 63n : v >> 31n;
      if (ordinal) fns.push("#" + Number(v & 0xffffn));
      else fns.push(cstr(b, pe.off(Number(v & 0x7fffffffn)) + 2, 128));
    }
    if (out.length < maxDlls) out.push({ dll, fns, total });
  }
  return out;
}

function peExports(b, pe, max = 300) {
  const d = pe.dirs[0];
  if (!d || !d.rva) return null;
  const p = pe.off(d.rva);
  if (p < 0 || p + 40 > b.length) return null;
  const n = b.readUInt32LE(p + 24);
  const names = pe.off(b.readUInt32LE(p + 32));
  const out = [];
  for (let i = 0; i < Math.min(n, max) && names > 0; i++) out.push(cstr(b, pe.off(b.readUInt32LE(names + i * 4)), 200));
  return { name: cstr(b, pe.off(b.readUInt32LE(p + 12))), count: n, names: out };
}

// ECMA-335 II.22 table schemas for tables 0x00-0x29 (enough to locate every table up to NestedClass).
// u1/u2/u4 fixed, s = #Strings index, g = #GUID, b = #Blob, t<N> = index into table N, c<Name> = coded index.
const CODED = {
  TypeDefOrRef: [2, [0x02, 0x01, 0x1b]],
  HasConstant: [2, [0x04, 0x08, 0x17]],
  HasCustomAttribute: [5, [0x06, 0x04, 0x01, 0x02, 0x08, 0x09, 0x0a, 0x00, 0x0e, 0x17, 0x14, 0x11, 0x1a, 0x1b, 0x20, 0x23, 0x26, 0x27, 0x28, 0x2a, 0x2c, 0x2b]],
  HasFieldMarshal: [1, [0x04, 0x08]],
  HasDeclSecurity: [2, [0x02, 0x06, 0x20]],
  MemberRefParent: [3, [0x02, 0x01, 0x1a, 0x06, 0x1b]],
  HasSemantics: [1, [0x14, 0x17]],
  MethodDefOrRef: [1, [0x06, 0x0a]],
  MemberForwarded: [1, [0x04, 0x06]],
  Implementation: [2, [0x26, 0x23, 0x27]],
  CustomAttributeType: [3, [0x06, 0x0a]],
  ResolutionScope: [2, [0x00, 0x1a, 0x23, 0x01]],
};
const SCHEMA = [
  /*00 Module*/ ["u2", "s", "g", "g", "g"],
  /*01 TypeRef*/ ["cResolutionScope", "s", "s"],
  /*02 TypeDef*/ ["u4", "s", "s", "cTypeDefOrRef", "t4", "t6"],
  /*03 FieldPtr*/ ["t4"],
  /*04 Field*/ ["u2", "s", "b"],
  /*05 MethodPtr*/ ["t6"],
  /*06 MethodDef*/ ["u4", "u2", "u2", "s", "b", "t8"],
  /*07 ParamPtr*/ ["t8"],
  /*08 Param*/ ["u2", "u2", "s"],
  /*09 InterfaceImpl*/ ["t2", "cTypeDefOrRef"],
  /*0A MemberRef*/ ["cMemberRefParent", "s", "b"],
  /*0B Constant*/ ["u1", "u1", "cHasConstant", "b"],
  /*0C CustomAttribute*/ ["cHasCustomAttribute", "cCustomAttributeType", "b"],
  /*0D FieldMarshal*/ ["cHasFieldMarshal", "b"],
  /*0E DeclSecurity*/ ["u2", "cHasDeclSecurity", "b"],
  /*0F ClassLayout*/ ["u2", "u4", "t2"],
  /*10 FieldLayout*/ ["u4", "t4"],
  /*11 StandAloneSig*/ ["b"],
  /*12 EventMap*/ ["t2", "t20"],
  /*13 EventPtr*/ ["t20"],
  /*14 Event*/ ["u2", "s", "cTypeDefOrRef"],
  /*15 PropertyMap*/ ["t2", "t23"],
  /*16 PropertyPtr*/ ["t23"],
  /*17 Property*/ ["u2", "s", "b"],
  /*18 MethodSemantics*/ ["u2", "t6", "cHasSemantics"],
  /*19 MethodImpl*/ ["t2", "cMethodDefOrRef", "cMethodDefOrRef"],
  /*1A ModuleRef*/ ["s"],
  /*1B TypeSpec*/ ["b"],
  /*1C ImplMap*/ ["u2", "cMemberForwarded", "s", "t26"],
  /*1D FieldRVA*/ ["u4", "t4"],
  /*1E ENCLog*/ ["u4", "u4"],
  /*1F ENCMap*/ ["u4"],
  /*20 Assembly*/ ["u4", "u2", "u2", "u2", "u2", "u4", "b", "s", "s"],
  /*21 AssemblyProcessor*/ ["u4"],
  /*22 AssemblyOS*/ ["u4", "u4", "u4"],
  /*23 AssemblyRef*/ ["u2", "u2", "u2", "u2", "u4", "b", "s", "s", "b"],
  /*24 AssemblyRefProcessor*/ ["u4", "t35"],
  /*25 AssemblyRefOS*/ ["u4", "u4", "u4", "t35"],
  /*26 File*/ ["u4", "s", "b"],
  /*27 ExportedType*/ ["u4", "u4", "s", "s", "cImplementation"],
  /*28 ManifestResource*/ ["u4", "u4", "s", "cImplementation"],
  /*29 NestedClass*/ ["t2", "t2"],
];

/** Read the CLI metadata of a .NET PE: assembly, references, resources, types and their members. */
function dotnetMetadata(b, pe) {
  const cli = pe.dirs[14];
  if (!cli || !cli.rva) return null;
  const co = pe.off(cli.rva);
  const mo = pe.off(b.readUInt32LE(co + 8));
  const cliFlags = b.readUInt32LE(co + 16);
  if (mo < 0 || b.readUInt32LE(mo) !== 0x424a5342) return { error: "metadata signature not found" };
  const vlen = b.readUInt32LE(mo + 12);
  const runtime = cstr(b, mo + 16, vlen);
  let p = mo + 16 + vlen + 2;
  const nStreams = b.readUInt16LE(p);
  p += 2;
  const streams = {};
  for (let i = 0; i < nStreams; i++) {
    const off = b.readUInt32LE(p);
    const size = b.readUInt32LE(p + 4);
    const name = cstr(b, p + 8, 32);
    streams[name] = { off: mo + off, size };
    p += 8 + ((name.length + 4) & ~3);
  }
  const ts = streams["#~"] || streams["#-"];
  if (!ts) return { runtime, error: "no metadata tables stream" };
  let t = ts.off;
  const heap = b[t + 6];
  const valid = b.readBigUInt64LE(t + 8);
  t += 24;
  const rows = new Array(64).fill(0);
  for (let i = 0; i < 64; i++) {
    if ((valid >> BigInt(i)) & 1n) {
      rows[i] = b.readUInt32LE(t);
      t += 4;
    }
  }
  if (heap & 0x40) t += 4; // extra data
  const sz = { s: heap & 1 ? 4 : 2, g: heap & 2 ? 4 : 2, b: heap & 4 ? 4 : 2 };
  const colSize = (c) => {
    if (c === "u1") return 1;
    if (c === "u2") return 2;
    if (c === "u4") return 4;
    if (c === "s" || c === "g" || c === "b") return sz[c];
    if (c[0] === "t") return rows[Number(c.slice(1))] < 0x10000 ? 2 : 4;
    const [bits, tabs] = CODED[c.slice(1)];
    const max = Math.max(...tabs.map((x) => rows[x]));
    return max < 1 << (16 - bits) ? 2 : 4;
  };
  const layout = SCHEMA.map((cols) => {
    const offs = [];
    let o = 0;
    for (const c of cols) {
      offs.push(o);
      o += colSize(c);
    }
    return { cols, offs, size: o };
  });
  const start = [];
  for (let i = 0; i < SCHEMA.length; i++) {
    start[i] = t;
    t += rows[i] * layout[i].size;
  }
  const cell = (tab, row, col) => {
    const L = layout[tab];
    const at = start[tab] + (row - 1) * L.size + L.offs[col];
    const n = colSize(L.cols[col]);
    return n === 1 ? b[at] : n === 2 ? b.readUInt16LE(at) : b.readUInt32LE(at);
  };
  const strs = streams["#Strings"] || { off: 0 };
  const blobs = streams["#Blob"] || { off: 0 };
  const str = (i) => cstr(b, strs.off + i, 1024);
  const decoded = (name, v) => {
    const [bits, tabs] = CODED[name];
    return { table: tabs[v & ((1 << bits) - 1)], row: v >>> bits };
  };
  const typeName = (tab, row) => {
    if (!row) return "";
    if (tab === 0x02) return [str(cell(2, row, 2)), str(cell(2, row, 1))].filter(Boolean).join(".");
    if (tab === 0x01) return [str(cell(1, row, 2)), str(cell(1, row, 1))].filter(Boolean).join(".");
    if (tab === 0x1b) return "(generic instance)";
    return "";
  };
  /** Number of parameters from a method signature blob. */
  const paramCount = (blobIdx) => {
    let q = blobs.off + blobIdx;
    const comp = () => {
      const c = b[q];
      if ((c & 0x80) === 0) {
        q += 1;
        return c;
      }
      if ((c & 0xc0) === 0x80) {
        q += 2;
        return ((c & 0x3f) << 8) | b[q - 1];
      }
      q += 4;
      return ((c & 0x1f) << 24) | (b[q - 3] << 16) | (b[q - 2] << 8) | b[q - 1];
    };
    comp(); // blob length
    const conv = b[q++];
    if (conv & 0x10) comp(); // generic parameter count
    return comp();
  };

  const asm = rows[0x20]
    ? { name: str(cell(0x20, 1, 7)), version: [1, 2, 3, 4].map((k) => cell(0x20, 1, k)).join("."), culture: str(cell(0x20, 1, 8)) }
    : null;
  const refs = [];
  for (let r = 1; r <= rows[0x23]; r++) refs.push(str(cell(0x23, r, 6)) + " " + [0, 1, 2, 3].map((k) => cell(0x23, r, k)).join("."));
  const resources = [];
  for (let r = 1; r <= rows[0x28]; r++) resources.push(str(cell(0x28, r, 2)));
  const nested = new Map();
  for (let r = 1; r <= rows[0x29]; r++) nested.set(cell(0x29, r, 0), cell(0x29, r, 1));
  const types = [];
  const nTypes = rows[2];
  for (let r = 1; r <= nTypes; r++) {
    const flags = cell(2, r, 0);
    const name = str(cell(2, r, 1));
    const ns = str(cell(2, r, 2));
    const ext = decoded("TypeDefOrRef", cell(2, r, 3));
    const base = typeName(ext.table, ext.row);
    const f0 = cell(2, r, 4);
    const f1 = r < nTypes ? cell(2, r + 1, 4) : rows[4] + 1;
    const m0 = cell(2, r, 5);
    const m1 = r < nTypes ? cell(2, r + 1, 5) : rows[6] + 1;
    const methods = [];
    for (let m = m0; m < m1 && m <= rows[6]; m++) {
      const mf = cell(6, m, 2);
      let np = 0;
      try {
        np = paramCount(cell(6, m, 4));
      } catch {
        /* odd blob */
      }
      methods.push({ name: str(cell(6, m, 3)), params: np, pub: (mf & 7) === 6, isStatic: (mf & 0x10) !== 0 });
    }
    const fields = [];
    for (let f = f0; f < f1 && f <= rows[4]; f++) {
      const ff = cell(4, f, 0);
      fields.push({ name: str(cell(4, f, 1)), pub: (ff & 7) === 6, isStatic: (ff & 0x10) !== 0 });
    }
    let full = ns ? ns + "." + name : name;
    let outer = nested.get(r);
    for (let d = 0; outer && d < 8; d++) {
      full = typeName(2, outer) + "/" + full;
      outer = nested.get(outer);
    }
    let kind = flags & 0x20 ? "interface" : "class";
    if (base === "System.Enum") kind = "enum";
    else if (base === "System.ValueType") kind = "struct";
    else if (base === "System.MulticastDelegate") kind = "delegate";
    else if (kind === "class" && (flags & 0x180) === 0x180) kind = "static class";
    else if (kind === "class" && flags & 0x80) kind = "abstract class";
    const vis = flags & 7;
    types.push({ full, ns, kind, base, pub: vis === 1 || vis === 2, methods, fields, nested: nested.has(r) });
  }
  return { runtime, ilOnly: (cliFlags & 1) !== 0, asm, refs, resources, types, methodPtr: rows[5] > 0, counts: { types: nTypes, methods: rows[6], fields: rows[4], memberRefs: rows[0x0a] } };
}

function describeDotnet(md, filter) {
  const out = [];
  if (md.error) return [".NET metadata: " + md.error];
  out.push(".NET assembly: " + (md.asm ? md.asm.name + " " + md.asm.version + (md.asm.culture ? " (" + md.asm.culture + ")" : "") : "(module only)") + " · runtime " + md.runtime + (md.ilOnly ? " · IL only" : " · mixed mode"));
  out.push(md.counts.types + " types, " + md.counts.methods + " methods, " + md.counts.fields + " fields, " + md.counts.memberRefs + " member references");
  const refNames = md.refs.map((r) => r.split(" ")[0]);
  const frameworks = [];
  if (refNames.some((r) => /^UnityEngine/.test(r))) frameworks.push("Unity");
  if (refNames.some((r) => /^(0Harmony|HarmonyLib|Harmony)$/i.test(r))) frameworks.push("Harmony patches");
  if (refNames.some((r) => /^BepInEx/i.test(r))) frameworks.push("BepInEx plugin");
  if (refNames.some((r) => /^MelonLoader/i.test(r))) frameworks.push("MelonLoader mod");
  if (refNames.some((r) => /^Assembly-CSharp$/i.test(r))) frameworks.push("references the game's Assembly-CSharp");
  if (frameworks.length) out.push("Looks like: " + frameworks.join(", "));
  if (md.refs.length) out.push("References (" + md.refs.length + "): " + md.refs.slice(0, 60).join(", "));
  if (md.resources.length) out.push("Embedded resources (" + md.resources.length + "): " + md.resources.slice(0, 40).join(", "));
  if (md.methodPtr) out.push("(uncompressed metadata with pointer tables: member lists may be off)");
  const q = String(filter || "").toLowerCase();
  const fmtM = (m) => (m.isStatic ? "static " : "") + (m.pub ? "" : "~") + m.name + "(" + (m.params ? m.params : "") + ")";
  const fmtF = (f) => (f.isStatic ? "static " : "") + (f.pub ? "" : "~") + f.name;
  let shown = 0;
  let hidden = 0;
  const body = [];
  for (const t of md.types) {
    if (t.full === "<Module>") continue;
    const generated = /[<>]/.test(t.full);
    let methods = t.methods;
    let fields = t.fields;
    if (q) {
      const typeHit = t.full.toLowerCase().includes(q);
      if (!typeHit) {
        methods = methods.filter((m) => m.name.toLowerCase().includes(q));
        fields = fields.filter((f) => f.name.toLowerCase().includes(q));
        if (!methods.length && !fields.length) continue;
      }
    } else if (generated) {
      hidden++;
      continue;
    }
    if (shown >= (q ? 200 : 400)) {
      hidden++;
      continue;
    }
    shown++;
    const ms = methods.filter((m) => q || !/^[<.]|^get_|^set_|^add_|^remove_/.test(m.name) || m.name === ".ctor");
    const props = [...new Set(methods.filter((m) => /^get_|^set_/.test(m.name)).map((m) => m.name.slice(4)))];
    let line = (t.pub ? "" : "~") + t.kind + " " + t.full + (t.base && !/^System\.(Object|Enum|ValueType|MulticastDelegate)$/.test(t.base) ? " : " + t.base : "");
    const parts = [];
    if (t.kind === "enum") parts.push("values: " + fields.filter((f) => f.name !== "value__").map((f) => f.name).slice(0, 40).join(", "));
    else {
      if (ms.length) parts.push("methods: " + ms.slice(0, q ? 80 : 30).map(fmtM).join(", ") + (ms.length > (q ? 80 : 30) ? " …+" + (ms.length - (q ? 80 : 30)) : ""));
      if (props.length) parts.push("properties: " + props.slice(0, 30).join(", "));
      const fs2 = fields.filter((f) => !/BackingField/.test(f.name));
      if (fs2.length) parts.push("fields: " + fs2.slice(0, q ? 60 : 20).map(fmtF).join(", ") + (fs2.length > (q ? 60 : 20) ? " …+" + (fs2.length - (q ? 60 : 20)) : ""));
    }
    if (parts.length) line += "\n    " + parts.join("\n    ");
    body.push(line);
  }
  out.push("");
  out.push(q ? "Types/members matching \"" + filter + "\" (" + shown + "):" : "Types (~ = not public; " + shown + " shown):");
  out.push(...body);
  if (hidden) out.push("…" + hidden + " more types (compiler-generated or over the limit). Pass filter to narrow by type or member name.");
  out.push("Method bodies are not decompiled here; for IL/C# use a decompiler (e.g. ilspycmd) via Shell.");
  return out;
}

function describePe(b, filter) {
  const pe = parsePe(b);
  if (!pe) return ["MZ header without a valid PE header (DOS executable or damaged file)."];
  const out = [];
  const when = pe.time ? new Date(pe.time * 1000).toISOString().slice(0, 10) : "";
  out.push("PE " + (pe.is64 ? "PE32+" : "PE32") + " · " + pe.machine + " · " + (pe.dll ? "DLL" : "EXE") + " · " + pe.subsystem + (when ? " · timestamp " + when + " (a build hash on reproducible builds)" : ""));
  out.push("Sections: " + pe.sections.map((s) => s.name + " " + fmtBytes(s.rawSize)).join(", "));
  const md = pe.dirs[14] && pe.dirs[14].rva ? dotnetMetadata(b, pe) : null;
  if (md) return out.concat(describeDotnet(md, filter));
  const imps = peImports(b, pe);
  if (imps.length) {
    out.push("Imports (" + imps.length + " DLLs):");
    for (const i of imps) out.push("  " + i.dll + " (" + i.total + "): " + i.fns.join(", ") + (i.total > i.fns.length ? " …" : ""));
  }
  const exp = peExports(b, pe);
  if (exp && exp.count) {
    const q = String(filter || "").toLowerCase();
    const names = q ? exp.names.filter((n) => n.toLowerCase().includes(q)) : exp.names;
    out.push("Exports of " + exp.name + " (" + exp.count + (q ? ", matching \"" + filter + "\": " + names.length : "") + "): " + names.join(", ") + (exp.count > exp.names.length ? " …" : ""));
  }
  if (pe.dirs[2] && pe.dirs[2].rva) out.push("Has a resource section (icons, version info, manifests).");
  return out;
}

// ---------------------------------------------------------------- archives

/** Random-access reader over a file or a buffer. */
function source(src) {
  if (Buffer.isBuffer(src)) return { size: src.length, read: (pos, len) => src.subarray(pos, Math.min(src.length, pos + len)), close() {} };
  const fd = fs.openSync(src, "r");
  const size = fs.fstatSync(fd).size;
  return {
    size,
    read(pos, len) {
      const n = Math.max(0, Math.min(len, size - pos));
      const buf = Buffer.alloc(n);
      if (n) fs.readSync(fd, buf, 0, n, pos);
      return buf;
    },
    close() {
      fs.closeSync(fd);
    },
  };
}

function zipEntries(src) {
  const tailLen = Math.min(src.size, 65557 + 22);
  const tail = src.read(src.size - tailLen, tailLen);
  let e = -1;
  for (let i = tail.length - 22; i >= 0; i--) {
    if (tail.readUInt32LE(i) === 0x06054b50) {
      e = i;
      break;
    }
  }
  if (e < 0) throw new Error("ZIP end-of-central-directory record not found (truncated or not a ZIP)");
  let count = tail.readUInt16LE(e + 10);
  let cdSize = tail.readUInt32LE(e + 12);
  let cdOff = tail.readUInt32LE(e + 16);
  if (cdOff === 0xffffffff || count === 0xffff) {
    const loc = e - 20;
    if (loc >= 0 && tail.readUInt32LE(loc) === 0x07064b50) {
      const rec = src.read(Number(tail.readBigUInt64LE(loc + 8)), 56);
      count = Number(rec.readBigUInt64LE(32));
      cdSize = Number(rec.readBigUInt64LE(40));
      cdOff = Number(rec.readBigUInt64LE(48));
    }
  }
  const cd = src.read(cdOff, Math.min(cdSize, 64 * 1024 * 1024));
  const out = [];
  let p = 0;
  for (let i = 0; i < count && p + 46 <= cd.length; i++) {
    if (cd.readUInt32LE(p) !== 0x02014b50) break;
    const nlen = cd.readUInt16LE(p + 28);
    const elen = cd.readUInt16LE(p + 30);
    const clen = cd.readUInt16LE(p + 32);
    const ent = {
      name: cd.toString("utf8", p + 46, p + 46 + nlen),
      method: cd.readUInt16LE(p + 10),
      csize: cd.readUInt32LE(p + 20),
      size: cd.readUInt32LE(p + 24),
      local: cd.readUInt32LE(p + 42),
    };
    // Zip64 sizes / offset live in the extra field.
    if (ent.size === 0xffffffff || ent.csize === 0xffffffff || ent.local === 0xffffffff) {
      let x = p + 46 + nlen;
      const xe = x + elen;
      while (x + 4 <= xe) {
        const id = cd.readUInt16LE(x);
        const len = cd.readUInt16LE(x + 2);
        if (id === 1) {
          let q = x + 4;
          if (ent.size === 0xffffffff) (ent.size = Number(cd.readBigUInt64LE(q)), (q += 8));
          if (ent.csize === 0xffffffff) (ent.csize = Number(cd.readBigUInt64LE(q)), (q += 8));
          if (ent.local === 0xffffffff) ent.local = Number(cd.readBigUInt64LE(q));
        }
        x += 4 + len;
      }
    }
    out.push(ent);
    p += 46 + nlen + elen + clen;
  }
  return out;
}

function zipRead(src, ent) {
  if (ent.size > 64 * 1024 * 1024) throw new Error(ent.name + " is " + fmtBytes(ent.size) + "; too large to extract here");
  const h = src.read(ent.local, 30);
  if (h.readUInt32LE(0) !== 0x04034b50) throw new Error("bad local header for " + ent.name);
  const data = src.read(ent.local + 30 + h.readUInt16LE(26) + h.readUInt16LE(28), ent.csize);
  if (ent.method === 0) return data;
  if (ent.method === 8) return zlib.inflateRawSync(data);
  throw new Error(ent.name + " uses compression method " + ent.method + " (only stored and deflate are supported; use 7-Zip via Shell)");
}

function zipFlavor(names) {
  const has = (re) => names.some((n) => re.test(n));
  if (has(/^\[Content_Types\]\.xml$/) && has(/^word\//)) return "Word document (DOCX)";
  if (has(/^\[Content_Types\]\.xml$/) && has(/^xl\//)) return "Excel workbook (XLSX)";
  if (has(/^\[Content_Types\]\.xml$/) && has(/^ppt\//)) return "PowerPoint deck (PPTX)";
  if (has(/^extension\.vsixmanifest$/)) return "VS Code extension (VSIX)";
  if (has(/^AndroidManifest\.xml$/)) return "Android package (APK)";
  if (has(/\.nuspec$/)) return "NuGet package";
  if (has(/^META-INF\/MANIFEST\.MF$/)) return "Java archive (JAR)";
  if (has(/^mimetype$/) && has(/\.opf$/)) return "EPUB book";
  return "";
}

function xmlText(xml) {
  return String(xml)
    .replace(/<\/(w:p|a:p|text:p|p|div|row|si)>/gi, "\n")
    .replace(/<w:tab\/>/g, "\t")
    .replace(/<[^>]+>/g, "")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&quot;/g, '"')
    .replace(/&apos;/g, "'")
    .replace(/&amp;/g, "&")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}

function tarEntries(buf) {
  const out = [];
  let p = 0;
  while (p + 512 <= buf.length && out.length < 5000) {
    const h = buf.subarray(p, p + 512);
    if (h.every((c) => c === 0)) break;
    let name = cstr(h, 0, 100);
    if (ascii(h, 257, 5) === "ustar") {
      const prefix = cstr(h, 345, 155);
      if (prefix) name = prefix + "/" + name;
    }
    const size = parseInt(cstr(h, 124, 12).trim() || "0", 8) || 0;
    const type = String.fromCharCode(h[156] || 48);
    out.push({ name: name + (type === "5" ? "/" : ""), size, data: p + 512 });
    p += 512 + Math.ceil(size / 512) * 512;
  }
  return out;
}

// ---------------------------------------------------------------- PDF

function pdfString(s) {
  return s.replace(/\\(\d{1,3}|.)/gs, (_, c) => {
    if (/^\d/.test(c)) return String.fromCharCode(parseInt(c, 8));
    return { n: "\n", r: "", t: "\t", b: "", f: "", "(": "(", ")": ")", "\\": "\\", "\n": "" }[c] ?? c;
  });
}

function pdfHex(h) {
  const hex = h.replace(/\s+/g, "");
  const bytes = Buffer.from(hex.length % 2 ? hex + "0" : hex, "hex");
  if (bytes[0] === 0xfe && bytes[1] === 0xff) {
    const sw = Buffer.from(bytes.subarray(2, 2 + ((bytes.length - 2) & ~1)));
    sw.swap16();
    return sw.toString("utf16le");
  }
  return bytes.toString("latin1");
}

/** Text shown by BT…ET blocks of a content stream (Tj, TJ, ', "). */
function pdfContentText(s) {
  const out = [];
  const re = /BT([\s\S]*?)ET/g;
  let m;
  while ((m = re.exec(s))) {
    const blk = m[1];
    const tok = /\((?:\\.|[^\\)])*\)|<[0-9A-Fa-f\s]*>|\[|\]|-?\d*\.?\d+|T[jJ*dDm]|'|"/g;
    let t;
    let line = "";
    let inArr = false;
    while ((t = tok.exec(blk))) {
      const v = t[0];
      if (v[0] === "(") line += pdfString(v.slice(1, -1));
      else if (v[0] === "<") line += pdfHex(v.slice(1, -1));
      else if (v === "[") inArr = true;
      else if (v === "]") inArr = false;
      else if (/^-?\d/.test(v)) {
        if (inArr && Number(v) < -180) line += " ";
      } else if (v === "T*" || v === "Td" || v === "TD" || v === "'" || v === '"') line += "\n";
    }
    out.push(line);
  }
  return out.join("\n");
}

function describePdf(b) {
  const s = b.toString("latin1");
  const out = [];
  const pages = (s.match(/\/Type\s*\/Page(?![s\w])/g) || []).length;
  const meta = [];
  for (const k of ["Title", "Author", "Subject", "Creator", "Producer", "CreationDate"]) {
    const m = s.match(new RegExp("/" + k + "\\s*\\(((?:\\\\.|[^\\\\)])*)\\)")) || s.match(new RegExp("/" + k + "\\s*<([0-9A-Fa-f\\s]+)>"));
    if (m) meta.push(k + ": " + (m[0].includes("(") ? pdfString(m[1]) : pdfHex(m[1])).slice(0, 200));
  }
  out.push("PDF " + s.slice(5, 8) + " · " + (pages || "?") + " page(s)" + (/\/Encrypt\b/.test(s) ? " · encrypted" : ""));
  if (meta.length) out.push(...meta);
  const texts = [];
  const re = /stream\r?\n/g;
  let m;
  let total = 0;
  while ((m = re.exec(s)) && total < 400000) {
    const begin = m.index + m[0].length;
    const end = s.indexOf("endstream", begin);
    if (end < 0) break;
    const dict = s.slice(Math.max(0, m.index - 600), m.index);
    const d = dict.slice(dict.lastIndexOf("<<"));
    if (/\/Subtype\s*\/Image|\/Type\s*\/(XObject|Metadata|XRef|ObjStm)|\/Length1/.test(d)) {
      re.lastIndex = end;
      continue;
    }
    let data = b.subarray(begin, end);
    if (/\/FlateDecode/.test(d)) {
      try {
        data = zlib.inflateSync(data);
      } catch {
        try {
          data = zlib.inflateSync(data, { finishFlush: zlib.constants.Z_SYNC_FLUSH });
        } catch {
          re.lastIndex = end;
          continue;
        }
      }
    } else if (/\/Filter/.test(d)) {
      re.lastIndex = end;
      continue;
    }
    const txt = pdfContentText(data.toString("latin1"));
    if (txt.trim()) {
      texts.push(txt);
      total += txt.length;
    }
    re.lastIndex = end;
  }
  const text = texts.join("\n").replace(/[ \t]+\n/g, "\n").replace(/\n{3,}/g, "\n\n").trim();
  const printable = text.replace(/[^\x20-\x7e\n\t\u00a0-\u024f]/g, "").length;
  if (!text) out.push("No extractable text (scanned pages, or text in embedded-font encodings). Render a page to an image to look at it, or use pdftotext via Shell if installed.");
  else if (printable < text.length * 0.7) out.push("Text is mostly in embedded-font encodings and cannot be decoded here. Use pdftotext via Shell if installed.\nSample: " + text.slice(0, 300));
  else out.push("Text (" + text.length + " chars):\n" + text);
  return out;
}

// ---------------------------------------------------------------- optional helpers (pdf.js, 7-Zip)
// Both are found at run time and never bundled: pdf.js (pdfjs-dist, Apache-2.0) from the folder
// Tools\Fetch-ThirdParty.ps1 -AgentBridge fills, 7-Zip (LGPL) as an installed program run as a process.

/** pdfjs-dist's Node build under one of the third-party folders, or "". */
function findPdfjs(dirs) {
  for (const d of dirs || []) {
    for (const rel of [["node", "node_modules"], ["node_modules"]]) {
      const f = path.join(d, ...rel, "pdfjs-dist", "legacy", "build", "pdf.mjs");
      if (fs.existsSync(f)) return f;
    }
  }
  return "";
}

/** "3", "2-5", "1,4,7-9" → sorted unique 1-based page numbers within 1..n (empty spec = all). */
function parsePages(spec, n) {
  const s = String(spec == null ? "" : spec).trim();
  if (!s) return Array.from({ length: n }, (_, i) => i + 1);
  const out = new Set();
  for (const part of s.split(/[,\s]+/)) {
    const m = part.match(/^(\d+)(?:-(\d*))?$/);
    if (!m) continue;
    const a = Math.max(1, +m[1]);
    const b = Math.min(n, m[2] === undefined ? a : m[2] === "" ? n : +m[2]);
    for (let p = a; p <= b; p++) out.add(p);
  }
  return [...out].sort((x, y) => x - y);
}

/**
 * PDF text through pdf.js: handles compressed object streams, font encodings and encryption that
 * describePdf cannot. Returns null when pdf.js is not installed.
 * @param {string|Buffer} src
 * @param {{dirs?:string[], pages?:string, maxChars?:number}} [o]
 * @returns {Promise<{lines:string[], pages:number}|null>}
 */
async function pdfjsText(src, o = {}) {
  const mod = findPdfjs(o.dirs);
  if (!mod) return null;
  const pdfjs = await import(require("url").pathToFileURL(mod).href);
  const data = new Uint8Array(typeof src === "string" ? readCapped(src, 200 * 1024 * 1024) : src);
  const doc = await pdfjs.getDocument({ data, isEvalSupported: false, disableFontFace: true, useSystemFonts: false, verbosity: 0 }).promise;
  try {
    const max = o.maxChars || 40000;
    const lines = ["PDF (pdf.js) · " + doc.numPages + " page(s)"];
    try {
      const meta = await doc.getMetadata();
      const info = (meta && meta.info) || {};
      for (const k of ["Title", "Author", "Subject", "Creator", "Producer", "CreationDate"]) if (info[k]) lines.push(k + ": " + String(info[k]).slice(0, 200));
      if (info.EncryptFilterName) lines.push("Encrypted (" + info.EncryptFilterName + "), opened without a password");
    } catch {
      /* no metadata */
    }
    const want = parsePages(o.pages, doc.numPages);
    let total = 0;
    let last = 0;
    let empty = 0;
    const body = [];
    for (const p of want) {
      if (total >= max) break;
      const page = await doc.getPage(p);
      const tc = await page.getTextContent();
      const t = tc.items.map((i) => (i.str || "") + (i.hasEOL ? "\n" : "")).join("").replace(/[ \t]+\n/g, "\n").replace(/\n{3,}/g, "\n\n").trim();
      page.cleanup();
      last = p;
      if (!t) {
        empty++;
        continue;
      }
      const chunk = "--- page " + p + " ---\n" + t;
      body.push(total + chunk.length > max ? chunk.slice(0, max - total) + "\n…" : chunk);
      total += chunk.length;
    }
    if (!body.length) lines.push("No text on " + (want.length === doc.numPages ? "any page" : "pages " + o.pages) + " (scanned images, most likely).");
    else {
      if (empty) lines.push(empty + " page(s) without text (scanned images, most likely).");
      lines.push(...body);
      const rest = want.filter((p) => p > last);
      if (rest.length) lines.push("…stopped at page " + last + " (" + max + " characters). Pass pages=\"" + rest[0] + "-" + rest[rest.length - 1] + "\" for more.");
    }
    return { lines, pages: doc.numPages };
  } finally {
    await doc.destroy();
  }
}

/** 7z.exe from 7-Zip's install folders or PATH, or "". */
function find7z() {
  const c = [];
  for (const v of ["ProgramFiles", "ProgramW6432", "ProgramFiles(x86)"]) if (process.env[v]) c.push(path.join(process.env[v], "7-Zip", "7z.exe"));
  for (const d of String(process.env.PATH || "").split(path.delimiter)) if (d) c.push(path.join(d, process.platform === "win32" ? "7z.exe" : "7z"));
  return c.find((f) => {
    try {
      return fs.statSync(f).isFile();
    } catch {
      return false;
    }
  }) || "";
}

function run7z(exe, args, { maxBytes = 64 * 1024 * 1024, timeoutMs = 60000 } = {}) {
  return new Promise((resolve, reject) => {
    const p = spawn(exe, args, { windowsHide: true });
    const out = [];
    let n = 0;
    let err = "";
    const timer = setTimeout(() => {
      p.kill();
      reject(new Error("7-Zip timed out"));
    }, timeoutMs);
    p.stdout.on("data", (d) => {
      n += d.length;
      if (n > maxBytes) {
        p.kill();
        clearTimeout(timer);
        reject(new Error("output larger than " + fmtBytes(maxBytes)));
        return;
      }
      out.push(d);
    });
    p.stderr.on("data", (d) => (err = (err + d).slice(-2000)));
    p.on("error", (e) => {
      clearTimeout(timer);
      reject(e);
    });
    p.on("close", (code) => {
      clearTimeout(timer);
      if (code && code !== 1) reject(new Error("7-Zip exit " + code + (err.trim() ? ": " + err.trim().split(/\r?\n/).pop() : "")));
      else resolve(Buffer.concat(out));
    });
  });
}

/** Entries of anything 7-Zip opens (7z, RAR, XZ, BZip2, CAB, ISO, MSI, ...): [{name, size}]. */
async function sevenZipList(abs, exe = find7z()) {
  if (!exe) return null;
  const txt = (await run7z(exe, ["l", "-slt", "-ba", "-sccUTF-8", "-p", abs])).toString("utf8");
  const list = [];
  for (const block of txt.split(/\r?\n\r?\n/)) {
    const name = (block.match(/^Path = (.*)$/m) || [])[1];
    if (!name) continue;
    const dir = /^Attributes = D/m.test(block) || /^Folder = \+/m.test(block);
    list.push({ name: name.replace(/\\/g, "/") + (dir ? "/" : ""), size: +((block.match(/^Size = (\d+)/m) || [])[1] || 0) });
  }
  return list;
}

/** One entry's bytes, through 7-Zip. */
async function sevenZipRead(abs, entry, exe = find7z()) {
  return run7z(exe, ["e", "-so", "-p", abs, entry]);
}

/**
 * AnalyzeFile for formats 7-Zip handles. Returns null when 7-Zip is not installed.
 * @returns {Promise<{text:string, image?:{buf:Buffer,name:string}|null}|null>}
 */
async function sevenZipDescribe(abs, { entry, filter, exe = find7z() } = {}) {
  if (!exe) return null;
  const list = await sevenZipList(abs, exe);
  const head = [abs + " · " + fmtBytes(fs.statSync(abs).size) + " · read with 7-Zip"];
  if (!entry) return { text: head.concat(listing(list, list.reduce((a, e) => a + e.size, 0))).join("\n"), image: null };
  const ent = findEntry(list, entry);
  if (!ent) return { text: head.concat(["No entry matching \"" + entry + "\". First entries: " + list.slice(0, 20).map((e) => e.name).join(", ")]).join("\n"), image: null };
  const data = await sevenZipRead(abs, ent.name.replace(/\/$/, ""), exe);
  const d = detect(data, ent.name);
  if (d.kind === "image") return { text: head.concat(["Entry " + ent.name + ": " + d.label + " · " + fmtBytes(data.length)]).join("\n"), image: { buf: data, name: ent.name } };
  if (d.kind === "text") {
    const t = decodeText(data);
    return { text: head.concat(["Entry " + ent.name + " (" + t.split(/\r?\n/).length + " lines):", t.slice(0, 40000)]).join("\n"), image: null };
  }
  const inner = analyzeFile(data, { name: ent.name, filter, depth: 1 });
  return { text: head.concat(["Entry " + ent.name + ":", inner.text]).join("\n"), image: inner.image };
}

/** Formats AnalyzeFile hands to 7-Zip when it is installed. */
const SEVEN_ZIP_FORMATS = new Set(["7z", "rar", "xz", "bzip2", "zstd", "cab", "iso", "msi"]);

// ---------------------------------------------------------------- fallback

function hexDump(b, n = 256) {
  const rows = [];
  for (let o = 0; o < Math.min(n, b.length); o += 16) {
    const row = b.subarray(o, Math.min(o + 16, b.length));
    const hex = [...row].map((c) => c.toString(16).padStart(2, "0")).join(" ");
    rows.push(o.toString(16).padStart(8, "0") + "  " + hex.padEnd(48) + "  " + [...row].map((c) => (c >= 32 && c < 127 ? String.fromCharCode(c) : ".")).join(""));
  }
  return rows.join("\n");
}

/** Printable ASCII and UTF-16LE runs, like `strings`. */
function strings(b, { min = 6, max = 120, limit = 8 * 1024 * 1024 } = {}) {
  const s = b.subarray(0, limit);
  const out = new Set();
  const latin = s.toString("latin1");
  for (const m of latin.matchAll(new RegExp("[\\x20-\\x7e]{" + min + ",}", "g"))) {
    out.add(m[0].slice(0, 200));
    if (out.size >= max) break;
  }
  if (out.size < max) {
    for (const m of latin.matchAll(new RegExp("(?:[\\x20-\\x7e]\\x00){" + min + ",}", "g"))) {
      out.add(m[0].replace(/\x00/g, "").slice(0, 200) + "  (UTF-16)");
      if (out.size >= max) break;
    }
  }
  return [...out];
}

// ---------------------------------------------------------------- analyzeFile

function findEntry(list, want) {
  const w = String(want).replace(/\\/g, "/").replace(/^\/+/, "").toLowerCase();
  return list.find((e) => e.name.toLowerCase() === w) || list.find((e) => e.name.toLowerCase().endsWith("/" + w)) || list.find((e) => e.name.toLowerCase().endsWith(w));
}

function listing(list, total) {
  const files = list.filter((e) => !e.name.endsWith("/"));
  const rows = files.slice(0, 300).map((e) => fmtBytes(e.size).padStart(10) + "  " + e.name);
  if (files.length > 300) rows.push("…" + (files.length - 300) + " more entries");
  return [files.length + " files" + (total != null ? ", " + fmtBytes(total) + " uncompressed" : "") + ":", ...rows, "Pass entry=<name> to read one entry (text, image, or a nested binary)."];
}

/**
 * Text summary of a file the model cannot read as text.
 * @param {string|Buffer} src absolute path, or bytes (then pass opts.name)
 * @param {{name?:string, filter?:string, entry?:string, depth?:number}} [opts]
 * @returns {{text:string, kind:string, format:string, image?:{buf:Buffer,name:string}|null}}
 */
function analyzeFile(src, opts = {}) {
  const isPath = typeof src === "string";
  const name = isPath ? src : opts.name || "data";
  const size = isPath ? fs.statSync(src).size : src.length;
  let head;
  if (isPath) {
    const s = source(src);
    try {
      head = s.read(0, 65536);
    } finally {
      s.close();
    }
  } else head = src.subarray(0, 65536);
  const det = detect(head, name);
  const lines = [name + " · " + det.label + " · " + fmtBytes(size)];
  const res = (extra) => ({ text: lines.concat(extra || []).join("\n"), kind: det.kind, format: det.format, image: null });
  const whole = () => (isPath ? readCapped(src) : src);
  const depth = opts.depth || 0;
  /** Read one archive entry: images go to the model, text is shown, binaries are analysed in turn. */
  const fromEntry = (entName, data) => {
    const d = detect(data, entName);
    if (d.kind === "image") {
      const info = imageInfo(data, d.format);
      lines.push("Entry " + entName + ": " + d.label + (info ? " " + info.width + "x" + info.height : "") + " · " + fmtBytes(data.length));
      return { ...res(), image: { buf: data, name: entName } };
    }
    if (d.kind === "text") {
      const t = decodeText(data);
      return res(["Entry " + entName + " (" + t.split(/\r?\n/).length + " lines):", t.slice(0, 40000)]);
    }
    if (depth >= 2) return res(["Entry " + entName + ": " + d.label + " · " + fmtBytes(data.length)]);
    const inner = analyzeFile(data, { name: entName, filter: opts.filter, depth: depth + 1 });
    return { ...res(["Entry " + entName + ":", inner.text]), image: inner.image };
  };

  try {
    if (det.kind === "image") {
      const info = imageInfo(head.length >= size ? head : whole(), det.format);
      if (info) lines.push(info.width + "x" + info.height + (info.detail ? " · " + info.detail : ""));
      return { ...res(), image: { buf: isPath ? null : src, name } };
    }
    if (det.kind === "text") {
      const t = decodeText(whole());
      const n = t.split(/\r?\n/).length;
      return res([n + " lines (" + (det.format === "utf16" ? "UTF-16" : "UTF-8/ASCII") + "). Use Read for numbered lines. First lines:", t.split(/\r?\n/).slice(0, 30).join("\n")]);
    }
    switch (det.format) {
      case "pe":
        return res(describePe(whole(), opts.filter));
      case "pdf":
        return res(describePdf(whole()));
      case "zip": {
        const s = source(src);
        try {
          const list = zipEntries(s);
          const flavor = zipFlavor(list.map((e) => e.name));
          if (flavor) lines[0] += " · " + flavor;
          if (opts.entry) {
            const ent = findEntry(list, opts.entry);
            if (!ent) return res(["No entry matching \"" + opts.entry + "\". " + list.length + " entries; first: " + list.slice(0, 20).map((e) => e.name).join(", ")]);
            return fromEntry(ent.name, zipRead(s, ent));
          }
          const extra = listing(list, list.reduce((a, e) => a + e.size, 0));
          const doc = flavor.startsWith("Word") ? findEntry(list, "word/document.xml") : null;
          if (doc) extra.push("", "Document text:", xmlText(zipRead(s, doc).toString("utf8")).slice(0, 20000));
          return res(extra);
        } finally {
          s.close();
        }
      }
      case "tar": {
        const b = whole();
        const list = tarEntries(b);
        if (opts.entry) {
          const ent = findEntry(list, opts.entry);
          if (!ent) return res(["No entry matching \"" + opts.entry + "\"."]);
          return fromEntry(ent.name, b.subarray(ent.data, ent.data + ent.size));
        }
        return res(listing(list, list.reduce((a, e) => a + e.size, 0)));
      }
      case "gzip": {
        const inner = zlib.gunzipSync(whole());
        const innerName = String(name).replace(/\.(t?gz)$/i, (m) => (m.toLowerCase() === ".tgz" ? ".tar" : ""));
        lines.push("Decompressed: " + fmtBytes(inner.length));
        if (depth >= 2) return res();
        const sub = analyzeFile(inner, { name: innerName, filter: opts.filter, entry: opts.entry, depth: depth + 1 });
        return { ...res([sub.text]), image: sub.image };
      }
      case "7z":
      case "rar":
      case "xz":
      case "bzip2":
      case "zstd":
      case "cab":
      case "iso":
      case "msi":
        return res(["Not unpacked here. List it with 7-Zip through Shell: & \"C:\\Program Files\\7-Zip\\7z.exe\" l \"" + name + "\" (extract one file with: x -o<folder> \"" + name + "\" <entry>)."]);
      case "mpq": {
        const b = head;
        lines.push("MPQ format v" + (b.readUInt16LE(12) + 1) + ", archive size " + fmtBytes(b.readUInt32LE(8)) + ", hash table " + b.readUInt32LE(24) + " entries, block table " + b.readUInt32LE(28) + " entries");
        return res(["Files are hashed, so names need a listfile. Use an MPQ tool (e.g. MPQEditor / StormLib) through Shell to extract."]);
      }
      case "unitybundle":
        return res(["Unity bundle header: " + cstr(head, 0, 16) + " · format " + head.readUInt32BE(8) + " · player " + cstr(head, 12, 32) + " · engine " + cstr(head, 12 + cstr(head, 12, 32).length + 1, 32), "Extract assets with AssetRipper / UnityPy through Shell.", "Strings: " + strings(head, { max: 30 }).join(" | ")]);
      case "tesplugin":
        return res(["Bethesda plugin; record types and masters (from strings): " + strings(head, { min: 4, max: 40 }).slice(0, 40).join(" | "), "Use xEdit for full record views."]);
      default: {
        const b = isPath ? source(src) : null;
        let data = head;
        try {
          if (b) data = b.read(0, Math.min(size, 8 * 1024 * 1024));
        } finally {
          if (b) b.close();
        }
        const ss = strings(data);
        return res(["First bytes:", hexDump(head, 256), ss.length ? "Strings (" + ss.length + (ss.length >= 120 ? "+" : "") + "):\n" + ss.join("\n") : "No readable strings in the first 8 MB."]);
      }
    }
  } catch (e) {
    return res(["Could not analyse further: " + ((e && e.message) || e), "First bytes:", hexDump(head, 128)]);
  }
}

// ---------------------------------------------------------------- prompt image references

/**
 * Image paths / URLs mentioned in free text: absolute Windows paths (spaces allowed), UNC, ~\ paths,
 * file:/// URIs, http(s) URLs, markdown ![](...) targets, and bare relative paths like media/icon.png.
 * Relative ones are returned as written; the caller resolves them and keeps the ones that exist.
 */
function findImageRefs(text, max = 8) {
  const t = String(text || "");
  const found = [];
  const add = (v) => {
    const s = String(v || "").trim().replace(/^["'`<(]+|["'`>),.;:]+$/g, "");
    if (s && !found.some((f) => f.toLowerCase() === s.toLowerCase())) found.push(s);
  };
  const E = IMAGE_EXT_SRC;
  const pats = [
    new RegExp("https?://[^\\s<>\"')\\]]+?\\.(?:" + E + ")(?:\\?[^\\s<>\"')\\]]*)?(?![\\w])", "gi"),
    new RegExp("file:///?[^\\s<>\"')\\]]+?\\.(?:" + E + ")(?![\\w])", "gi"),
    new RegExp("(?:(?<![\\w/])[A-Za-z]:[\\\\/]|\\\\\\\\[^\\\\\\s]+\\\\)[^\\n\\r\"'<>|*?]*?\\.(?:" + E + ")(?![\\w])", "gi"),
    new RegExp("~[\\\\/][^\\n\\r\"'<>|*?]*?\\.(?:" + E + ")(?![\\w])", "gi"),
    new RegExp("!?\\[[^\\]]*\\]\\(<?([^)<>\\n]+?\\.(?:" + E + "))>?\\)", "gi"),
    new RegExp("(?<![\\w:\\\\/.~-])((?:\\.{1,2}[\\\\/])?(?:[\\w.-]+[\\\\/])*[\\w.-]+\\.(?:" + E + "))(?![\\w])", "gi"),
  ];
  for (const re of pats) {
    for (const m of t.matchAll(re)) {
      let v = m[1] || m[0];
      if (/^file:/i.test(v)) {
        try {
          v = decodeURIComponent(v.replace(/^file:\/\/\/?/i, ""));
        } catch {
          v = v.replace(/^file:\/\/\/?/i, "");
        }
      }
      // A fragment of a path already found (the relative pattern also hits the tail of absolute ones).
      if (found.some((f) => f.replace(/\\/g, "/").toLowerCase().endsWith(String(v).replace(/\\/g, "/").toLowerCase()))) continue;
      add(v);
      if (found.length >= max) return found;
    }
  }
  return found;
}

module.exports = {
  API_MIMES,
  MAX_IMAGE_BYTES,
  DEFAULT_MAX_EDGE,
  IMAGE_EXT,
  detect,
  decodeText,
  imageInfo,
  decodeBmp,
  decodeTga,
  decodeDds,
  downscale,
  encodePng,
  crc32,
  prepareImage,
  imageTokens,
  parsePe,
  dotnetMetadata,
  zipEntries,
  analyzeFile,
  findImageRefs,
  findPdfjs,
  parsePages,
  pdfjsText,
  find7z,
  sevenZipList,
  sevenZipDescribe,
  SEVEN_ZIP_FORMATS,
  hexDump,
  strings,
  fmtBytes,
};
