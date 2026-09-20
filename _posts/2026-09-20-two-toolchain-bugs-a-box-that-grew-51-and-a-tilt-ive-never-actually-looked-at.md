---
layout: post
title: "Two toolchain bugs, a box that grew 51%, and a tilt I've never actually looked at"
date: 2026-09-20
categories: [devops, hardware]
tags: [freecad, cadquery, 3d-printing, cad, verification, homelab, hardware]
excerpt: "I need real hardware to test against, so I built two dev mules — an x86 tower with printed parts filling the gaps a case never anticipated, and a Pi 5 bench box with a fully printed enclosure. Both designed as parametric scripts rather than in a GUI, every part verified by reading the exported geometry back instead of trusting the build report. That check earned its keep three times, on three unrelated bug classes. Then a touchscreen that didn't fit grew the box 51.7% — a design call, not a CAD one. Several dimensions are still estimates, and one part's tilt has never been looked at."
author: Douglas Lockamy
ai_assisted: true
---

I need real hardware to test against. Not eventually — now, while there's
no deadline pressure, because the skills involved in designing, printing
and assembling a box are not skills you want to acquire under one.

So: two dev mules. One is an x86 box in a commodity mid-tower with
printed parts filling the gaps a case never anticipated. The other is a
Pi 5 bench box with a fully printed, scratch-designed enclosure. Both are
internal pipeline-verification hardware — nobody is waiting on either one
but me, and neither is a product.

Both were designed as *code*: parametric scripts producing STEP and STL,
rather than modelled in a GUI. This is about what that bought me, and
about the three separate ways the scripts lied while exiting cleanly.

## The standard: read the geometry back

A script exiting zero proves nothing. Every part gets its exported file
read back in and interrogated:

```python
shp = Part.Shape(); shp.read("part.step")
assert len(shp.Solids) == 1, f"got {len(shp.Solids)} solids, expected 1"
assert shp.isValid()
print(shp.BoundBox.XLength, shp.BoundBox.YLength, shp.BoundBox.ZLength)
```

Solid count is the workhorse. Almost every real geometry bug I hit shows
up as "N solids where I intended 1" — booleans that didn't actually fuse,
features that fragmented — and the bounding box gets compared against
spec per part, not eyeballed.

The count has to encode *intent*, though, not a constant. One part in the
second box is a bottom panel with four discrete TPU feet in the same
file: five solids, correctly, by design. Assert `== 1` everywhere and you
either get a false alarm or you learn to ignore the alarm, and the second
one is much worse than having no check at all.

## Box one: the bug the script was happy to hide

The first scaffold went out as CadQuery — Python CAD-as-code, same OCCT
kernel FreeCAD uses — because every dimension was already pinned down in
the build breakdown, so there was nothing to *explore*, only to express.
Nine printed parts, ten solids out, every bounding box checked against
spec. It needed a throwaway Python 3.11 venv: Homebrew's default is 3.14
now and there's no OCP wheel for it yet.

Then I switched toolchains, because FreeCAD's headless CLI already ships
inside the GUI install I had — 1.0.2 at the time — and I'd rather be
fluent in the application than in a library. Two parts as a trial: a
kill-switch escutcheon with engraved text, and a screen bezel built as a
12°-rotated loft. Both exported clean on the first run, text engraving
included, which was the operation I'd expected to need a GUI for.

"Exported clean" is exactly the trap. The verification pass caught what
the run didn't: the escutcheon came back as **two disjoint solids**. Its
raised fence sat flush on the base — coincident faces, zero volumetric
overlap — and a boolean union across a shared face succeeds while
producing two pieces that merely touch. Fixed with a real 0.2 mm overlap
before the fuse, plus an assertion guarding the regression.

The useful part came next. I ran the same read-it-back check over the
*already committed* output from the first toolchain and found the
identical bug class in a part the trial had never touched — another
two-solid part, this time from an accidental ~3 mm sliver between a
screen cutout and a grille cutout positioned by two independent offsets.
They didn't quite collide; they left a bridge too thin to survive. The
fix wasn't to nudge a number, it was to derive the screen cutout's
position *from* the grille geometry with a named minimum bridge, so the
relationship lives in the source instead of in my head. Same bug, two
toolchains, found by the check and not by either tool.

## Box two: two toolchain bugs worth the price of admission

The Pi-based box is thirteen parts across fourteen files, all
FreeCAD-native, reusing geometry from the first box wherever a part was
functionally identical rather than re-deriving it. Verified the same way,
and checked independently rather than trusting the build report. Two
toolchain bugs came out of it, both the silent kind.

**`freecadcmd` sets `__name__` to the script's filename, not
`"__main__"`.** Gate your generation loop behind the ordinary Python
main-guard idiom and the script runs, exports nothing, prints no error
and exits 0. There are simply no files. If you've ever wondered whether
"exit code 0" is a verification standard, there's your answer.

**Reassigning a shape's `.Placement` after it's already been unioned or
cut can fragment it into multiple solids instead of translating it.** I
hit this angling a set of cooler-exhaust vent slots — move the placement,
and what should have been one repositioned body comes back as several.
Fixed by building the slots into the cut geometry directly instead of
positioning them after the fact. Note this is a *second* route to the "N
solids where 1 was intended" symptom from a completely different cause,
which is why the check earns its keep: it catches a class of failure, not
a specific bug.

## The panel that didn't fit, and the box that grew

Then the interesting failure, which wasn't a bug at all.

The design called for a small desk-terminal object: 195 mm wide, 80 deep,
58 tall. The real DSI touchscreen panel's PCB is about 110 × 70 mm — not
the ~105 × 67 the layout had been estimated around. Seventy millimetres
of panel does not go into a 58 mm-tall box, and the sealed speaker
chambers needed more width besides. The mic pod didn't fit the specified
depth either: a genuine 10 mm overhang.

The CAD pass could have absorbed both. Grow the box, move on, note it in
a commit message. Instead both went back as a design call, because the
height change isn't a dimension — it's a different object. 58 mm to 88 mm
is a **51.7% increase** on the axis the whole silhouette was designed
around, and I recomputed that rather than repeating the round number I'd
written down earlier.

The answer changed the box rather than just resizing it: 220 × 90 × 88
mm, with depth pushed deliberately past the minimum so the thing reads
*deeper than it is tall* — a planted stance countering the cantilevered
mic's forward moment instead of looking tippy under it. Closer to a Braun
table radio than to the thin bar it started as. The overhang became a
specified cantilever, braced 15 mm down into the front baffle so it's
structural rather than hopeful.

The closing pass verified that with `Part.common()` intersection-volume
checks rather than solid counts alone — the brace shares real volume with
the baffle and shares *none* with the kill-switch mount or the top vent —
and passing them took actual layout moves rather than new assertions.

Whoever implements a spec shouldn't be the one quietly rewriting it. That
30 mm was a design decision wearing a CAD decision's clothes, and the
only reason I noticed is that the number was too big to wave through.

## What the checks still don't cover

Honest column, because everything above is geometry verifying geometry
and the interesting failures are all outside that circle.

The panel outline that drove the entire box-growth decision is still an
estimate, not a datasheet pull. I grew a box 51.7% on the strength of a
number I have not sourced, which is defensible as a direction and not
defensible as a dimension.

The mic pod's 15° tilt was built by sign convention matching the screen
bezel and has **never been looked at** by a human. If it reads backwards
it's a one-line fix, but no assertion I've written can tell me that —
it's the same class of gap that let a mesh repair destroy a letterform
elsewhere this week while every check stayed green.

And while all the geometry was being verified, the thing that nearly bit
me was material: the printer handles PETG fine, but its stock build plate
was pulled from PETG's recommended list after adhesion problems. Geometry
checks verify geometry. They say nothing about whether the part sticks to
the bed.

## Next

Placeholders get closed against real datasheets before anything prints in
a material I care about, the tilt direction gets a look in the GUI, and
then the first structural parts go on the plate. Source and verified
STEP/STL stay committed together, so the files open without installing a
toolchain first.

---

The honest shape of it: two boxes designed as code, three geometry bugs
that a clean exit code would have shipped, one dimension change that was
a design decision in disguise, and a stack of estimates I'm still
carrying. The read-it-back check paid for itself three times over. It
also cannot see the two things most likely to cost me a reprint.

The companion post covers the session-driven side of the same week,
including a mesh "repair" that destroyed a letterform while every
assertion passed: [Two MCP bridges, a mesh repair that ate a letterform,
and 204 clipped labels I haven't
fixed](/posts/2026/09/20/two-mcp-bridges-a-mesh-repair-that-ate-a-letterform-and-204-clipped-labels-i-havent-fixed/).
If you're doing parametric CAD for real parts and you have a verification
check I'm missing, I'd like to steal it — [find me on
LinkedIn](https://www.linkedin.com/in/douglas-lockamy-49097b33/).
