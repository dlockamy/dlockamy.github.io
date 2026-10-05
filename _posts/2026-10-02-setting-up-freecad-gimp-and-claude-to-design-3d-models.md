---
layout: post
title: "Setting up FreeCAD, GIMP and Claude to design 3D models — and making the setup prove its own work"
date: 2026-10-02
categories: [hardware, tooling]
tags: [claude-code, freecad, gimp, mcp, 3d-printing, cad, python, macos, linux]
excerpt: "An overview of the setup I use to design 3D-printable parts with Claude Code, headless FreeCAD and GIMP, and the three ways it lies to you if you let it: a model with a hole missing passes the topology checks, FreeCAD's command line exits 0 on a failed script, and the checker itself can be wrong. The step-by-step now lives in a twelve-part tutorial in the public repo."
author: Douglas Lockamy
ai_assisted: true
---

> **Updated 2026-10-04.** This post started as the whole setup guide, about 4,700 words. It is now the overview and primer. The step-by-step moved into a [twelve-part tutorial](https://github.com/dlockamy/claude-cad-workbench/blob/main/docs/tutorial/README.md) in the repo: one short part per idea, each ending in a check you can run and a link to the next part. Where a section below says "tutorial part N", that is where the detail is.

I design small hardware — enclosures, panels, brackets, mounts — and for the last few weeks most of that design work has been Claude writing CAD as code, FreeCAD running it headless, and GIMP handling the images around it. Getting Claude to drive FreeCAD is the easy half. The hard half is getting the setup to **tell you when it is wrong**, and most of this post, and most of the tutorial, is about that.

Everything lives in a public repo: [`dlockamy/claude-cad-workbench`](https://github.com/dlockamy/claude-cad-workbench). It has four skills, a CAD subagent, an installer, a read-only environment checker, an example part, and the tutorial.

## The setup in one table

| Layer | Tool | Runs headless? | When you need it |
|---|---|---|---|
| Driver | Claude Code | n/a | always |
| CAD | FreeCAD, via `freecadcmd` | **yes** | always: this is the main path |
| CAD, live window | FreeCAD + the `freecad-mcp` bridge | **no** | only to *see* the model |
| Images | GIMP 3.2 + the `gimp-agent-mcp` bridge | **yes** | renders, concept sheets, labelled assets |

The default path has **no bridge at all**. Claude writes a Python script, `freecadcmd` runs it, and the script exports STEP and STL and checks its own work. That is reproducible, runs unattended, and works in CI. The bridges are an optional layer on top.

The one idea that holds it together: **a CAD script should be a test that happens to emit a part.** If you want to try the habit before reading anything else, [part 1 of the tutorial](https://github.com/dlockamy/claude-cad-workbench/blob/main/docs/tutorial/01-the-idea-and-the-first-check.md) is a ten-minute first check.

## Three ways it lies to you

**1. A part with a hole missing passes the topology checks.** The example in the repo is a mounting plate whose script computes its expected volume by hand, verifies the STEP file it wrote rather than the object that wrote it, and asserts that each hole is actually open. Break it on purpose, by moving one hole off the plate, and this is what comes back:

```
  ok    one solid (got 1)
  ok    shape is valid
  ok    bounding box 80.000 x 50.000 x 10.000 == spec 80.000 x 50.000 x 10.000
  FAIL  volume 25011.53 mm3 vs hand-computed 24957.05 mm3 (0.2183% off)
  FAIL  hole 0 removed 0.00 mm3 (a real hole removes 54.48)
```

Every topology check is green. A boolean cut whose tool sits outside the part "succeeds": it removes nothing and raises nothing. Only the volume and feature checks catch it. ([Tutorial parts 3 and 4](https://github.com/dlockamy/claude-cad-workbench/blob/main/docs/tutorial/03-write-a-part-that-checks-itself.md).) I wrote about the real-world version of this in [the hole that removed 0.00 mm³](/posts/2026/09/27/the-hole-that-removed-nothing-and-eighteen-screws-that-couldnt-reach/).

**2. `freecadcmd` exits 0 on a failed script.** Run a script file that raises, or has a syntax error, and FreeCAD prints the exception and returns success. A script that raises also runs twice, and unflushed output is lost when `sys.exit` follows it, so a red CI build can arrive with no explanation. `freecadcmd -c "..."` is honest; a script file is not. The fix is dull: record failures, call `sys.exit(1)`, and `print(..., flush=True)` everywhere. I reproduced all of it on FreeCAD 1.0.2 on macOS and again on 1.1.4 on Linux. ([Tutorial part 4](https://github.com/dlockamy/claude-cad-workbench/blob/main/docs/tutorial/04-make-it-fail-on-purpose.md).)

**3. Your checker can be wrong too.** The STL preview renderer I started from tipped the model the wrong way, so +Z pointed down the screen and a raised boss drew as a recess. It looked plausible, and I only caught it because I knew what the part should look like. The whole bug was one sign.

![The mounting plate rendered from its STL: four clearance holes and a raised centre boss with an insert bore](/images/freecad-mount-plate-iso.png)

That image is correct. Test a checker on a part whose answer you already know before you trust it on one you don't. ([Tutorial part 5](https://github.com/dlockamy/claude-cad-workbench/blob/main/docs/tutorial/05-look-at-the-part.md).)

## Teaching Claude the house rules

Claude Code loads skills when their description matches the task. The repo's four skills (`parametric-cad-verify`, `drive-desktop-app`, `raster-compositing`, `multi-material-print-handoff`) and the `mechanical-cad-engineer` agent are plain markdown. There is no magic in them: they hold the list of things that already went wrong once, so Claude doesn't rediscover them on your part, and the long-term value is that list getting longer. `./install.sh` links them into `~/.claude`, or `claude --plugin-dir` loads them for one session. ([Tutorial part 6](https://github.com/dlockamy/claude-cad-workbench/blob/main/docs/tutorial/06-teach-claude-the-house-rules.md).)

## The two bridges, briefly

GIMP's bridge is the easy one: it has a real headless mode, and a pixel read back to a value you knew in advance is a good proof that it works. FreeCAD's needs the GUI open, so it is for *looking*, never for unattended work. It also exposes an `execute_code` endpoint on loopback with no auth token by default, so I leave auto-start **off** and start it per session. Whichever bridge you add, prove it over stdio before you restart Claude, and verify by measuring a result you computed beforehand, not by trusting "the call succeeded". ([Tutorial parts 7 to 9](https://github.com/dlockamy/claude-cad-workbench/blob/main/docs/tutorial/07-the-gimp-bridge.md).)

## New since the first version: from a drawing to a rigged model

The same habits turned out to work on a different job: taking one generated image of a character to a skinned, rigged 3D model that plays animation clips in a web viewer. I did it twice, on a push-up ice cream pop mascot and a humanoid. What carried over, and what didn't:

- **The back is invented.** One front view nearly covers a revolve; for a humanoid, the depth and the whole back are guesses. Say so.
- **Stills hide rig bugs.** Both rigs looked right from every angle and had joints that did nothing. The Khronos validator will pass a rig with a dead joint (the repo's example shows it: the deliberately broken tube gets 0 errors and 0 warnings), because valid and working are different claims. The repo now has a small `check_rig.py` that catches joints deforming nothing.
- **A clean slice is not a printable model.** Both models slice without error in Bambu Studio. The mascot would not print as built: its stick ends in a rounded tip, so the first layer is 38 mm of path and it stands on something close to a dot. The slicer says "Success" and nothing in its output warns you; `slice_report.py` prints the number.

Neither model has been printed. ([Tutorial parts 11 and 12](https://github.com/dlockamy/claude-cad-workbench/blob/main/docs/tutorial/11-from-a-drawing-to-a-model.md).)

## What this setup can't tell you

It checks geometry, not fit: parts that meet at 0.000 mm in CAD won't mate in PLA, and at quarter scale a 0.4 mm clearance becomes 0.1 mm and the parts fuse. It checks the holes you thought of: the costliest defect I've had was [18 of 25 fasteners specified with a screw that couldn't work](/posts/2026/09/27/the-hole-that-removed-nothing-and-eighteen-screws-that-couldnt-reach/), past four fastener checks that all passed. A slicer treats one file as one rigid body with one orientation. And the first real print is still the real test, as the [quarter-scale print post](/posts/2026/09/27/a-phantom-collision-a-real-one-and-a-quarter-scale-print-that-beat-four-verification-passes/) shows. ([Tutorial part 10](https://github.com/dlockamy/claude-cad-workbench/blob/main/docs/tutorial/10-what-this-cannot-tell-you.md).) The install-night story for the bridges is [here](/posts/2026/09/20/two-mcp-bridges-a-mesh-repair-that-ate-a-letterform-and-204-clipped-labels-i-havent-fixed/).

## What I verified, and what I didn't

Everything in the tutorial was run on a real machine. The repo README has a ["Verified on" table](https://github.com/dlockamy/claude-cad-workbench#verified-on) with the dates, tool versions and results: macOS with FreeCAD 1.0.2 and GIMP 3.2.6, and Linux with FreeCAD 1.1.4 and Bambu Studio 2.8.2. **Not run:** Windows, GIMP 2.10, any slicer other than Bambu Studio, and a real print of either model. If something doesn't reproduce for you, open an issue.

## Where to go next

The tutorial is twelve short parts, and each links to the next:

1. [The idea, and the first check](https://github.com/dlockamy/claude-cad-workbench/blob/main/docs/tutorial/01-the-idea-and-the-first-check.md)
2. [Install the tools](https://github.com/dlockamy/claude-cad-workbench/blob/main/docs/tutorial/02-install-the-tools.md)
3. [Write a part that checks itself](https://github.com/dlockamy/claude-cad-workbench/blob/main/docs/tutorial/03-write-a-part-that-checks-itself.md)
4. [Make it fail on purpose](https://github.com/dlockamy/claude-cad-workbench/blob/main/docs/tutorial/04-make-it-fail-on-purpose.md)
5. [Look at the part, and check your checker](https://github.com/dlockamy/claude-cad-workbench/blob/main/docs/tutorial/05-look-at-the-part.md)
6. [Teach Claude the house rules](https://github.com/dlockamy/claude-cad-workbench/blob/main/docs/tutorial/06-teach-claude-the-house-rules.md)
7. [The GIMP bridge](https://github.com/dlockamy/claude-cad-workbench/blob/main/docs/tutorial/07-the-gimp-bridge.md)
8. [FreeCAD's live bridge](https://github.com/dlockamy/claude-cad-workbench/blob/main/docs/tutorial/08-freecads-live-bridge.md)
9. [Prove a bridge before you trust it](https://github.com/dlockamy/claude-cad-workbench/blob/main/docs/tutorial/09-prove-a-bridge-before-you-trust-it.md)
10. [What this setup cannot tell you](https://github.com/dlockamy/claude-cad-workbench/blob/main/docs/tutorial/10-what-this-cannot-tell-you.md)
11. [From a drawing to a model](https://github.com/dlockamy/claude-cad-workbench/blob/main/docs/tutorial/11-from-a-drawing-to-a-model.md)
12. [Check the rig](https://github.com/dlockamy/claude-cad-workbench/blob/main/docs/tutorial/12-check-the-rig.md)

Or, if you only try two commands, make them these, and run the second one first, honestly:

```sh
git clone https://github.com/dlockamy/claude-cad-workbench && cd claude-cad-workbench
freecadcmd examples/mount-plate/mount_plate.py                       # passes, exit 0
MOUNT_PLATE_BREAK=1 freecadcmd examples/mount-plate/mount_plate.py   # fails, exit 1
```

Seeing a model with a missing hole sail through every topology check, and then watching your own script catch it, is the fastest way I know to understand why the rest of the setup is shaped the way it is.
