# Owner artwork folder

Place user-owned PNG or JPG files here, named by exact card ID in assets/card_art_index.csv.

Example: `01-01.png` for card ID `01-01`.

Each image must be exactly 1200 x 960 pixels in landscape orientation.
Run `python build.py` to embed supplied images into the single playable HTML.
No user artwork is included in this repository yet, and absent images remain blank.

Cards are matched by the unambiguous visible name and type/faction, never the hidden opponent hand.
Images are displayed in a fixed 400 x 320 pixel region of the 512 x 704 card face.
The renderer preserves 5:4 ratio and does not auto-crop or stretch.
Invalid or duplicate IDs and wrong-size files cause a build error instead of silent substitution.
