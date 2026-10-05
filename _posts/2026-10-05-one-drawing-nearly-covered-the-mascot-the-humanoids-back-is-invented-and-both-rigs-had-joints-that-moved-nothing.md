---
layout: post
title: "Giving two generated characters a skeleton"
date: 2026-10-05
categories: [hardware, tooling]
tags: [3d, freecad, blender, gltf, three-js, rigging, image-generation, z-image, verification, 3d-printing]
excerpt: "I took two generated images, one of a push-up ice cream pop mascot and one of an armoured humanoid, through the same pipeline: measure the drawing, build a CAD solid from the measurements, skin it with the same drawing, rig it, validate it. On the mascot, a near-symmetric revolve, one front view covered almost everything. On the humanoid, it covered the front, and the depth, the back and the scale are assumptions. Both first fused solids were invalid, both rigs had joints that owned no vertices, and both passed the Khronos validator once fixed, which says less than it sounds like. Neither has been printed, and nobody has watched the animations at speed."
author: Douglas Lockamy
ai_assisted: true
---

I took two generated images of two characters this week and turned each
one into a measured, skinned, rigged 3D model. One is a push-up ice cream
pop on a stick with white gloves. The other is a slender armoured humanoid
standing in an A-pose.

Same pipeline both times: measure the drawing, build a CAD solid from the
measurements, wrap the same drawing back onto it, rig it, then try to
prove it wrong. The how-to is written up elsewhere: the [setup
overview](/posts/2026/10/02/setting-up-freecad-gimp-and-claude-to-design-3d-models/),
and parts
[11](https://github.com/dlockamy/claude-cad-workbench/blob/main/docs/tutorial/11-from-a-drawing-to-a-model.md)
and [12](https://github.com/dlockamy/claude-cad-workbench/blob/main/docs/tutorial/12-check-the-rig.md)
of the [tutorial](https://github.com/dlockamy/claude-cad-workbench/blob/main/docs/tutorial/README.md).
This post is the comparison, because the two characters stressed the
pipeline in different places.

The short version: a near-symmetric revolve gives you most of its shape
from one front view. A humanoid gives you its front, and everything else
is a guess you have to label.

![Left, the generated drawing of the mascot: a white tapered cup printed with red, blue and yellow dots, an orange soft-serve swirl on top, a smiling face, white gloves on thin navy arms, standing on a white stick. Right, the 3D model of it, skinned with that same drawing, seen from the same front angle.](/images/pogo-pop-drawing-and-model.jpg)

## Where the two images came from

Both were generated locally, on a desktop with a 12 GB RTX 3060, with
[Z-Image-Turbo](https://huggingface.co/Tongyi-MAI/Z-Image-Turbo), Tongyi-MAI's
6B image model, run through `diffusers` from Q4_K_M GGUF quantizations of
the transformer and its Qwen3-4B text encoder, with CPU offload on. A
1024 x 1024 image at 9 steps takes about 44 seconds, after a 59-second
load, and peaks at 7.7 GiB of VRAM. The prompt, seed and settings are
recorded beside every result.

The mascot came out of an image series built on one premise: an
alt-history video-game mascot that starts as a 4-bit Atari sprite and ends
as an over-the-top, Quake-era violent reboot. The first round made 12
pieces down that lineage, and the character did not hold together across
them; the model kept wandering off into popsicles and cones. A second
round locked the character to a fixed written description, and from that
round I picked one text-only render, seed 11, as the core design: a
tapered cup with a soft-serve swirl on top. That is the drawing everything
below follows.

The humanoid is a single image, seed 0, same toolchain, and one image is
all there is.

## The mascot: one view nearly covers a revolve

A cup, a swirl and a stick are all round, so the front view is close to
the whole story. Measuring the drawing meant reading each row of pixels
for the cup's half-width, the swirl's half-width, the stick, and where the
gloves and dots sit, at 0.12 mm per pixel for a figure about 100 mm tall.
FreeCAD, run headless, revolved those profiles into a cup, a swirl with
three ridge rings, and a stick, then swept two arms and placed two
ellipsoid gloves.

The first fuse came back as two solids, not one. The right glove didn't
touch its arm. Printing a bounding box per solid found it, and a longer
arm fixed it. The finished solid is about 62 x 37 x 99 mm, as measured in
the viewer. FreeCAD's own bounding box said 69 x 40, because it counts the
control points of curved surfaces, not the surfaces.

Skinning wraps the drawing around the model cylindrically. The front 180
degrees show the drawing; the back shows a copy with the face removed. So
the mascot's back is invented too, but a dotted cup looks much the same
from behind, so it's a cheap guess, though still a guess. The real costs
were smaller. The drawing's navy outline became a dark band down the seam.
Its baked cel shading wrapped around the back as a pink tint, so the
texture was flattened to plain albedo and the renderer does the lighting.
The dots still pinch slightly where they cross the side seam. And the
CAD mesher wanted 473,000 triangles on the swirl to keep that seam clean,
so the skinner meshes the round parts itself from the exact CAD profiles,
at about 83,000.

Then a skeleton of 14 joints, rooted at the stick tip so a lean pivots
where a real pogo would, and 7 clips: Idle, Hop, Hop Forward, Cheer,
Wave, Wobble and Spin Hop. The swirl's stretch and the arms' flop aren't
keyframed. They come from spring-damper systems driven by the body's own
acceleration. The CAD, skin, viewer, rig and clips were one night's run,
and the night after went to trying to break it.

![The three.js viewer showing the mascot mid-Wave with the skeleton overlay on: yellow joint dots joined by red lines run from the stick tip up through the cup to the top of the swirl, and out along both arms to the gloves. The footer reads 83,476 triangles, 14 joints, 7 animations.](/images/pogo-pop-viewer-skeleton.jpg)

That looks like a working rig. Before the validation night it wasn't,
and every still I'd rendered looked right. Validation found that the spine and chest joints owned no vertices at all: the side of the
cup was one long quad strip with nothing for those joints to grab, so every spine and chest rotation in every clip
did nothing. The squash you could see came from a blend between the hips
and the base of the swirl. Motion QA flagged tearing, a dump of the skin
weights found the cause, and the fix was a ring of vertices at least every
3 mm. The same pass found arm roots stretching to 2.9x and pinching to
0.2x until they were weighted entirely to the shoulder, and a Cheer raise
of 118 degrees that put 10.6% of the glove samples inside the cup wall.
104 degrees clears it.

The Khronos validator reported 58,293 warnings for unused joint slots
holding non-zero indices, plus 1,101 zero-area triangles at the revolve's
poles. After the fixes it reports 0 errors and 0 warnings. Blender 5.2
imports the file with 14 bones and 7 actions, and its own skinning matches
an independent numpy evaluation within 0.004 mm. The first time I compared
them, they disagreed by up to 7 mm, and that was my test's bug: Blender's
importer leaves every action as an NLA strip and doesn't reset pose bones
between actions. The viewer passes 50 end-to-end checks in headless
Chrome. Validation also caught auto-rotate counting frames instead of
seconds, so it spun 2.4x faster on a 144 Hz display, and an animation
panel sitting on top of the toolbar at 390 px wide.

![An animated loop of the Hop clip, rendered in Blender: the mascot squashes down onto its stick, springs into the air with its arms swinging up, and comes back down.](/images/pogo-pop-hop.webp)

That's the Hop clip, rendered from the exported file. Nobody has
watched it at real-time speed and judged whether it *feels* right.
Every check I just listed is a number or a still. The face is baked into
the texture, so there are no blinks. The character has no legs, so Hop
Forward leans into the jump and stays where it is.

## The humanoid: one view covers the front

The humanoid broke the pipeline before any geometry existed. It is dark
grey armour on a dark grey backdrop, and a plain threshold filled in the
gap between the legs and merged the floor shadow into the feet. The third
attempt worked. The backdrop is a vignette, not a flat colour, so I fitted
a smooth polynomial to it, thresholded the difference, and rebuilt the
lower body separately so the leg gap stays open and the shadow drops out.

A humanoid isn't a revolve, so the measurements went into a parts spec
instead: 16 parts, each a stack of elliptical cross-sections along a path,
or an ellipsoid. Every **width** is measured from the matte. Every
**depth** is assumed, at roughly 0.6 of the width for the torso and head.
The right side is the left side mirrored, and the measured right side
agreed within a few pixels. The scale is 0.2 mm per pixel, which makes the
figure 179 mm tall. That number is arbitrary, and I've written it down as
arbitrary.

The useful decision was making that one spec feed both the CAD loft and
the skinner. On the mascot, the skin was built from the CAD profiles. On
the humanoid, both read the same file, so the solid and the textured mesh
can't drift apart.

The first CAD fuse was invalid: four solids. The sword's loft had come out
inside-out, with negative volume, and the tabard and hip discs were
floating in front of the body without touching it. **Every one of those
parts was a valid solid on its own.** Reversing the loft and sinking the
floating parts into the body gave one valid solid of 65.9 cm³, and a
separate check of the STL outside FreeCAD agreed: watertight, one body.

Then the back.

![Five panels. Left, the generated source image: a slender armoured alien-reptilian figure in an A-pose on a grey backdrop, with a crested helmet, a glowing cyan chest core, bronze shoulder pieces, a brown tabard and a sword hilt over one shoulder. Then the 3D model from the front, three-quarter, side and back. The front matches the drawing closely; the side view is thin and patchy; the feet are flat saucers; the back is an almost uniformly dark, nearly black figure.](/images/lastling-image-and-model-views.jpg)

The back is invented, and the picture doesn't hide it. The back texture
is a darkened, smoothed copy of the front with the face, the chest core
and the belt painted out, and it renders nearly black. Its first version
had black holes where the painted-out areas were too big for the blur to
fill. The side textures are patchy because they come from a front-on
projection. The feet are saucer-shaped ellipsoids where the drawing has
clawed boots. Only the sword's grip is visible in the image, so the rest
of it is a guessed scabbard. A small gold shard that floats beside the
head in the source image is an artefact of generation, and I didn't model
it.

The rig has 18 joints and 3 clips: Idle, Walk and Wave. Walk is in place
and slides. After the mascot, I added a check that fails the build if any
joint owns too few vertices or moves too few when rotated. Its very first
run failed: both hand joints owned zero vertices. This time the cause was
the weighting, not the mesh. The wrist blend was centred on the joint but
the projection stopped at the joint, so no hand vertex could ever pass a
weight of 0.5. It was the same family of bug as the mascot's spine, with a
different cause, and this time a check caught it rather than a symptom.
Then came 96,402 validator warnings, the same unused-joint-slot problem as
the mascot. After the fixes: validator 0 errors and 0 warnings, and
Blender's skinning within 0.002 mm of mine. The viewer was only looked at
in headless Chrome. The mascot's 50-check UI test was not ported.

I paused it there. My verdict at the time: "Not too bad for a first
pass but for sure needs a lot of work to be in a good spot."

## What carried over, and what broke differently

| | Mascot | Humanoid |
|---|---|---|
| What one front view gives you | nearly the whole shape | the front |
| The back | invented, and cheap to guess | invented, and it shows |
| Depth | follows from the revolve | assumed (about 0.6 of width for torso and head) |
| Scale | about 100 mm, chosen | 179 mm, arbitrary |
| Where it first pushed back | skinning: the seam and the baked shading | the matte, before any geometry |
| First fused solid | 2 solids (a glove off its arm) | 4 solids (an inside-out loft, floating parts) |
| Dead joints | spine and chest: no vertices in the mesh | both hands: weighting never reached them |
| Found by | motion QA, then a weight dump | the influence check, first run |
| Validator after fixes | 0 errors, 0 warnings | 0 errors, 0 warnings |
| Printed | no | no |

The scripts carried over with small changes. The mascot's preview renderer,
glTF reader and Blender cross-check were reused. The matte, the
generic parts spec, the humanoid weights and the influence check are new.
The lessons carried over more cleanly than the code:

- **A per-part check is not a whole-model check.** Both first fuses were
  wrong, and on the humanoid every individual part was valid.
- **A rig can look right in every still and have joints that do nothing.**
  It happened on both, for different reasons. (The [weekly
  post](/posts/2026/10/04/a-rule-that-fired-zero-times-a-30-day-session-that-ended-when-you-closed-the-browser-and-a-fix-thats-merged-but-not-live/)
  had the one-line version of this.)
- **The validator checks the file is well formed, not that the rig
  works.** A joint that owns no vertices doesn't make a file malformed.
  The public repo has the proof in miniature: a
  deliberately broken [skinned
  tube](https://github.com/dlockamy/claude-cad-workbench/tree/main/examples/skinned-tube)
  with one inert joint gets 0 errors and 0 warnings, and
  [`check_rig.py`](https://github.com/dlockamy/claude-cad-workbench/blob/main/tools/check_rig.py)
  catches it.
- **When a second tool disagrees, suspect your test first.** Blender's 7
  mm was my comparison script. FreeCAD's 69 x 40 was control points.
- **One spec feeding both the CAD and the skin keeps them from drifting.**
- **A clean slice is not a printable model.** Bambu Studio sliced the
  mascot and said Success. Its first layer was 38 mm of path, because it
  stands on a rounded 4 mm stick tip, close to a dot. A flat 36 mm x 2 mm
  base fused under the stick makes the first layer 2,944 mm of path, cuts
  the filament added by supports from about 60% to about 17%, and comes
  to 3 h 10 m without supports. The humanoid stands on two feet: 649 mm of first layer, 4 h 33 m without supports,
  7 h 23 m with them. Slicing is all either has had.

The comparison I didn't expect: the humanoid is the less finished model,
but it's the easier one to print, because a figure with feet has a
footprint and a mascot on a pogo stick doesn't.

## About the names

"Pogo Pop" and "Lastling" are working names, and neither has been
trademark-cleared. A Pogo games brand already exists, and a quick search
that found nothing specific for Lastling is not a clearance.

## Not done, as of writing

- **Neither model has been printed.** Both have only been sliced.
- **Nobody has judged how any of the animations feel at real-time speed.**
  All ten clips across the two characters were checked with numbers and
  stills only.
- Neither file has been opened in Unity, Godot or Unreal, and neither
  viewer has been tried in Safari, Firefox or on a touch screen. The
  humanoid's viewer has had no UI test at all.
- The humanoid's back, sides, depth, feet and most of its sword are
  guesses. It's paused, and the obvious next step is getting real back
  and side views of the same character instead of inventing them.
- Both names still need a real trademark search.

---

The honest shape of it: on the round character, the front view was most
of the answer. On the humanoid, it was the front of the answer. Both first
fuses were wrong, both rigs had joints that moved nothing, and the checks
that found them looked at what the model *did*: which vertices a joint
owned, how far an edge stretched, how much plastic touched the bed.

If you've found a way to get a believable back and side out of a single
front-view image, short of drawing them yourself, I'd like to hear how:
[find me on LinkedIn](https://www.linkedin.com/in/douglas-lockamy-49097b33/).
