# Audio Bench, Listener, Agent and Seal

Four shared modules split sound work into deciding, doing, judging and shipping, so no model ever generates or
touches audio when a sound's source license bars AI tools, and every change is inspectable and repeatable.

| Module | Role | Touches audio? |
|---|---|---|
| `audio_agent.py` | **Local audio agent.** Reads the purpose, finds clips in the library (name search only for licensed tiers), decides layers, roles, gains, offsets and pitches from `analyze()` numbers, renders seeds through the bench and lets the listener pick. | Decides only. |
| `audio_bench.py` | **Programmatic bench.** Mixing, blending, texture layering, impact engine, boom randomizer, character bank and 46 effects as deterministic numpy/scipy processing, driven by a recipe. | Yes, by the recipe alone. No model inside. |
| `audio_listener.py` | **Read-only quality tuner.** The CLAP judge (`laion/clap-htsat-unfused`, CPU) scores sounds against their purpose, picks the best of several candidates, says whether a new version beats the old, and ranks a set. | Listens only. Nothing it produces ships. |
| `audio_rebuild.py` | **Rebuild from clips.** The production step behind the mods' licensed sounds: an anti-aliased (polyphase) pitch move, layers from the other clips, a random all-pass scramble that leaves the lowest band's phase alone, the lead clip's colour matched back, its first milliseconds kept for the attack, light glue and its loudness, tried until the result stays under a correlation bar against every clip, the listener choosing. Folder mode rebuilds every AAMT sidecar sound whose references include a pack that bars AI tools. | Yes, deterministic. |
| `audio_seal.py` | **Sealing.** Packs a mod's sounds into one scrambled archive (MTSA1) that a Lua or C++ reader unseals in memory, so no sound file sits loose in a mod. | Container only. |

The loop a person or an agent runs: `analyze` the sound (numbers), decide what it needs, write a recipe, `render`, then
`Listener.compare` or `pick` to judge, adjust, and finally `seal` for shipping.

## The program and the page

`Tools\AudioBench.exe` (source in `Tools/AudioBench`, .NET Framework 4.7.2 + WebView2) finds the toolkit and its
Python, starts `audio_bench_server.py` from the repo and shows the page in its own window with the server log. Menus
load sounds as sources, export the last render, restart the server, and open the catalog. `Tools\AudioBench-GUI.bat`
does the same in your browser. The page (`audio_bench_gui.html`) has:

- **Audio agent**: say what sound you need, pick a kind (impact, boom, texture, voice, plain or auto), how many seeds;
  the agent proposes a recipe with its sources loaded and the listener's pick playing. Then edit.
- **Sources**: import files, record from the microphone, add a path, search the asset library (tier shown).
- **Layers**: the first is the main sound. Each has gain, pitch, pan, offset, a band to sit in, `fit` (cut / stretch /
  loop / grains) and `follow` (its loudness follows another layer: texture layering). **Impact engine** makes punch,
  body and tail layers from one source; **Boom** stacks every loaded source with randomized role, gain, offset, pitch
  and pan from the seed (re-roll with a new seed); **Transmute** gives the main sound another source's loudness shape
  and colour.
- **Chains**: effects grouped (utility, tone, pitch & time, dynamics & drive, modulation, space & stereo, generators),
  presets grouped (character bank, impact engine, shaping); bypass, reorder, expand a preset into steps.
- **30-band equaliser** on any eq30 step, with presets; drag or type.
- **Transport**: original, render & listen, A/B, loop, waveform, export (wav/ogg/flac, mono, rate), the listener's
  verdict for a purpose, **hand-off** (seed variants written to a folder for tuning by hand in an outside editor, with a
  warning when a source's license speaks against taking it elsewhere) and **take back** (a tuned file checked against
  its sources and loaded).
- **Analysis**: original and render side by side, band spectrum, correlation and tone match.
- **Recipe JSON**: exactly what an agent sends the bench; apply edits, save and load.

## What the agent gets back: meter, checks, shares

Every render answers with a **distance meter** against each source clip in the mix: `waveform_pct` (the figure the
pack terms are judged by, normalized cross-correlation at any lag over both channels and their sum), `tone_pct`,
`envelope_pct`, level and length, the bar (`SIMILARITY_BAR_PCT`, 22%) and `under_bar`. The page draws these as bars
per source with the red terms line; licensed and restricted sources are marked, so while mixing you see at every step
whether anything has drifted too close to a clip. `check_render` flags clipping, DC offset, silence, inaudible rumble
and mono cancellation; `validate(recipe)` refuses a recipe with unknown effects, parameters out of range, missing
sources or impossible follows before anything renders. `layer_share` says what each layer contributes by energy, and
the agent's `report` lists its reasons: the explanation a person reads instead of guessing.

## Synthesized sources and the wider layer system

A source can be synthesized instead of loaded (`audio_materials.py`): `{"synth": "material", "material": "crystal",
"size": 0.7, "force": 0.6}` is a modal-synthesis strike on one of 13 materials (wood, bone, crystal, glass, metal,
stone, mushroom, slime, chitin, flesh, astral, void, plasma), `{"synth": "footstep", "surface": "mud", "weight": 0.8}`
a heel-and-toe step on one of 10 surfaces. No clip is behind them, so they carry no license at all.

Layers can also: `align: "onset"` (the attack lands on the main layer's), `duck` (get out of another layer's way),
`auto_gain_db` (sit a set distance under the main layer), `repeat` (count, gap, decay and pitch drop per repeat),
`pan_sweep`, `doppler` (pitch and level rise then fall), `reverse`, besides `follow`, `band`, `fit`, `pitch`, `pan`
and `offset_ms`. `breed(a, b, ratio, mutation, seed)` makes an offspring recipe from two parents with lineage
recorded; `Listener.tags(x, sr)` gives semantic tags (aggressive, organic, mechanical, magical, ...) for search by
meaning.

## Bench recipe

```python
import sys; sys.path.insert(0, r"D:\games\Ai assisted toolkit\Tools\Shared")
from audio_bench import Bench, analyze, catalog, impact_recipe, boom_recipe, load, save
from audio_listener import Listener

x, sr = load("hit.wav")
recipe = {
    "seed": 7, "length": "longest",
    "sources": {"main": "hit.wav", "tex": "gravel.wav"},
    "layers": [
        {"source": "main", "pitch": -3, "chain": [{"fx": "preset", "name": "impact_body"}]},
        {"source": "tex", "gain_db": -10, "fit": "grains", "band": [1500, 9000], "follow": {"layer": 0, "amount": 1.0},
         "chain": [{"fx": "decorrelate", "spread": 0.4}]},
    ],
    "master": [{"fx": "reverb", "room": 0.3, "mix": 0.15}, {"fx": "level", "rms_db": -19}, {"fx": "fade"}],
}
y, sr = Bench(sr).render(recipe)
verdict = Listener().compare(y, x, sr, "heavy metal door slams shut")
```

`impact_recipe(punch, body, tail, seed=...)` and `boom_recipe([sources], seed=..., layers=4)` build the two tool
layouts; `catalog()` / `python audio_bench.py describe` prints every effect with defaults, ranges and meaning, the
presets, the EQ presets and the recipe schema. Command line: `describe`, `analyze`, `apply`, `preset`, `handoff`,
`takeback`, `selftest`.

Effects: gain, level, normalize, fade, trim, length, reverse, dc, denoise · lowcut, highcut, bandpass, bass, treble,
mid, tilt, eq30 · pitch, stretch, formant, tone_from, envelope_from · saturate, bitcrush, compress, intensity,
transient, gate · tremolo, chop, ring, vibrato, chorus, flanger, phaser · echo, reverb, shimmer, width, pan,
decorrelate, doubles, noise · sub, comb, glide.

Presets: character bank brute, fiend, wraith, automaton, giant, imp, operator, cavern · impact_punch, impact_body,
impact_tail, huge_impact · heavier, smaller, distant, metallic, ghostly, crushed, robot, clean_up, rebuild, transmute.

## Agent

```python
from audio_agent import Agent
plan = Agent().propose("heavy iron portcullis slams shut", kind="impact", seconds=1.6, candidates=4)
plan["recipe"], plan["report"], plan["candidates"], plan["render"]
```

`kind` auto-guesses from the words. `sources={name: array}` fixes the material instead of searching (how the
Magi-Tech rebuild uses it). Command line: `python audio_agent.py "<purpose>" --kind impact --out x.wav --recipe x.json`.

## Listener

`Listener().pick(candidates, sr, purpose, tone_ref=original)`, `.compare(new, old, sr, purpose)`,
`.audit([(label, audio, sr, purpose), ...])`. `match` is CLAP similarity to the purpose text (about 0.2 poor, 0.5
strong), `clean` is log-odds of clean against noisy (compare takes of one sound), `faults` are measured (clipped,
silent, cut off), `rank` adds a plain-DSP tone match so a cleaner candidate that no longer sounds like its material
doesn't win. A tone reference never enters the model. Command line: `audit`, `compare`.

## Seal

`python audio_seal.py seal <mod> <mod>/sfx/<x>/sounds.mtsa --include sfx interface/x/sounds [--remove]` packs the
sounds; `install-lua <mod>` writes the self-contained OpenStarbound `postLoad` asset script (`assets.bytes` →
unseal → `assets.add`) and hooks it in `_metadata`; `write-cpp-key <StarSealedKey.hpp>` writes the key header for the
engine fork's `SealedAssetSource` (`source/base/StarSealedAssetSource.*`), which mounts every `*.mtsa` inside a mod.
The key file `audio_seal.key` is never committed. **Any mod can seal its own sounds**: seal with its own key file
(`--key mine.key`) and `--embed-key`, which writes `sounds.key` beside the archive; both engine readers try that
file when the archive's key is not the build's, and the Lua reader is installed with the same key
(`install-lua --key mine.key`). For StarCrawlers Chimera the Breachwork Loader uses wrapped keys instead: every
`sounds.pak` carries a random key wrapped with the loader's public key, so any mod author seals with
`BreachworkModManager.exe --seal-audio` or `_modding/audio/sfx_archive.py` and only the loader can open it. The cipher is a splitmix64 keystream so the Lua reader runs at
50 MB/s with no C library; it is scrambling against copying and tools, not secrecy, and a Lua reader's key is in the
reader, so ship that script only where the C++ reader is not available.

Used by: `audio_pipeline.py` (picks among Stable Audio takes), the StarCrawlers Chimera mods'
`_modding/audio/sfx_alter.py` and `sfx_audit.py`, and `Tools/Starbound/magitech_audio_redo.py`.
