# MRR Card Game artwork specification - Phase 58

Artwork is supplied by the project owner. Do not generate replacement characters or procedural art for the PC integrated 3D card image area.

## Fixed size and crop
- Source master: 1200 x 960 pixels, landscape aspect ratio 5:4.
- Canvas texture: 512 x 704 pixels.
- Reserved canvas region: x=56, y=199, width=400, height=320, exact aspect ratio 5:4.
- Preferred image: PNG, sRGB. JPG is also acceptable when actual images are delivered.
- Never distort the artwork. The future asset importer should preserve aspect ratio and fit 5:4. Any nonconforming source requires an explicit cropping or letterbox choice.
- Keep all essential subjects inside the 5:4 safe region and away from its outer edges.
- Frame, name, mana cost, card type, health and other gameplay information are drawn outside this image region.

## Asset identity
- Phase21 defines 244 cards. The companion card art index lists all cards and their stable IDs.
- Proposed filenames: assets/card-art/<card_id>.png, for example assets/card-art/01-01.png.
- Names alone are insufficient because some card names repeat across factions.
- Status awaiting_user_artwork means no photo has been supplied. There are zero fabricated images.
- Images are intentionally NOT fetched at runtime in Phase58. Future asset integration must be verified separately and preserve offline execution.

## Scope
- Only the PC integrated Three.js battlefield replaces procedural portraits with blank reserved image windows.
- Existing Phase21 rules, card data, AI, native actions, saving/loading, and older standalone 3D view are preserved.
- No mobile layout, new game rules, or artwork are added in this phase.

## Phase59 - Actual import workflow

1. Use `assets/card_art_index.csv` to find the desired original card ID. Do not use just the display name.
2. Put the user-created 1200 x 960 PNG or JPEG into `assets/card-art/<card_id>.png`, `<card_id>.jpg` or `<card_id>.jpeg`.
3. Run `python build.py`, or commit the image to GitHub and let GitHub Actions build it.
4. The importer verifies the actual file header, exact dimensions, known IDs, duplicate IDs, and maximum 8 MiB size per image. Invalid files stop the build with a clear error.
5. Valid artwork is base64-embedded into the standalone PC HTML on build. It requires no image server or runtime fetch. No artwork is supplied yet.
6. Only publicly displayed cards in the PC integrated 3D arena consume the image. The 244-card data, battle rules, AI, save/load and original 2D user interface remain untouched. The standalone legacy 3D modal is likewise unchanged.
7. The card face remains 512 x 704 px. Uploaded images fill x=56 through 455 and y=199 through 518, a 400 x 320 px 5:4 area, without distortion or automatic crop.
8. Missing artwork keeps the established blank placeholder. Exact public card name and displayed type/faction are resolved against all 244 original IDs. Duplicate names cannot swap images.

In this phase, the repository remains empty of user artwork. The test suite creates two-colour synthetic pixels only in a temporary QA fixture, not in the distributed build.
