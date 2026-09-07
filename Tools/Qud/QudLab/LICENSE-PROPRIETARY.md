# Qud Lab — Proprietary Core License

Copyright (c) 2026 Gregory Armstrong (Arendeth). All rights reserved.

## Scope

This license covers the proprietary / black-box core of Qud Lab, including
(without limitation):

- Install discovery and Steam/GOG ownership gate
- Assembly and asset binders that load Caves of Qud from a verified install
- Restricted simulation sandbox and SimHost protocol
- Mod-assistant HTTP server core and intelligence-cache writers
- Any code that instantiates or drives Caves of Qud runtime types

Open MIT components are separately licensed under LICENSE-MIT.md.

## Distribution

Simulator, SimHost, and Unity LoadFrom host **sources are not in the public
git tree**. Granting clone access to AAMT does not grant this license or these
files. Recipients who are allowed to use the restricted simulator unpack a
private archive with `Fetch-PrivatePack.ps1` (see `src/QudLab.Simulator/README.md`).
Public clones compile MIT `PublicStubs` that refuse to simulate.

## Requirements

1. You must own a legitimate Steam or GOG copy of Caves of Qud.
2. The software must load assemblies and assets only from your install.
3. You must not redistribute Caves of Qud DLLs, assets, blueprints, or data.
4. You must not use this software as a standalone Caves of Qud runtime,
   arena game, or general game engine hosting Qud logic for play.

## Restrictions

- No reverse engineering of the core for the purpose of creating a
  standalone Qud-like game or bypassing the ownership gate.
- No bundling of game assets or Managed assemblies with redistributions
  of Qud Lab.
- Simulation remains debug-only (no playable traversal or savegame runtime).
  A named GetZone / worldgen probe may model bootGame zone thaw for hang
  diagnosis; it is not a playable world.

## Third-party mods

User mods (including any ThreadingAPI or similar WIP mods) are not part of
Qud Lab and are not licensed under this file. Qud Lab may later offer optional
hooks; it does not ship those mods.

## Disclaimer

Provided as-is for mod development tooling, **with no warranty**. Use at your
own risk. This is unofficial experimental software, not a perfect toolset.
Freehold Games / Caves of Qud remain the property of their respective owners.
