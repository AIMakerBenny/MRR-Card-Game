# MRR Card Game - PC batch Phase 60-63

Base: Phase59 at `9827ee946af3589d94cd01d8e962b80a041b9c5b`.

## Implemented
- Phase60: exact-card-ID owner PNG/JPG appears on the publicly rendered native hand, board cards, inspector and catalog as well as the existing 3D card face. No hidden enemy back is ever replaced and no fake artwork ships.
- Phase61: artwork is contained without crop or stretch in native card artwork wells; blank 3D art remains blank without user images. Restrained PC card-border/hover treatment without an additional rectangular app panel.
- Phase62: a compact attack/move/cancel context command strip can appear near the currently selected public 3D card. Each button invokes the existing native inspector command. It never computes damage, resources, legality, AI, saves or turns. The strip follows PC viewport changes and stays inert when no native action exists.
- Phase63: Chromium tests for 1200x960 owner images shown in native hand and board with matching IDs, actual 2-player battle with contextual 3D attack and HP reduction, and desktop 1920x1080 / 1366x768 / 2560x1440 geometry checks. Keep all Phase55-59 regressions.

## Not done without outside input
- Original custom artwork for all 244 unique cards: user said they will supply it; the image slots stay blank until they do.
- Commercial-grade bespoke illustrated heroes, music, UI sounds, animated character assets and professional art direction must be authored/licensed/approved, not represented by fake screenshot mockups.
- A wholesale Godot 3D rewrite is not implied. This is still a working Three.js PC web game preserving the exact Phase21 original combat engine.

## Verification and handoff
Run `npm install && npm run vendor && python build.py`, then the GitHub Actions workflow including all Chromium regression scripts. Distribute `dist/index.html`, `dist/vendor/three.module.js` and art CSV from the successful matching **main** workflow only.

Owner artwork can be supplied incrementally using `assets/card-art/<original-card-id>.png` in strict `1200x960` size. The importer bundles only supplied files. Never treat test-only synthetic coloured pixels as game art.
