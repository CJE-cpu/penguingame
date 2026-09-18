# Art refresh v2

Generator: built-in image_gen (no CLI fallback).

Final project assets are saved alongside this file. Original source assets are preserved. Generated atlases are sliced at runtime by art.py; shared scales, alpha gutters and foot/head anchors keep cycles stable. Nearest-neighbor scaling preserves pixel edges.

## adult-motion-atlas-v2.png

6 x 5; walk 8, idle 2, ascent 2, descent 2, landing 2, hurt 2, slide 6, swim 6.

Final prompt:

```text
Use case: stylized-concept. Asset type: production transparent PNG sprite sheet for an Antarctic penguin platformer. Input image is an IDENTITY AND PIXEL-ART STYLE REFERENCE, not an edit target. Create a NEW precisely aligned 6-column by 5-row atlas, 30 isolated sprites in equal rectangular cells. Same adorable left-facing adult penguin in every cell: dark navy back and flippers, creamy white belly, orange beak and feet, crisp pixel-art outlines, natural proportions. Pixel art, not painterly, no gradients behind sprites. All sprites face LEFT. Row 1: walking phases 1-6. Row 2: walking phases 7-8, idle breathing 1-2, jump ascent 1-2. Row 3: falling poses 1-2, soft crouched landing 1-2, hurt recoil 1-2. Row 4: SIX genuine belly-sliding poses, penguin anatomically lying prone horizontally with white belly on ground, head upright at LEFT and feet trailing RIGHT, subtle flipper sweep and trailing feet; NEVER just rotate an upright penguin. Row 5: SIX genuine swimming stroke phases, penguin streamlined horizontally with head LEFT, alternating extended and tucked flippers and kicking feet, white belly DOWN, black back UP. Keep body scale consistent within each cycle, feet/belly ground baseline equal within each row, center of mass aligned. Transparent background with REAL alpha, NO checkerboard drawn into pixels, no labels, numbers, grid lines, water, snow puffs, shadows or cropped limbs. Leave clear transparent gutters, each sprite stays entirely in its cell. Intended to slice and downscale into 64x56 upright and 80x42 horizontal game frames.
```

## baby-motion-atlas-v2.png

4 x 2; walk 4, idle/blink 2, ascent 1, descent 1.

Final prompt:

```text
Use case: stylized-concept. Asset: NEW transparent PNG animation atlas for a baby penguin companion in an Antarctic pixel-art platformer. Input image: IDENTITY/STYLE reference. Exactly FOUR equal columns and TWO equal rows, eight isolated sprites, generous empty gutters, no labels, no grid lines. Same small fluffy gray Antarctic penguin chick with dark hood, white face, dark small beak, black little feet, all facing LEFT. Top row: FOUR readable walking phases, feet alternate forward/backward, flippers sway, tiny gentle body waddle, body size/face stay consistent and feet share a baseline. Bottom row: two idle breathing/blinking poses, one jumping pose with flippers spread, one descending landing-preparation pose. Crisp dark navy pixel-art outlines, soft gray feathers shaded in chunky pixels, match reference and adorable adult penguin style. Real transparent alpha, no background color, no checkerboard texture, no halos, no cast shadows, no snow. Every sprite wholly inside its cell, consistent character scale. Will render on 32x40 game canvases.
```

## enemy-motion-atlas-v2.png

4 x 4; crab 4, seal 4, skua 4, ice spirit 4.

Final prompt:

```text
Use case: stylized-concept. Asset type: NEW transparent pixel-art sprite sheet of enemies for an Antarctic penguin platformer. Input 1 crab and input 2 leopard seal are STYLE and IDENTITY references. Exactly FOUR columns by FOUR rows, sixteen isolated sprites in equal cells with generous transparent gutters, no labels/grid. Row 1: four phases of a cute red-orange crab walking sideways with alternating legs and moving claws, front-view identity identical in every frame. Row 2: left-facing spotted gray Antarctic leopard seal: two flipper-shuffling patrol phases, one braced head-raised warning, one forward stretched charging pose. Row 3: left-facing brown Antarctic skua seabird in four distinct wing-stroke phases (wings high, halfway down, fully down, recovering), identical body scale. Row 4: same small cyan-blue crystalline ice spirit in four phases: standing, crouching ready to leap, ascending with little limbs extended, descending. Consistent crisp pixel-art dark navy outlines and chunky highlights to match the existing penguin sprites. Each species has exactly one coherent design, no realism, no brush blur, no scenery, no cast shadows or impact particles. Real alpha transparent background, no checkerboard/halos, each sprite entirely in its own cell. Match dimensions within species, grounded feet/flipper baseline for patrol frames. Will render small at 44x30 crab, 68x34 seal, 48x40 skua, 36x40 spirit.
```

## adventure-objects-atlas-v2.png

4 x 3; journals, nest, flag, flowers, ice shell, two lever states, dive hole, practice arch, ocean rocks and seaweed.

Final prompt:

```text
Use case: stylized-concept. Asset: coherent NEW transparent Antarctic pixel-art object atlas for a penguin platformer. Exactly FOUR equal columns by THREE equal rows, twelve distinct isolated objects, generous transparent gutters, no labels, no grid, no cast shadows. Row 1 left to right: small closed tan explorer journal with snowflake clasp; open journal with simple blank pages and snowflake (NO letters); warm low oval nest of pebbles with pale straw; thin wooden pole with triangular orange-gold explorer flag. Row 2: little patch of FIVE icy cyan flowers with gold centers; transparent hollow frosted ice shell/cage with cracked edges and an EMPTY transparent center, sized to overlay a penguin chick; wooden-and-ice lever in DOWN state with yellow small flag; identical lever in UP state with green small flag. Row 3: oval dark blue open-water diving hole surrounded by chunky white snow/ice rim, water opening opaque blue; snow-capped horizontal ice tunnel arch with TWO vertical supports and a CLEAR transparent low opening beneath the lintel (wide platformer passage); blue seafloor rock cluster; Antarctic underwater seaweed clump. Style: crisp small-scale pixel art, dark navy outlines, icy blue-white highlights, restrained warm gold accents, cute exploration game, visually readable at 24-180px. Actual alpha transparency, no checkerboard or full background, each object wholly inside its cell. Hole and doorway openings as specified; nothing cropped. Match the established penguin game art.
```

## ocean-panorama-v2.png

Opaque underwater panorama, rendered once across the 1800 x 600 ocean.

Final prompt:

```text
Use case: stylized-concept. Asset: NEW wide panoramic background for an Antarctic penguin platformer's underwater exploration stage, landscape 3:1 composition if possible. Crisp 16-bit pixel-art environment, no characters or collectible fish, no text/UI. A continuous view below Antarctic sea ice: pale cyan-white thick ice ceiling along top 12%, cold blue water, shafts of soft cyan sunlight from cracks at upper left, distant ice pillars and faint submerged icebergs in background, darker blue layered depth, low rocky seafloor with sparse Antarctic seaweed along bottom 10%. Center 70% of image remains clean unobstructed blue open water so small penguin/fish sprites are readable. Left upper corner subtly shows a safe open-water exit gap in the ice ceiling, not a building. No tropical plants, corals, polar bears, palm trees, land horizon or repeated panel boundaries. Chunky pixel clusters, dark blue silhouettes in foreground, atmospheric yet bright enough for gameplay. No transparent background; opaque continuous panorama with one coherent perspective, no collage. Intended to scale into an 1800x600 underwater level and crop as camera moves, without tiling the image edges.
```

## fish-motion-atlas-v2.png

4 x 3; orange, blue and gold fish, four tail/fin poses per species.

Final prompt:

```text
Use case: stylized-concept. Asset: NEW genuine transparent pixel-art fish animation sprite sheet for an Antarctic platformer. Input image is visual STYLE reference, not an edit target. EXACTLY FOUR equal columns by THREE equal rows, twelve isolated sprites with clear empty gutters. All face LEFT. Row 1: four swimming tail-and-fin stroke phases of the same orange round-bodied fish, cream belly and orange fins. Row 2: four swimming phases of one distinct slender cyan-blue fish with dark blue dorsal fin and silver belly. Row 3: four swimming phases of one distinct golden fish with elegant longer gold fins and pale yellow belly. Each row is one coherent species; change tail and fins across frames, don't change face, body size or location. Crisp dark navy pixel outlines, chunky highlights, consistent cute game style, easily readable when scaled to 36x24px. Equal scale within each species, centered body, no cropped fins. Actual transparent alpha background, no checkerboard pattern, no water, bubbles, shadows, words, labels or grid lines.
```

