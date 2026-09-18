Tool: built-in image_gen.
Prompt 1: transparent pixel-art sprite atlas: left-facing penguin, three orange fish swimming poses, icy sparkle and falling icicle.
Prompt 2 (replacement): Antarctica coastal pixel-art landscape with immense white ice shelf cliffs, jagged snow-covered Antarctic mountains, deep blue Southern Ocean, pale blue sky and snowy ground at bottom; no animals, trees, buildings or text.
antarctica-background.png is the active Antarctic game background, 640x480.

Files:
- penguin-left: left-facing penguin, PNG and GIF.
- orange-fish-swim-1/2/3: three orange fish swimming poses, PNG and GIF. Blue and gold fish are tinted at runtime.
- ice-sparkle: icy sparkle effect, PNG and GIF.
- icicle: falling icicle, PNG and GIF.
- icicle-projectile.gif: copy of the icicle used by the earlier shooting example.
- antarctica-background: Antarctic landscape, PNG and GIF.
- penguin-fish-ice-sprite-atlas.png: original combined sprite sheet.

Adventure art update, built-in image_gen tool. Prompt: consistent Antarctic pixel-art 4x3 object atlas (adult penguin, baby, crab, igloo, cave entrance, chest, growth/speed/reverse potions, snow/smooth/cracked ice blocks), transparent background, isolated sprites. Alpha extraction edit: remove background and halos, preserve sprites and opaque doorways. Background prompt: six-panel pixel-art landscapes: snowy coast, glacier canyon, ice cave interior, blizzard plateau, fractured shelf, sunset nesting coast. Final cropped PNG files are in this directory.
Fish prompt (built-in image_gen): transparent single-row atlas, isolated orange, cyan-blue and golden fish with distinct silhouettes and crisp dark outlines, all facing left. Outputs: orange-fish.png, blue-fish.png, gold-fish.png.

Animation: built-in image_gen with penguin-adult-left.png as identity reference. Prompt: transparent 4x2 pixel-art atlas, four left-facing walk frames with alternating feet and flipper swing, idle, ascent with spread flippers, descent and crouched landing. Same identity/proportions. Extracted frames use one shared scale and foot baseline on 64x56 transparent canvases.

Built-in image_gen update: eight-phase left-facing walk cycle, alternating feet/flipper sway, consistent adult-penguin identity, transparent 4x2 atlas. Enemy atlas prompt: transparent 3x2 pixel-art poses for leopard seal patrol/charge, Antarctic skua wings up/down, ice spirit standing/jumping. Outputs are named by contents and preserved in this directory.
