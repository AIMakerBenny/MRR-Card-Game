# MRR Card Game PC visual-finish batch, Phases 73-76

Baseline: Phase72 main `444d293fea4ac54b1222bb90aed695fc272d5aad`. Engine preservation is mandatory.

## Delivered in this batch

- Phase73: A second physical gold ring marks only the field card selected by the original `#arena .selected-slot` state. It never becomes a raycast target.
- Phase74: Orange/red attack-target halos pulse only where the original `.attack-target` class is present. Target legality and HP remain decided solely by Phase21.
- Phase75: A subtle stationary halo size increase identifies hovered public slots without changing selected/other cards or any input semantics.
- Phase76: All focus/target cues honor `prefers-reduced-motion`, use preallocated Three.js scene meshes/materials with no per-frame allocations, and retain the Phase72 original legal-target halo animation.

## Verification and constraints

A new real Chromium/WebGL QA test at 1366x768, 1920x1080 and 2560x1440 verifies the native selected source, native enemy target, visual cue state, reduced-motion animation freeze, genuine mouse attack/HP damage, engine snapshot parity and fallback to 2D. The entire older regression suite and the byte-identical original source audit still run in GitHub Actions, with a 45-minute limit.

No replacement for the 244 original card illustrations has been authored. Owner supplied 1200x960 art is still required and the existing blank art reservations remain blank. Neither a new game engine nor a Godot rewrite is claimed. Finished deployment requires successful branch/PR Actions and successful Actions on the exact merged main HEAD.
