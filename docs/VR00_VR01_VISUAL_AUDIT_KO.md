# VR00-VR01 visual rework audit and QA gate

Date: 2026-10-12. Prior main HEAD: 04001ee34d3089dba51600e42f4e9d716836c433.
Prior main Actions: #38169868069 completed/success. Open PR at baseline: 0.

## Baseline structural findings
The current Phase76 integrated.js mounts the Three.js public battlefield while relying on visible legacy HTML hand, hero/turn controls, context actions and expandable inspector/rail. Native hand reveal is toggle-driven. CSS has many z-index/visibility conditional overrides. These make the experience resemble a layered HTML application rather than a cohesive digital card game.

## New VR01 architectural boundary
The independent src/visual-rework/vr01.js and vr01.css define a full-viewport PC shell. It displays exactly N public opponent card backs, mirrors the player's existing hand names/cost/type/stats, makes the reserved artwork area blank, moves hero HUD into compact accents, adds a native-delegating lower-right turn button and keeps the Three.js public board raycaster as the sole hit-test route. The VR scene uses a darker cold-stone material rather than the previous tan atlas. It does not read opponent hand identities or reimplement card rules.

The original Phase21 game remains byte-identical. Outside VR mode Phase76 rendering remains unchanged. Context attack/move/cancel still delegate to its native buttons; 2D fallback and utility panels remain accessible.

## Review gate and required evidence
Run the new tests/vr01_vertical_slice_e2e.py in GitHub Actions to generate before/after Chromium screenshots for FHD plus laptop and QHD new-mode captures. Check legibility, visual hierarchy and screenshot clipping manually. Automated test success does not prove satisfactory commercial art direction. Do not merge as complete until the user approves the screen.

## Scope not yet completed
VR01 is a playable vertical slice, not the VR02-VR08 complete game. More art direction iteration will be required after screenshot review. Owner artwork 1200x960 remains unavailable.
