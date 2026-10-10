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
