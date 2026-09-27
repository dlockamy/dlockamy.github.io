---
layout: post
title: "A phantom 21,500 mm³, a real 818, and a 25% print that beat four verification passes"
date: 2026-09-27
categories: [hardware, devops]
tags: [freecad, cad, 3d-printing, verification, open-hardware, ai-agents, hardware, bambu]
excerpt: "The companion piece to the Dial write-up, on a second device that is still mid-flight. A CAD agent ran an assembly check, got a 21,500 mm³ collision, and — instead of reporting it — went looking at its own checker first, found a rotation helper silently discarding a placement, and only then found the real 818 mm³ conflict hiding behind the fake one. Then: a verification harness that had been substituting a simplified pin for the one every part actually builds, making a defect invisible across the entire project; a chamfer that has cut nothing in any printed part since the day it was added; and a 20-minute quarter-scale print that found what four full CAD passes didn't, in direct contradiction of a rule I'd written down three days earlier."
author: Douglas Lockamy
ai_assisted: true
---

The [previous post](/posts/2026/09/27/the-hole-that-removed-nothing-and-eighteen-screws-that-couldnt-reach/)
was a retrospective: one device, taken all the way to real prints, and the
list of ways an agent-written verification harness reported green over
defects that would have cost a stranger their filament.

This one is the other shape. Same method, second device, except this device
isn't finished and the interesting material is what a working session
actually looks like from inside — including the bits that are still wrong
as I write this.

The device is **Ziggurat**: a modular stacking storage system for board
games. Trays and drawered base modules on a 196 mm grid, pin-and-pocket
corners, and one governing idea that does most of the design work — *every
module's floor is the lid of the module below it.* That's Mancala's own
logic generalised, and it means no module needs a lid, no module needs a
bridged ceiling over a drawer bay, and the stack physically cannot be
assembled with an open compartment.

It also fixes what the corner interface is *for*: **registration, not
latching**. A tower you reorder by hand every game night has to come apart
easily. Gravity holds it down; geometry keeps it square.

196 mm rather than 220, incidentally, because a chess board wants to be as
big as the bed allows and 220 mm fits neither an Ender-3-class 220 × 220
bed nor a Prusa-class 250 × 210 one in practice. The system is built on a
grid, not on a printer.

It's private for now. The licence is settled — CC-BY-4.0 for the geometry,
Apache-2.0 for the code — but publication waits on it actually working.

## The collision that wasn't there

The pass I want to start with was a routine one: build a four-drawer base
module in a quadrant pinwheel layout, verify that two of them stack.

The assembly check came back with a **~21,500 mm³ collision**. That's not a
tolerance issue, that's two parts occupying a shared region the size of a
sugar cube, and it would have sent a perfectly good design back for
redesign.

The agent didn't report it. It went and looked at the checker.

The rotation helper used to place each quadrant was **discarding the prior
placement instead of composing with it** — so a part that should have been
rotated *and* translated was being rotated back to the origin and tested
against geometry it never actually touches. The phantom volume was the
overlap between two parts that, in the real assembly, are nowhere near each
other.

It confirmed that two independent ways before believing it: once in memory,
once against a fresh reconstruction round-tripped through exported STEP.
Both agreed, the helper got fixed to use the shape's own rotate method
properly, and the phantom went to zero.

I find this the single most encouraging thing in either of these two posts,
and it's worth being precise about why. It is not "the AI was careful." It
is that the discipline the harness applies to the *design* — don't trust a
number, reproduce it a second way — got applied to the **harness itself**
when the harness produced an implausible answer. A verification system that
is exempt from its own standard is just a more confident source of wrong
answers.

## And then the real one, at 818 mm³

With the checker fixed, the same pass found a genuine conflict: the corner
interface pad collides with the installed drawer by **~818 mm³** at each
quadrant's outer corner. Small, real, and fatal to the drawer going in.

Fixed with a clearance notch on the drawer — and because the layout is a
rotational pinwheel, *one* notch covers all four installations, which is
the kind of thing symmetry hands you for free if the geometry is generated
rather than drawn four times.

The fix was reported as a trade-off, not a win: the notch costs rail travel
near the front of the drawer. That mattered more than it first looked,
which I'll come back to.

Third thing in the same pass, and the reason I trust the other two: a
louvre pull specified in the design brief simply **didn't fit** the drawer
face it was meant to sit on. 25 mm of face, 29.5 mm of pull. It got scaled
to fit — by a stated, uniform vertical factor of 0.8475, blade count and
order and proportions preserved, the exact number written down. Not quietly
nudged to "close enough," which is the failure mode that makes every other
number in a report worthless.

## The pin that was never the pin

Here's the one that reframes the whole project.

Every part in the system builds its corner pins from a single shared
geometry module. Lid, tray, base module, board — all of them, same code,
which is exactly the discipline you want.

The **cross-part check code did not use it.** It used a deliberately
fillet-less synthetic pin, and said so in its own docstring. A simplification,
documented, reasonable-looking.

Real pins have a 1.5 mm root fillet. That fillet bulges wider than the
pocket's opening at the mating plane: **~1.79 mm³ of real interference per
corner**, measured precisely, confirmed two independent ways. Invisible
across *every* verification pass in the entire project, because the thing
being checked was not the thing being built. And it affects every pin-and-
pocket joint in the system — lid-on-tray, tray-on-module,
module-on-module, all of it.

The follow-up was worse and better. Chasing that fillet produced the real
consequence: **the pin never reaches the pocket floor.** It seats about
1.3 mm short, which means every stacked assembly in this project so far has
been resting on four pin-root fillets rather than the rim-to-rim contact
the entire load-path argument depends on.

That also explained a physical test result I'd taken as good news. I'd
printed a pin-and-pocket coupon, mated it by hand and reported *"the fit is
really good."* It was — and the coupon was structurally incapable of
detecting this failure, because a flat coupon has no seating rim. Two
plates held 1.3 mm apart by fillet contact feel exactly like a good taper
fit in the hand. My positive test result was measuring something else.

And while in there, a second one: a lead-in chamfer added in an earlier fix
had been **built at a Z position below the part's actual material.** It has
cut nothing, in any printed part, since the day it was added. The feature
whose whole job is absorbing misalignment has never existed.

The standing rule that came out of this is the sentence I'd put on the wall:
**no check may substitute a simplified proxy for a feature that ships.**

## Measuring instead of picking

Fixing the fillet needed a number, and two sources disagreed — the design
reasoning said the pin's fillet reaches 4.305 mm, the CAD's own measurement
said ~4.66 mm.

The instruction was: don't pick one, and don't average them. Build the real
0.8 mm-filleted pin and read the reach off the actual geometry.

That produced a **third** number, 4.0003 mm — different from both estimates
— and it was cross-validated first by reproducing the earlier ~4.66 mm
reading for the *old* fillet almost exactly, so the measurement method was
proven against a known value before being trusted on an unknown one.

The bit I liked most: two new standing assertions were written, and both
were **tested against the old broken geometry before being shipped**. One
of them failed that test — it didn't actually discriminate the defect it
was written for — and got redesigned rather than committed. A check that
passes on the geometry it was written to catch is worse than no check,
because now you believe something.

Same pass, the old fillet-less pin function was deleted outright rather
than deprecated. Six call sites had to convert — one more than the dispatch
had named, and the deletion itself is what surfaced the extra one. One of
those conversions was buggy, and the new assertion caught it instead of it
shipping silently wrong.

Interference on the specific stacking check that started all this went from
~7.14 mm³ to **0.000000 mm³**.

## The 20-minute print that beat four CAD passes

Three days before all this I'd written down, on the back of the other
device, that scaled test prints don't work for fit and here's the table
proving it.

Then I ran a 25% scale print of the base module and drawer as a cheap
sanity check before committing hours of PETG, and it immediately found a
defect that had survived **four separate CAD verification passes** —
including a placed-collision check that specifically tested
drawer-versus-module fit.

The drawer's insertion *path* collided with the corner interface pad at
every depth except one. CAD had verified the end state. It had never
verified the journey.

The CAD-side confirmation was unambiguous once someone thought to ask: a
nine-point sweep along the real travel path returned 0.0000 mm³ collision
at the fully-seated endpoint — the position the drawer physically cannot
reach — and **403.7 to 817.6 mm³ everywhere else along the way.** The one
position the check had been sampling was the one position that was clean.

So both statements are true and they are not in conflict, which took a
minute to see:

- A scaled print **destroys clearances**. 0.45 mm nominal becomes ~0.11 mm
  at quarter scale, below what the printer can resolve. It cannot tell you
  whether a tolerance is right, and a tight or fused fit at 25% means
  nothing.
- A scaled print **preserves topology and path**. Does this part physically
  go where it's supposed to? Does the moving thing reach its final position
  without something in the way? Do the openings line up the way the drawing
  says? All of that survives scaling intact.

So the rule got refined rather than reversed: run a 25% print of any new
multi-hour part before committing to a full-scale slice, checking *"does
this even go together"* and never *"is this the right tolerance."* The CAD
harness got a reusable sweep-fit helper in the same pass, applied
everywhere a sliding fit exists. The cheap print is the backstop for
whatever that helper still misses.

## Owning the bill

The insertion fix has a cost, and the first report of that cost was wrong
in the flattering direction.

The original patch was described as costing about 15 mm of rail engagement.
The properly swept version actually costs **64.5 mm of 88.5 mm — 73%** — on
the pad-adjacent side. That correction came from the agent, unprompted,
flagged as worth a follow-up redesign rather than filed as resolved.

A 73% loss of rail engagement on a sliding retention mechanism is not a
footnote. It's the kind of number that, quietly rounded to 15, produces a
product that rattles apart in a year and a maintainer who can't work out
why.

## Real numbers beat the estimate, again

The "fewer, bigger modules" argument for the four-drawer layout was
running on estimates, so it got sliced for an A1 and turned into data.

The four-drawer module costs *more* per module than the single-drawer one —
5h33m against 4h42m, since uniform walls and an internal partition add
material. But each of its drawers is a quarter of the print time of the old
full-width drawer: **59 minutes against 2h22m**. Fully populated, the
four-drawer module and its drawers come to ~9h29m for four hands of
storage, against ~7h4m for one hand the old way.

After the insertion fix the drawer re-sliced at 53 min / 28.1 g, down from
59 min / 33.4 g — lighter *and* faster, because the swept slot removes more
material. Which is a nice sanity check: the fix's reported cost and the
slicer's independent numbers agree about what happened to the part.

That re-slice also only happened because I noticed the sliced file was
stale relative to the STL. It was confirmed by reading git history rather
than by assuming — the STL changed in one commit, the slice hadn't moved.
A geometry fix and its sliced output are two different artifacts and
nothing in the pipeline makes the second follow the first.

## Still open, as of tonight

This is the part a finished write-up doesn't have.

The **drawer's rail-and-groove retention may not be constructed the way it
claims.** Building a clearance test coupon — 73 × 30 × 10 mm, six solids,
three clearance variants at 0.35 / 0.45 / 0.55 mm per side, length-coded
20 / 25 / 30 mm so I can identify them by eye — forced a close reading of
the real module code, and the rail appears to sit flush with the drawer's
nominal edge rather than protruding into a groove, with the partition-side
groove cutting material out of the open bay instead of the partition.

Earlier assembly checks verified overall drawer-in-bay fit. None of them
ever verified rail-in-groove *engagement* specifically. So the sliding
retention mechanism itself is genuinely in question, separate from and
underneath the question of which clearance value is correct. The already-
sliced parts remain valid printable objects; that's not the issue. The
issue is whether the feature that's supposed to hold a drawer in does
anything at all.

Sequencing is deliberate: pick a clearance from the coupon test *first*,
fix the construction using that confirmed number *second*. Fixing it twice
is worse than waiting.

Also open: the coupon exports as one STL containing six disconnected
bodies, not six objects the slicer can assign different filaments to —
verified by checking the object count in the sliced file, which is 1. So it
tests three clearance *values* geometrically and does not test the real
PLA-rail-into-PETG-groove material pairing the actual assembly uses. Stated
as a limitation rather than assumed away.

And the coupon strings a little inside the groove channel. That one got
diagnosed rather than tuned: the Dial's stringing incident was a genuine
16 mm unsupported overhang past a 10 mm threshold, but this groove's bridge
is 3 mm, nowhere near it — so this is ordinary travel-move stringing across
six small solids sitting close together on a tiny plate, cosmetic, not the
same failure class. Deliberately deferred and carried forward as an
explicit watch-item for the first full-scale print, where the same groove
appears eight times with a lot more surface area. Not chased tonight.

---

The honest shape of this one: in a single day, on one unfinished device,
an agent-driven CAD pipeline found a bug in its own checker before it could
condemn a good design, found a real 818 mm³ conflict hiding behind the fake
one, discovered that the pin it had been verifying for the entire life of
the project was not the pin any part actually builds, discovered a feature
that has never existed in a printed part, and got beaten to a fifth defect
by twenty minutes of quarter-scale PLA.

The first three of those are the method working. The last two are the
method's limits, and the useful thing is that they're limits in different
directions: one says *your proxy isn't the part*, and the other says
*geometry verification checks states, and assembly is a path*.

I'd have caught none of this by hand, and I'd have caught none of it by
reading reports. Both posts land in the same place, from opposite ends of a
project's life: probe the artifact, generate the list, make every new check
fail once on the exact thing that fooled the last one — and hold the
verification code to the standard you hold the design to, because it is the
only thing standing between you and a confident green run over a part that
cannot be built.

If you've got a verification check for assembly *paths* rather than
assembly *states*, I'd genuinely like to see it — [find me on
LinkedIn](https://www.linkedin.com/in/douglas-lockamy-49097b33/).
