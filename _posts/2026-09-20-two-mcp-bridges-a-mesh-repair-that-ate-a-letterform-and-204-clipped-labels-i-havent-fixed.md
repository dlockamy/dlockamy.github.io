---
layout: post
title: "Two MCP bridges, a mesh repair that ate a letterform, and 204 clipped labels I haven't fixed"
date: 2026-09-20
categories: [devops, tooling]
tags: [mcp, gimp, freecad, automation, ai, verification, cad, svg]
excerpt: "I wired GIMP and FreeCAD up so a session could operate them the way it already operates a shell. Both bridges work; one of them can never run in CI, which changes what the capability is for. Then the night turned into three instances of one failure: a mesh repair that carved a wedge out of a letterform while every assertion passed, a massing model that was only wrong from one view, and an SVG audit confidently wrong about itself. The real defect it found — 204 clipped labels across 24 sheets — is still unfixed, and why I didn't just fix it is the useful part."
author: Douglas Lockamy
ai_assisted: true
---

Can a session *operate* GIMP the way it already operates a shell? Not
shell out to ImageMagick — actually drive the application, with its
layers and filters and text engine. The answer turned out to be yes, and
the same approach worked for FreeCAD. Both bridges are installed and
verified now.

The boundary goes first, because it changes what the capability is *for*:
one of these two can never run unattended, so it does not replace the
headless CAD pipeline I already had. It sits beside it. I nearly missed
that on install night, which would have been an expensive thing to
discover later.

## The row that decides everything

Two bridges, installed and verified the same night:

| | GIMP | FreeCAD |
|---|---|---|
| Bridge | `gimp-agent-mcp` 0.5.0 | `neka-nat/freecad-mcp` 0.1.24 |
| App | GIMP 3.2.6 | FreeCAD 1.1.3 |
| Tools exposed | 39 | 17 |
| **Headless** | **yes** | **no — the GUI must stay open** |

That last row is the load-bearing fact. The FreeCAD addon imports
`FreeCADGui` at module scope, so every tool fails the moment the window
closes. The repo ships a `test_headless.py`, which reads like reassurance
and isn't: it's a *tool that shells out to* `freecadcmd` for long jobs,
not evidence of a headless server.

Practical consequence, stated plainly: the FreeCAD bridge cannot run
unattended, which means it cannot run in CI, which means it is a *review
and exploration* surface rather than a generation one. The headless
`freecadcmd` procedure that actually produces my parts is untouched and
still the thing in the pipeline. Worth establishing before you commit,
because "I can drive FreeCAD from a session now" and "I can generate
parts in CI now" are very different sentences and only one of them is
true.

The generalised check, now written into a shared skill doc so the next
app gets the same treatment instead of the same lesson:

```sh
grep -n "^import .*Gui\|getMainWindow\|QApplication" <addon>/*.py
```

A module-level GUI import means a human has to keep a window open. Say
that out loud on day one.

## Read the bridge before you install it

These bridges exist to execute arbitrary code inside a desktop app.
That's the feature, not the flaw — but it is a local code-execution
surface and it deserves ten minutes of reading:

```sh
grep -rn "bind\|listen\|0\.0\.0\.0\|127\.0\.0\.1\|token\|secrets\." <pkg>/
grep -rn "urlopen\|requests\.\|http[s]*://\|subprocess\|exec(\|eval(" <pkg>/
```

What you want to find: loopback-only binds, a per-install random token,
no outbound HTTP. What you *will* find, and should expect, is an
`exec`-style endpoint. Both of mine bind loopback only — GIMP over a
token-authed TCP socket, FreeCAD over RPC on `:9875`.

The other thing I'd do again: prove the server over stdio *before*
restarting the client. MCP config is read at startup, so you can't test
new tools by calling them — you're stuck in a restart loop debugging
blind. Driving the server by hand (`initialize` →
`notifications/initialized` → `tools/list` → `tools/call`) catches every
install problem while it's still cheap, and hands you the real tool names
and schemas instead of the README's.

A few things that cost me time and are pure trivia until they aren't.
Tool names are namespaced, so it's `gimp_new_image`, not `new_image`. The
code-execution conventions differ and don't transfer — GIMP's
`gimp_run_python` returns a variable named `result`; FreeCAD's
`execute_code` returns `print()` output only and silently discards
`result`. And FreeCAD's companion CLI lives *inside* the macOS `.app`
bundle, so it isn't on `PATH`, and every feature that shells out to it
fails with "not found" until you pass the absolute path.

## Every bridge will report success for a no-op

So I closed each claim against evidence the domain itself produces. GIMP:
25/25 self-tests, 17/17 recipe tests, plus the independent stdio probe —
and renders pulled back and *looked at*. FreeCAD: geometry read back and
compared to a hand-computed volume — 49175.7 mm³ expected against
49175.7 actual through the GUI path, 5738.1 against 5738.1 through the
headless one. Same model, both paths, agreeing exactly.

That felt like enough. It wasn't, three times in one night.

## The wedge

I'd built a two-colour badge — a Lockamy Studios nameplate, raised
letterforms on a rounded plinth, explicitly a proposal rather than an
approved mark. DM Sans Bold draws a lowercase `k` as two contours that
overlap by 0.07 mm³. The union is a perfectly valid BREP: one solid, one
shell, `isValid()` true. FreeCAD's mesher still flags one non-manifold
edge.

So I cleared the flag. `Mesh.removeNonManifolds()` did exactly what its
name promises and what its name does not mention: it deletes facets. It
carved a visible wedge out of the `k`.

Every assertion in that build passed. Solid count, validity, and the
width-matching assert I had written specifically so the script would fail
loudly if the two lines of type drifted apart — all green, on a file with
a mutilated glyph in it. Nothing caught it. I caught it later, looking at
the slicer preview, after the bad file had already been opened by someone
else.

Two lessons out of that, and the second one is pinned to the wall:

**The tools disagree, and the consumer wins.** FreeCAD flags the fused
badge as non-manifold; `BambuStudio --info` reports that same mesh as
`manifold = yes`. I went chasing a defect my actual consumer doesn't
have — and finer tessellation, an alternate mesher, and a 2D face-union
before extrusion all left the edge exactly where it was. It's inherent to
the glyph outline, it's harmless, and the slicer handles it.

**A passing check is not a look.** The repair satisfied the entire test
suite while destroying a letter. Never repair a mesh to clear a warning
you haven't first proved matters.

## The same shape, twice more

The second instance was a massing model I was building from a concept I'd
only ever drawn in 2D. The canted head looked right in isometric — and
was structurally wrong: the cant had been cut as a recess into a vertical
face instead of applied to the head. Only the `Right` view exposed it.
One view is not verification either.

The third is the funniest, because the thing that was wrong was the
checker. I had a real defect to chase: SVG `<text>` doesn't wrap, so long
annotation prose placed in a single `<text>` element is simply clipped at
the `viewBox` edge in every correct renderer. My first pass at auditing it
did the obvious thing — read `font-size` off each `<text>` element,
estimate the run width, compare against the viewBox. It over-reported by
roughly 45%, because `font-size` is frequently inherited from a parent
`<g>` and the naive per-element read falls back to a default that's wrong
in both directions. (I'm hedging that number deliberately: it's what I
recorded at the time and it isn't reproducible from the fixed script.)

The corrected version walks the tree and carries inherited style down.
The honest numbers: all 24 concept sheets affected, 204 overflowing
`<text>` elements, worst single case running about 900px past a
980px-wide sheet. It's a template defect, not a per-sheet accident.

Three instances, one shape. A mesh repair agreeing with the assertions
that blessed it; a model agreeing with the one view I rendered it in; a
checker agreeing with its own default. The useful form of the rule isn't
"be skeptical," which is free and worthless — it's a question you can
actually ask: *independent with respect to what?* A second source that
shares the thing that could be wrong is not a second source.

## What I haven't fixed

The 204 clipped labels are still clipped. The fix is a
wrap-into-`<tspan>` pass, wrapping adds vertical height, and several
legend blocks already sit near the bottom edge — so a blind fix trades a
clipping bug for a collision bug, and I'd find out about the second one
the same way I found the first. It needs a re-render of each sheet to
catch what it introduces, which makes it its own task rather than a
one-liner I can slip in tonight.

The one set of sheets with zero overflows had no luck in it: they were
render-verified while being authored. The template the other 24 came from
never was. That's the whole post in one comparison.

Also not done: the FreeCAD GUI session doesn't survive a reboot, so the
capability quietly evaporates when the machine restarts, and I haven't
solved that beyond "open the window again."

---

The honest shape of the night: two bridges installed, one of them
narrower than it looks, and three separate opportunities to ship a defect
that every automated check I owned would have blessed. The procedure is
written down tool-neutrally now — bridge selection, auditing the
execution surface, the headless question, proving it over stdio,
verifying by measuring *and then looking* — so the next app I wire up
gets the treatment rather than the lesson.

If you're driving desktop apps from a session and you've found a saner
answer to the GUI-must-stay-open problem, I'd genuinely like to hear it —
[find me on
LinkedIn](https://www.linkedin.com/in/douglas-lockamy-49097b33/).

The companion post covers the CAD side of the same week: two dev mules
designed as code, two toolchain bugs, and a box that grew 51% because a
panel didn't fit — [Two toolchain bugs, a box that grew 51%, and a tilt
I've never actually looked
at](/posts/2026/09/20/two-toolchain-bugs-a-box-that-grew-51-and-a-tilt-ive-never-actually-looked-at/).
