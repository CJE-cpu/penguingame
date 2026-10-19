Tool: built-in image_gen.
Shield potion update: `shield-potion.png`, generated with the built-in image
generation tool using the growth, speed and former reverse potion sprites as
style references. Prompt: isolated transparent cyan potion with the same cork,
glass highlights and navy outline, a white-and-blue shield emblem and small
hexagonal frost sparkles; no arrows, letters, UI or ground shadow.

Platform rendering now uses cached, code-generated three-tone shelves. This
keeps collision edges clear and avoids loading or repeating large texture files.
Prompt 1: transparent pixel-art sprite atlas: left-facing penguin, three orange fish swimming poses, icy sparkle and falling icicle.
Prompt 2 (replacement): Antarctica coastal pixel-art landscape with immense white ice shelf cliffs, jagged snow-covered Antarctic mountains, deep blue Southern Ocean, pale blue sky and snowy ground at bottom; no animals, trees, buildings or text.
antarctica-background.png is the active Antarctic game background, 640x480.

Files:
- penguin-left.png: left-facing penguin.
- orange-fish-swim-1/2/3.png: three orange fish swimming poses. Blue and gold fish are tinted at runtime.
- ice-sparkle.png: icy sparkle effect.
- icicle.png: falling icicle.
- antarctica-background.png: Antarctic landscape.

The duplicate GIF exports and superseded sprite atlases were removed. The game
uses the PNG assets and the `*-v2.png` motion/object atlases.

Adventure art update, built-in image_gen tool. Prompt: consistent Antarctic pixel-art 4x3 object atlas (adult penguin, baby, crab, igloo, cave entrance, chest, growth/speed/reverse potions, snow/smooth/cracked ice blocks), transparent background, isolated sprites. Alpha extraction edit: remove background and halos, preserve sprites and opaque doorways. Background prompt: six-panel pixel-art landscapes: snowy coast, glacier canyon, ice cave interior, blizzard plateau, fractured shelf, sunset nesting coast. Final cropped PNG files are in this directory.
Fish prompt (built-in image_gen): transparent single-row atlas, isolated orange, cyan-blue and golden fish with distinct silhouettes and crisp dark outlines, all facing left. Outputs: orange-fish.png, blue-fish.png, gold-fish.png.

Animation: built-in image_gen with penguin-adult-left.png as identity reference. Prompt: transparent 4x2 pixel-art atlas, four left-facing walk frames with alternating feet and flipper swing, idle, ascent with spread flippers, descent and crouched landing. Same identity/proportions. Extracted frames use one shared scale and foot baseline on 64x56 transparent canvases.

Audio update: original synthesized mono OGG assets in `audio/`. Six regional
ambient loops, an underwater loop, and action cues cover jumping, collection,
items, damage, falls, enemy defeat, checkpoints, rescues, and the ending.

Boss art update, built-in image_gen using the existing leopard seal and cave
background as identity/style references. Six original arcade-readable poses
(idle, roar, warning, charge, stunned, defeated) use exaggerated silhouettes,
cyan motion accents, and consistent transparent 180x110 canvases. Classic
arcade platformers informed readability and color contrast only; no external
character, stage, UI, or sprite was copied.

Built-in image_gen update: eight-phase left-facing walk cycle, alternating feet/flipper sway, consistent adult-penguin identity, transparent 4x2 atlas. Enemy atlas prompt: transparent 3x2 pixel-art poses for leopard seal patrol/charge, Antarctic skua wings up/down, ice spirit standing/jumping. Outputs are named by contents and preserved in this directory.

Skua boss update, built-in image_gen. Prompt summary: an original transparent
4x2 pixel-art Antarctic skua boss atlas with hover-up, hover-down, warning,
dive, snowball-carry, stunned, hit and defeated poses; bold navy outlines,
warm brown feathers, readable arcade silhouettes and no text or UI. Output:
`skua-boss-atlas.png`.
