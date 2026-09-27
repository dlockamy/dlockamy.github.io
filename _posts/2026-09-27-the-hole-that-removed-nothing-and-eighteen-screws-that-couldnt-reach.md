---
layout: post
title: "The hole that removed 0.00 mm³, and eighteen screws that couldn't reach"
date: 2026-09-27
categories: [hardware, devops]
tags: [freecad, cad, 3d-printing, verification, open-hardware, ai-agents, hardware, bambu]
excerpt: "A full device — enclosure, BOM, slicer project, assembly docs — designed as parametric code and verified by an agent rather than drawn by hand. Seven CAD rounds, thirty-one feature probes, two hundred and seventy-six interference pairs, all green. Then: two face plates that could not enter their own shells, a clearance hole that removed zero material and left a 0.29 mm nick, a diffuser held by nothing at all, and eighteen of twenty-five fasteners specified at a length that physically cannot work — four separate fastener checks passing the entire time, because every one of them modelled the hole and none of them modelled the screw. Every defect here passed a check first. That is the whole point."
author: Douglas Lockamy
ai_assisted: true
---

Last week I wrote about two dev-mule boxes designed as parametric scripts,
and the three ways those scripts lied while exiting cleanly. This is the
next thing that happened, which is that the studio took the same approach
and pointed it at a real device meant to go out as an open build —
something a stranger downloads, prints, buys parts for, and assembles,
with no access to me when it doesn't work.

The device is a 7" touchscreen control panel with a big detented dial:
Raspberry Pi 5, the official Touch Display 2, 309 × 200 × 66 mm, every
enclosure part printable on a 250 × 210 mm bed, about $323 of bought parts.
"The Dial" is a working name. It went from a concept sheet to a private
repo with parametric CAD, a researched BOM, a nine-plate Bambu Studio
project, print-oriented STLs, generated assembly drawings and generated
wiring diagrams over about two days, almost none of it drawn by hand. The
CAD was generated and verified by an agent. I reviewed and I printed.

What I want to write down is not "AI can do CAD now." It's the specific
shape of what that verification catches, what it misses, and the single
most useful sentence I got out of the whole exercise:

**A check that can pass for the wrong reason is not a check.**

Every defect below passed something before it was caught. Several passed
everything, for several rounds, and one of them cost real plates.

## The standard, restated

Same as before: nothing is trusted from the build report. Every part gets
its *exported* STEP read back in and interrogated — solid count, validity,
shell count, bounding box against spec. That baseline is table stakes and
it caught nothing interesting here, because the interesting defects on a
multi-part assembly are not inside parts. They're *between* parts.

So the checks grew. By the end there were about twenty of them, and each
one exists because a specific real defect got past all the others.

## Checks that fired into empty space

The first category is the ugly one: a check that ran, returned a number,
and the number was meaningless.

A grille cut landed in **empty space** — the boolean ran against
coordinates where no material was. Solid count: fine. Validity: fine.
Interference: fine. The part simply had no grille. Nothing in the run
distinguished "I cut a hole" from "I cut at nothing," because the check
asserted that the *operation* happened, not that the *feature* existed.

Worse, when the probe that was supposed to verify those holes was written,
it was written **from the same wrong coordinates**. It fired into the same
void, found the void, and reported success. Two independent-looking green
results, one shared mistake.

A speaker pod passed its interference check while bolted to the **outside**
of the shell, because the check tested the pod where it had been wrongly
placed rather than where it installs. A wall-mount plane got read off the
wrong face, which would have hung the whole panel 11 mm *inside* the
drywall. A "sound path" check confirmed an opening in every layer between
the speaker and the outside world — each layer individually — while a
solid diffuser sealed the stack. Every layer passed. The path didn't
exist.

And then the one that actually costs money.

## 448 mm³ of overlap that nobody ever asked about

Two face plates would not enter their own shells. Real, gross,
448 mm³ of solid-on-solid overlap. Not a tolerance problem — the parts
occupy the same space.

The interference check had been running for rounds. It was a **hand-written
list of pairs**, and the list had never paired a face plate with its own
body. Why would it? Nobody writes down the pair they consider obviously
fine. The check was green because the failing case was not in it.

The fix is a rule rather than a pair: enumerate by generation. All pairs,
built from the model — 276 of them, with exactly one named skip that has
to justify itself in a comment. Not 40 pairs someone remembered.

And nesting *clearance*, not just non-overlap. Two parts that meet at
exactly 0.000 mm in CAD do not go together in PLA. A 0.4 mm allowance is a
budget, and anything below it fails.

## A hole that removed 0.00 mm³

The band insert and the diffuser had no mounting holes. At all.

Not undersized. Not misplaced by a hair. The boss centres fell **1 mm
outside the part outlines**, so the Ø3.4 mm clearance cut intersected the
corner of the part and nothing else. It removed **0.00 mm³** and left a
0.29 mm nick in the edge where a hole was supposed to be.

Both parts were therefore held by nothing. The diffuser's nearest neighbour
in *any* direction was 3.4 mm away — unlocated in X, Y and Z, a part
floating in the assembly, and every geometry check green.

Three checks came out of that, and they only work as a set:

- **Fastener-hole-exists**, measured as *volume actually removed versus the
  cylinder you asked for*. A hole that removes zero should be the loudest
  failure in the run.
- **Minimum feature wall**, probed on the *finished* part — because
  elsewhere a grille perforation had eaten its way to 0.08 mm from a screw
  hole. The hole existed; there was no part left around it.
- **No floating part.** If nothing is within touching distance in any
  direction, it isn't installed, it's hovering.

The first two are a genuine pair and neither is sufficient alone. On a
finished part, "a real hole" and "the edge just ends here" both read as
fully open.

Same family: four heat-set-insert bores were cut correctly and then
**filled back in** by a support rib that got fused afterwards. Cutting is
not the same as having cut. Assert on the finished shape or a later boolean
silently undoes an earlier one.

## Model the fastener, not the hole

This is the expensive one, and it's the lesson I'd keep if I could only
keep one.

**Eighteen of twenty-five fasteners were specified with a screw that cannot
work.**

Two joints needed roughly 49 mm and 61 mm of screw and the BOM said
M3 × 12. The boss ended 10 mm in, the back wall sat 45–56 mm behind it, and
the screw was expected to cross open air to get there. Others went the
other way and bottomed out, standing 3.8 mm proud of a surface they were
supposed to be clamping.

There were **four separate fastener checks** in the harness at the time.
Every single one passed.

All four modelled the **hole**. Does it exist? Is there material around it?
Is the driver path clear? Did a later operation fill it in? Those are four
good questions about a hole. Not one of them modelled the **screw** as a
physical object with a length.

So now it is one. For every fastener: a real object, from its seating face,
through each part it crosses, to its thread engagement — and an assertion
that the screw the BOM literally specifies both *reaches* and *engages*,
with engagement inside a stated range. Too long fails as hard as too short;
a screw that bottoms out in a blind boss holds its own head off the surface
and clamps nothing.

Two traps inside that check, both of which bit:

**Where the head bears is not obvious.** A trim screw looked like it passed
through a 3 mm face plate. It didn't — the boss passed through a 7.9 mm
hole in that plate, the head never touched it, and the clamped travel was
zero. Measure the seating face off the geometry. Do not assume the near
part carries the load.

**A long boss is not a bare cylinder.** Lengthening a boss to 50–60 mm to
meet the screw produces exactly the floating cantilever a slicer refuses.
It needs a printed gusset, and getting that right took four rounds against
the *real slicer*, because CAD-level overhang reasoning never converged on
it.

Related, and a different question entirely: debossed labels with
0.06–0.18 mm strokes against a 0.4 mm nozzle. Valid geometry. Correctly
placed. Slices without a warning. Comes off the bed blank, because nothing
narrower than one extrusion width can be extruded at all. Every other check
in the harness asks *is this geometry correct*. That one asks *can this
machine make it*, and you have to ask it separately, with the nozzle width
and layer height written down as constants.

## The exit code that could not fail

Now the part that makes all of the above worse in retrospect.

`freecadcmd` — the headless CLI I'm running everything through — **catches
an uncaught exception in a script, prints `Exception while processing
file`, and exits 0.**

A failed assertion reports success. A plain syntax error reports success.
Every "exit 0, all checks passed" in this build's history, mine and the
agent's alike, was reading a status code structurally incapable of
reporting failure.

```
$ freecadcmd checks.py
Exception while processing file: /path/checks.py
$ echo $?
0
```

`sys.exit(1)` does propagate. So every assertion routes through a helper
that calls it — and, more importantly, the plumbing got proven by **forcing
a failure and watching the exit code**, not by reading the helper and
agreeing with it. Before trusting any toolchain's status code, spend thirty
seconds making it fail on purpose. This is the second time in two weeks
that same CLI has handed me a clean exit over nothing happening; the first
was it setting `__name__` to the filename, so a main-guarded script exports
no files, prints no error, and exits 0.

## The class that costs plates: a reference that moved

The two defects that actually burned filament are the same defect wearing
different clothes. Something was **derived from a number, and then that
number moved.**

The window border was widened to stop a boss printing in air. The insert
and the diffuser are sized off that window — and nobody re-derived them, so
their mounts ended up 1 mm outside the parts and their screw holes became
nicks. That's the 0.00 mm³ hole above.

A boss diameter grew to accept a deeper heat-set insert. The face plate
outline around it was never re-checked. That's the 448 mm³ overlap above.

Neither is a geometry problem. Both are bookkeeping problems that the
geometry inherits, and both passed every check because the checks had been
enumerated by hand *from the design as it used to be*. Derive it, don't
restate it. Generate the list. Assert the feature, not the operation that
was supposed to produce it.

## Then print it, because the slicer isn't the last word

Slicing every plate and failing on any warning is itself a real test — it
caught a 194 mm unsupported bridge on a tub that had been oriented
open-side down, plus a floating shelf and floating bosses that no geometry
check had flagged.

And then a real print found something the slicer never mentioned. The face
plate's screen-window rebate was a pocket in the **bed face**, so its ledge
printed over air. Bambu gave no warning at all. Fixed by dropping the
rebate entirely — the front is now one flat plane with 100% first-layer
contact and the trim sits proud by 1.5 mm instead of recessed.

The second print strung at the cable-slot opening: a 16 mm unsupported
ledge that the newly-written check had *already reported* before the print
confirmed it. Which is the better of the two outcomes, and the reason a
check that merely reports is not a check. Decide the threshold — here,
any downward-facing surface with only air under it, over 10 mm, fails the
build — or the report is just a thing you scroll past.

## Iterate on coupons, never on a scaled model

The obvious way to test fit cheaply is to print the big parts at 25%. For
*fit*, it does not work, and the reason is worth having in a table:

| | Full | ×0.25 |
|---|---|---|
| Fit clearance | 0.40 mm | **0.10 mm** — under one extrusion; parts fuse |
| Wall thickness | 3.0 mm | 0.75 mm — under two perimeters |
| M3 clearance hole | Ø3.4 | Ø0.85 — no screw exists |
| Heat-set insert | Ø4.0 × 6.5 | Ø1.0 × 1.6 — no such insert |

Scaling is uniform. Manufacturing isn't. Every defect in this post is
clearance-scale — a boss 2 mm into a wall, mount holes 1 mm outside a part,
a blocked screw axis — and a quarter-scale model deletes precisely those
and confirms only what you already knew, which is that the lid sits on the
box.

What works instead is **full-scale section coupons**: intersect the real
exported part with a box around each fastener or interface, cutting every
member of a mating pair with the same box so the interface survives, each
coupon kept in its parent's print orientation so it tests the same
overhangs and the same first layer.

But know what a coupon can't see, because this one hurt. A 37 mm coupon of
a 63 mm-deep part passed every fit test it was given while the screws for
that joint were 44 mm too short — the span only exists at full depth. A
coupon answers "do these two surfaces meet correctly." It never answers "is
this assembly buildable."

(There is a real exception to the no-scaled-models rule, which I found on a
different device three days later and which the companion post covers.)

## One more, on telling people what to reprint

After a fix, you have to say precisely which parts changed, or you either
waste a stranger's filament or leave a stale part in their build.

Do not derive that list from volume and bounding box. A countersink cut on
the *wrong face* of a speaker cup moved 77 mm³ of material with a volume
delta of **0.0000 mm³** and a byte-identical bounding box. That part needed
reprinting and every summary statistic in the run said it hadn't changed.
Compare shapes — boolean difference in both directions against the previous
release, per part.

## What isn't done

Honest column.

The device's software — dial navigation, the idle-reset behaviour, the LED
palette — is unowned and unstarted. The enclosure is real and the thing it
contains does nothing. First light is going to be plain Raspberry Pi OS
Bookworm rather than the studio's own OS image, because a live readiness
check found that image has no Raspberry Pi target at all and no arm64
artifact of the app exists anywhere, which is a much shorter sentence than
the plan it replaced.

Round two of prints hasn't happened; every plate needs one clean full-scale
run before any of this is public. The BOM is still single-sourced per line,
which reads like an ad and is getting a second source per row. And the
public name isn't settled.

---

The honest shape of it: an agent produced a complete, coherent, genuinely
well-organised device package in about two days, and then the verification
harness — also agent-written — reported green through a grille that didn't
exist, two plates that couldn't enter their shells, two parts held by
nothing, and eighteen screws that couldn't span their own joints, on a CLI
that returns 0 when the script crashes.

None of that is an argument against doing it this way. The same pipeline
found and fixed all of it, faster than I would have, and wrote the check
that prevents each one from recurring. But the value is not in the
generation. It's in the discipline that every new check gets **made to fail
on the exact geometry that fooled the old one, once, before anybody trusts
it** — and in probing the exported file instead of reading the summary.
Every serious defect in this build was found by interrogating geometry.
None of them were found by reading a report that said everything passed.

The companion post is the same discipline on a second device, mid-flight,
including the pass where the CAD agent caught a bug in its own verification
code before it could reject a perfectly good design:
[A phantom 21,500 mm³, a real 818, and a 25% print that beat four
verification passes](/posts/2026/09/27/a-phantom-collision-a-real-one-and-a-quarter-scale-print-that-beat-four-verification-passes/).

If you run parametric CAD for real parts and you have a check that isn't in
this post, I'd like to steal it — [find me on
LinkedIn](https://www.linkedin.com/in/douglas-lockamy-49097b33/).
