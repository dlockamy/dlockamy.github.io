---
layout: post
title: "Setting up FreeCAD, GIMP and Claude to design 3D models — and making the setup prove its own work"
date: 2026-10-02
categories: [hardware, tooling]
tags: [claude-code, freecad, gimp, mcp, 3d-printing, cad, python, macos, linux]
excerpt: "A walkthrough of the setup I use to design 3D-printable parts with Claude Code, headless FreeCAD and GIMP 3 — install steps for macOS and Linux, the two optional MCP bridges, and an example part whose script fails loudly when the geometry is wrong. The interesting part isn't getting Claude to drive CAD. It's that FreeCAD's command line will happily exit 0 on a failed build, and a part with a missing hole passes the standard topology checks. Everything is in a public repo, including the skills."
author: Douglas Lockamy
ai_assisted: true
---

I design small hardware — enclosures, panels, brackets, mounts — and for the
last few weeks most of that design work has been Claude writing CAD as code,
FreeCAD running it headless, and GIMP handling the images around it. This post
is the setup, written so you can reproduce it on your own machine: what to
install, how to wire it to Claude Code, and the part I'd have wanted someone to
tell me first.

That part is this. Getting Claude to drive FreeCAD is the easy half. The hard
half is getting the setup to tell you when it's wrong — because FreeCAD's
command line will exit `0` on a build that failed, and a 3D model with a hole
missing passes the standard topology checks. Most of what follows is about
closing those two gaps.

Everything here lives in a public repo:
[`dlockamy/claude-cad-workbench`](https://github.com/dlockamy/claude-cad-workbench)
— four skills, a CAD subagent, an installer, a read-only environment checker, and
the example part this post walks through. I'll flag at the end exactly what I
ran when, because a setup guide that doesn't say what was tested is just a
rumor.

This is the how-to companion to three earlier write-ups, which tell the stories
rather than the steps: [install night for the two bridges](/posts/2026/09/20/two-mcp-bridges-a-mesh-repair-that-ate-a-letterform-and-204-clipped-labels-i-havent-fixed/),
[the Dial's verification failures](/posts/2026/09/27/the-hole-that-removed-nothing-and-eighteen-screws-that-couldnt-reach/),
and [the quarter-scale print that beat four verification passes](/posts/2026/09/27/a-phantom-collision-a-real-one-and-a-quarter-scale-print-that-beat-four-verification-passes/).
I link to them rather than retell them.

---

## The shape of the system

Three tools, two ways of connecting them, and one of the two is optional.

| Layer | Tool | Runs headless? | When you need it |
|---|---|---|---|
| Driver | Claude Code | — | always |
| CAD | FreeCAD, via `freecadcmd` | **yes** | always — this is the main path |
| CAD (live window) | FreeCAD + `freecad-mcp` bridge | **no** | only to *see* the model or iterate with a window open |
| Images | GIMP 3.2 + `gimp-agent-mcp` bridge | **yes** | renders, concept sheets, labelled assets |

The default path involves **no bridge at all**. Claude writes a Python script;
`freecadcmd` runs it; the script exports STEP and STL and checks its own work.
That is reproducible, runs unattended, and works in CI. The bridges add a live
window on top — useful, but a different thing, and the FreeCAD one has a
constraint I'll get to that changes how much you can lean on it.

---

## Step 0: install the tools

**macOS (Homebrew).** The cask names exist; I checked them with `brew info`
before writing this:

```sh
brew install --cask freecad gimp
brew install uv
```

FreeCAD's command line ships *inside* the app bundle and isn't on your `PATH`:

```sh
/Applications/FreeCAD.app/Contents/Resources/bin/freecadcmd --version
```

**Linux.** Neither GIMP nor FreeCAD maintains an official apt repo or PPA — I
checked, rather than assumed. The upstream-blessed routes are Flatpak or
AppImage, and I used Flatpak:

```sh
flatpak install flathub org.gimp.GIMP org.freecad.FreeCAD
flatpak run --command=freecadcmd org.freecad.FreeCAD --version
```

Note the app ID: `org.freecadweb.FreeCAD` is the old, end-of-life one.

**Two version traps.**

- You need **GIMP 3.2.x**. GIMP 2.10 is unsupported by the bridge, and
  Python-Fu doesn't exist on current distros' 2.10 packages at all (no
  `gimp-python` package on Ubuntu 24.04). GIMP 3's Python API is also a genuine
  break — no `pdb` object, colours are `Gegl.Color` rather than tuples, fonts and
  gradients must be looked up by object. Don't carry 2.10 recipes across.
- **Flatpak sandboxes get their own private `/tmp`**, even with broad host
  filesystem permission. FreeCAD's Flatpak couldn't see the host's `/tmp`; use a
  path under `$HOME`. It's per-app, not universal — check each one.

---

## Step 1: prove the headless path before touching a bridge

Don't install anything else until this works:

```sh
freecadcmd -c "
import Part
b = Part.makeBox(10, 20, 30)
print('volume=%.1f solids=%d valid=%s' % (b.Volume, len(b.Solids), b.isValid()))"
```

```
volume=6000.0 solids=1 valid=True
```

`10 × 20 × 30 = 6000`. That's the whole habit in miniature: compare what the
tool says against a number you computed yourself. Hold on to it.

---

## Step 2: write the part as code that checks itself

Here's the claim the rest of the post defends: **a CAD script should be a test
that happens to emit a part.** Not the other way around.

The example is a deliberately boring mounting plate — 80 × 50 × 6 mm, four M3
clearance holes, a centre boss with a blind bore for a heat-set insert. I
wanted something small enough to read in one sitting and large enough to
contain the failure modes that have actually cost me prints.

Every dimension is a named constant at the top. Anything I'd have had to guess
carries a `PLACEHOLDER` comment, so an estimate can never pass for a measurement:

```python
PLATE_L, PLATE_W, PLATE_T = 80.0, 50.0, 6.0
HOLE_D = 3.4            # M3 clearance
HOLE_INSET = 8.0
BOSS_D, BOSS_H = 20.0, 4.0
BORE_D = 4.0            # PLACEHOLDER: check your insert's datasheet
BORE_DEPTH = 6.5
OVERLAP = 0.2           # boss sinks into the plate so the fuse is a real fuse

NOZZLE = 0.4
MIN_WALL = 3 * NOZZLE   # three perimeters
```

Three ideas carry the verification. None is clever; each exists because a real
part failed without it.

**1. Compute the expected answer by hand, not from the shape.** If you check a
shape's volume against a number derived from the same code that built it, you
have checked nothing.

```python
def expected_volume():
    v = PLATE_L * PLATE_W * PLATE_T
    v += math.pi * (BOSS_D / 2) ** 2 * BOSS_H
    v -= 4 * math.pi * (HOLE_D / 2) ** 2 * PLATE_T
    v -= math.pi * (BORE_D / 2) ** 2 * BORE_DEPTH
    return v
```

**2. Verify the file you wrote, not the object that wrote it.** The script
exports a STEP file, reads it back into a fresh shape, and runs the whole
battery again on that: one solid, `isValid()`, one shell per solid (more than
one means a sealed internal void — unprintable, and invisible to the other two
checks), bounding box equal to spec, fits the printer bed with margin, volume
matches the hand calculation.

**3. Assert the feature, not the operation.** "I cut a hole" and "there is a
hole" are different claims. The script measures the volume each boolean actually
removed and compares it with the cylinder it asked for, then probes the
*finished* part at each hole's centre to confirm it's open — so a later fuse
that fills a bore back in gets caught too.

Run it:

```sh
freecadcmd examples/mount-plate/mount_plate.py
```

```
mount plate
  ok    fuse produced one solid (got 1)
[built]
  ok    one solid (got 1)
  ok    shape is valid
  ok    solid 0: one shell, no enclosed void (got 1)
  ok    bounding box 80.000 x 50.000 x 10.000 == spec 80.000 x 50.000 x 10.000
  ok    fits the build volume with margin
  ok    volume 24957.05 mm3 vs hand-computed 24957.05 mm3 (0.0000% off)
[features]
  ok    hole 0 removed 54.48 mm3 (a real hole removes 54.48)
  ...
  ok    insert bore is still open on the finished part
[re-imported STEP]
  ok    volume 24957.05 mm3 vs hand-computed 24957.05 mm3 (0.0000% off)

ALL CHECKS PASSED
```

Good. Now the part that matters more than the passing run.

---

## Step 3: make it fail on purpose

A check you've never seen fail isn't a check. The script has a switch that
moves one mounting hole so its centre lands off the plate:

```sh
MOUNT_PLATE_BREAK=1 freecadcmd examples/mount-plate/mount_plate.py
```

Here's what comes back — and I'd like you to read the first block closely:

```
[built]
  ok    one solid (got 1)
  ok    shape is valid
  ok    solid 0: one shell, no enclosed void (got 1)
  ok    bounding box 80.000 x 50.000 x 10.000 == spec 80.000 x 50.000 x 10.000
  ok    fits the build volume with margin
  FAIL  volume 25011.53 mm3 vs hand-computed 24957.05 mm3 (0.2183% off)
[features]
  FAIL  hole 0 removed 0.00 mm3 (a real hole removes 54.48)
  FAIL  hole 0 keeps -9.70 mm of wall (min 1.20)
  FAIL  hole 0 centre is on the plate and open

5 CHECK(S) FAILED
```

The part has a missing hole and **every topology check is green**: one solid,
valid, one shell, the right bounding box, fits the bed. A boolean cut whose tool
sits entirely outside the part "succeeds" — it removes nothing and raises
nothing. The only things that catch it are the checks that look at *features*
and *volume*. This is a defect I've hit for real: a clearance hole whose
centre landed a millimetre outside a part removed 0.00 mm³ and left a tiny nick
in the corner instead of a hole, while solid count, validity and interference
all passed ([the full story](/posts/2026/09/27/the-hole-that-removed-nothing-and-eighteen-screws-that-couldnt-reach/)).

The exit code on that run is `1`. Which brings me to the thing that nearly made
all of this pointless.

---

## Step 4: `freecadcmd` will lie to you about success

I verified each of these on FreeCAD 1.0.2 on macOS while preparing this post,
because I wanted to quote behaviour I'd reproduced rather than half-remembered.

**An uncaught exception exits 0.** Run a script that does `assert False` and
FreeCAD prints `Exception while processing file: … [boom]` and returns success.
A syntax error does the same. Any CI step that trusts the exit code, or an
agent that reads "exit 0, ran fine", is trusting a number that cannot report
failure. Thirty seconds spent making your toolchain fail on purpose is cheap
insurance.

**A script that raises runs twice.** First with `__name__` set to the file's
stem, then again as `__main__`. I proved it by appending to a file from a script
that then raised: two lines. Side effects happen twice.

**`__name__` is the filename, not `"__main__"`.** The usual
`if __name__ == "__main__":` guard silently runs nothing — no error, exit 0,
zero files written. Call `main()` unconditionally.

**`sys.exit(n)` does propagate the exit code.** That's the escape hatch, and it's
why the example's `check()` helper never raises: it records failures and the
script calls `sys.exit(1)` at the end.

**…but `sys.exit` doesn't flush Python's stdout.** I found this one the hard
way, today. My first version of the example exited `1` correctly, and with
output redirected to a file the failure report was *empty*. A red build with no
explanation. The fix is `print(..., flush=True)` everywhere. If you take one
thing from this section, take that: it's invisible when you run the script in a
terminal and it only bites in CI.

One tidy-up: `freecadcmd` also leaves a `__pycache__/` next to the script it
runs. Add it to `.gitignore`.

---

## Step 5: look at the part — and check your checker

Verification by numbers has a blind spot: you can't tell a part looks wrong from
its volume. I want to *see* it, on a machine with no CAD GUI. The repo has a
~100-line renderer (`tools/render_stl_iso.py`, numpy + Pillow) that parses a
binary STL, shades it against a fixed light, and rasterizes with a real z-buffer.

![The mounting plate rendered from its STL: four clearance holes and a raised centre boss with an insert bore](/images/freecad-mount-plate-iso.png)

That image is correct, and the first one I rendered wasn't. The renderer I
started from — one I'd put together earlier for a different part — tipped the
model the wrong way about the X axis, so +Z pointed *down* the screen. The part was
upside down. The raised boss rendered as a recess; the plate's edge walls
showed on the far side. It looked plausible enough that I only caught it
because I knew what the boss should look like. An earlier preview from the
same renderer has the same defect and sat in my notes unnoticed — which is its
own lesson: **test your
checker against a part whose answer you already know.**

It's also the same lesson as the previous section from the other direction. One
view isn't verification, and neither is one tool. An isometric flatters detail
and hides profile; for a part defined by an angle or a taper, render the
orthographic view that feature lives in.

---

## Step 6: teach Claude the house rules

Claude Code loads *skills* — folders with a `SKILL.md` and a frontmatter
description — when the description matches the task. The repo has four, plus
a subagent:

| Skill / agent | What it carries |
|---|---|
| `parametric-cad-verify` | The headless workflow, the verification battery, the `freecadcmd` traps above, and the geometry gotchas. |
| `drive-desktop-app` | How to choose, audit, install and *prove* an MCP bridge. |
| `raster-compositing` | Layered, repeatable GIMP images — and what a raster editor can't do. |
| `multi-material-print-handoff` | Getting verified CAD into a multi-colour slicer project. |
| `mechanical-cad-engineer` (agent) | Implements a part spec and won't call it done until it has read the geometry back. |

Install them with:

```sh
git clone https://github.com/dlockamy/claude-cad-workbench && cd claude-cad-workbench
./install.sh        # symlinks skills + agent into ~/.claude
./tools/doctor.sh   # read-only: what's installed, what's missing
```

`install.sh` only ever replaces symlinks it created itself. I tightened that
while testing it: my first version would have silently replaced an existing
symlink pointing somewhere else — which on my own machine would have swapped out
a different, already-installed copy of the CAD agent. It now skips anything it
doesn't own and says so. `./install.sh --uninstall` removes exactly what it added.

Then you can just ask:

> Use the mechanical-cad-engineer agent to make a 60 × 40 × 5 mm bracket with two
> M4 clearance slots. It needs to fit a 220 mm bed.

The skills are plain markdown, which is the point — there's no magic in them.
What they carry is the list of things that already went wrong once, so Claude
doesn't have to rediscover each of them on your part. The long-term value of the
repo is that list getting longer.

---

## Step 7: GIMP (headless-capable)

GIMP is the easy bridge. [`gimp-agent-mcp`](https://github.com/SarutobiSasuke8/gimp-agent-mcp)
(Apache-2.0, 39 tools at 0.5.0) runs as stdio → a token-authenticated loopback
connection → a plug-in inside GIMP, and — unlike FreeCAD's — it has a real
headless mode. From its README:

```sh
uvx gimp-agent-mcp install-plugin
uvx gimp-agent-mcp install-skills --client claude
uvx gimp-agent-mcp doctor
```

(`install-skills` defaults to every agent client it finds; `--client claude`
keeps it to Claude Code.) **Start GIMP by hand once before `install-plugin`** —
the plug-in installer needs GIMP's profile directory to exist, and without it
says "Could not find a GIMP 3 config directory." Start it from Finder, not a
shell: on my Mac, a first launch via `open -a GIMP` and via `gimp-console` from
the command line both hung silently at 0% CPU. The app was freshly installed and
quarantined, so I suspect a macOS first-run approval I couldn't see from a
script, but I didn't confirm that. Launched by hand, GIMP opened without trouble,
and everything after that point worked as the README says. Restart GIMP after
the plug-in installs, then *Filters → Development → Start Agent Bridge* in the open
window (or have the agent call `gimp_launch(mode="headless")` and skip the
window entirely). Register it with Claude Code:

```sh
claude mcp add gimp -- uvx gimp-agent-mcp serve
```

I confirmed that `claude mcp add <name> -- <command> [args]` is the right shape
against the installed CLI's own help instead of trusting memory. And note the
bridge ships its *own* skills and recipes (sprite sheets, stickers, web export)
— install those too and don't rebuild them.

What GIMP is good for here: rendering concept images from CAD or SVG output,
layered scenes, labelled assets, anything that must be regenerated when its
source changes. What it isn't: photoreal. A raster editor draws; it doesn't
invent, and "remove the background" only works on a flat-colour field — on a
photograph it destroys the image while appearing to succeed. Say that to
yourself before you start, because the failure mode is a confident wrong answer.

Two habits that earned their place when I used it:

- **Make the agent look.** `gimp_render` returns the image; `gimp_measure` reads
  pixels and alpha bounds. Build one named layer per element (`sky`, `device`,
  `device-reflection`) so "make the sun smaller" is a ten-second change.
- **Bloom goes *behind* the thing that emits light.** Bloom on top washes out the
  detail it's meant to sell. It's the most common self-inflicted error in this
  kind of scene.

---

## Step 8: FreeCAD's live bridge — and the constraint that decides how you use it

[`neka-nat/freecad-mcp`](https://github.com/neka-nat/freecad-mcp) (MIT) gives
Claude a live FreeCAD window: create objects, screenshot the viewport, run
code. It's the most-used of the FreeCAD bridges — about 2,600 stars and a push on
September 24 when I checked — which is why I picked it over the alternatives. I'd still read its
source before installing anything that exists to execute code on your machine,
and so should you.

**The load-bearing fact: this bridge needs the GUI open.** The addon runs inside
FreeCAD and (in 0.1.24, the version I audited) imports the GUI at module scope,
so every tool dies when you close the window. A file in the repo called `test_headless.py` does not mean the server
is headless — it's a tool that shells out to `freecadcmd` for heavy jobs
(`execute_code_headless`, which is genuinely useful: a native OpenCascade crash
only kills the helper, not your GUI session). Plan accordingly: the live bridge
is for *looking*, never for unattended or CI work. That's exactly the gap the
headless path in Step 2 fills.

Install the addon into the directory **FreeCAD itself reports**, not one copied
from a table:

```sh
freecadcmd -c "import os; print(os.path.join(FreeCAD.getUserAppDataDir(), 'Mod'))"
```

I'm telling you to ask because the table lies. The bridge's docs list a
versioned directory for FreeCAD 1.0 on macOS; on my 1.0.2 install, FreeCAD
reported the plain unversioned `…/FreeCAD/Mod`. `tools/install-freecad-addon.sh`
does the asking for you, then clones the addon and copies it in (it never
writes anywhere but where FreeCAD said, and takes `--dest` for a dry run).

Then, once, by hand: restart FreeCAD, pick the **MCP Addon** workbench, and in
the FreeCAD MCP menu tick **Auto-Start Server** — otherwise someone has to click
*Start RPC Server* every launch, and a capability that needs a human click isn't
automatable. Point the bridge at the real `freecadcmd` so the headless tool
works, since the macOS one isn't on `PATH`:

```sh
claude mcp add freecad -- uvx freecad-mcp --freecadcmd /Applications/FreeCAD.app/Contents/Resources/bin/freecadcmd
```

Three things that differ from the GIMP bridge and will bite you if you assume
they don't:

- **Different return convention.** FreeCAD's `execute_code` returns what you
  `print()` and silently discards a variable named `result`; GIMP's does the
  opposite. Probe with a one-liner before a long script.
- **Pass object identity explicitly.** Neither bridge tracks "the focused
  document." Capture the id the create call returns and thread it through.
- **Security.** Both bridges expose an arbitrary-code endpoint
  (`execute_code`, `gimp_run_python`) that runs with your user's permissions.
  They bind to loopback, which is the right default. If you turn on FreeCAD's
  *Remote Connections*, set an auth token — unauthenticated, anything that can
  reach the port can run Python as you.

### Prove it over stdio before you restart the client

(This is the short version; the [install-night post](/posts/2026/09/20/two-mcp-bridges-a-mesh-repair-that-ate-a-letterform-and-204-clipped-labels-i-havent-fixed/)
has what each check caught.)

MCP config is read when the client starts, so you can't test a new bridge by
calling its tools. Drive the server directly first: send `initialize`, then
`notifications/initialized`, then `tools/list`, then a `tools/call`. It finds
every install problem while it's still cheap to fix, and `tools/list` tells you
the *real* tool names — they're namespaced (`gimp_new_image`, not `new_image`),
and guessing from the README is how you lose an hour.

The repo has a stdlib-only script for exactly this, `tools/mcp_probe.py`. Against
the GIMP bridge:

```sh
python3 tools/mcp_probe.py list -- uvx gimp-agent-mcp serve
```

```
server: gimp-agent-mcp
39 tools
  gimp_help
  gimp_status
  ...
```

39, matching the README. Because GIMP keeps running between calls, you can then
launch it headless, open a file and read a pixel back, one `call` at a time:

```sh
python3 tools/mcp_probe.py call gimp_launch '{"mode":"headless"}' -- uvx gimp-agent-mcp serve
python3 tools/mcp_probe.py call gimp_open '{"path":"docs/img/mount-plate-iso.png"}' -- uvx gimp-agent-mcp serve
python3 tools/mcp_probe.py call gimp_measure '{"kind":"color","image_id":1,"x":5,"y":5}' -- uvx gimp-agent-mcp serve
```

The image came back as 1400 × 1400, which is what the renderer writes, and the
pixel at (5, 5) read `[18, 18, 20, 255]` — the exact background colour the
renderer paints. That's the independent check: a value I knew in advance, read
back through the bridge, matching.

Then **verify by measuring, never by "the call succeeded."** Both bridges will
report success for a no-op. When I drove FreeCAD through the live session I built
a plate-plus-boss-minus-bore and read the volume back: 49175.7 mm³ from the
model, 49175.7 mm³ from arithmetic done by hand. That agreement is the evidence.
The tool saying "created" is not.

---

## What this setup can't tell you

I'd be overselling it if I stopped at the green checkmarks.

**It checks geometry. It doesn't check fit.** Every check above asks "is this
model correct." None asks "will this go together in PLA." Parts that meet at
exactly 0.000 mm in CAD won't mate in plastic; you need a real clearance budget
(0.4 mm is where I landed) and a check that fails below it. When I iterate fits I
print full-scale *section coupons* of the real mating features, not a scaled-down
model: scaling is uniform and manufacturing isn't — at quarter scale a 0.4 mm
clearance becomes 0.1 mm, below one extrusion width, and the parts fuse.

**It checks the holes you thought of.** In the largest build I've used this on,
the single most expensive defect was *18 of 25 fasteners specified with a screw
that couldn't work*. Four separate fastener checks existed and all of them
passed, because every one modelled the **hole**, and none modelled the **screw**
as an object with a length. A check suite is a statement about what you already
worried about — that [post](/posts/2026/09/27/the-hole-that-removed-nothing-and-eighteen-screws-that-couldnt-reach/)
has the whole account.

**Slicer orientation is a modelling decision.** A slicer treats one file as one
rigid body with one orientation. A flat panel with four feet, exported as a
single file, forced supports across the entire underside of the panel — "nearly
impossible to remove," in my own words after printing it. Anything that can't
share an orientation with the rest of the part has to be its own file.

**The first real print is still the real test.** (The [quarter-scale
print post](/posts/2026/09/27/a-phantom-collision-a-real-one-and-a-quarter-scale-print-that-beat-four-verification-passes/)
is about exactly that.) The larger project this approach came out of, the [Dial Panel](https://github.com/slash-builder/hw-2015-dial-panel)
(a wall-mounted smart-home panel, generated from one parametric script and
sliced plate by plate as a test), is labelled BETA in its own README for exactly
this reason: all nine plates have been printed at least once and six are waiting
on a reprint. A real print found a ledge the slicer never warned about.

---

## What I verified, and when

The setup here accumulated across a few sessions on different machines, so here
is what I actually ran, as opposed to what I'm relaying from the vendors' docs:

- **Today, on a Mac with FreeCAD 1.0.2:** the example part (good run and the
  deliberately-broken run), the four `freecadcmd` behaviours in Step 4, the
  renderer, `doctor.sh`, `install.sh` (into a scratch directory), and
  `install-freecad-addon.sh` (with `--dest`, so nothing touched my real
  FreeCAD). I also installed GIMP 3.2.6 and `uv` with the exact `brew` commands
  from Step 0 (both worked), then ran the GIMP bridge: `install-skills`,
  `install-plugin`, `doctor` (it found the config directory and the plug-in),
  the bridge's own `smoke` command (24 checks against a headless GIMP, all
  passed), and `tools/mcp_probe.py` over stdio — 39 tools listed, then a
  headless launch, an image opened, and a pixel read back to the expected value.
  **Not run today:** the *Filters → Development → Start Agent Bridge* menu path
  in a live GUI window (I drove the headless mode instead, and didn't restart
  the GUI GIMP that was already open), registering either bridge with `claude mcp add`, and the FreeCAD
  bridge at all.
- **2026-09-19, macOS, GIMP 3.2.6 + FreeCAD 1.1.3:** both bridges driven over
  stdio (`gimp-agent-mcp` 0.5.0, `freecad-mcp` 0.1.24), geometry read back and
  compared to hand-computed volume, headless and live-GUI paths agreeing.
- **2026-09-26, Ubuntu 24.04, Flatpak GIMP 3.2.6 + FreeCAD 1.1.3:** headless and
  GUI FreeCAD, GIMP batch, Bambu Studio opening the exported STL and
  independently reporting the same dimensions.
- **Not claimed:** Windows; GIMP 2.10; any slicer other than Bambu Studio; and
  `freecad-mcp` 0.1.25, which PyPI shows as current today and I haven't re-run.

If something here doesn't reproduce for you, that's more useful to me than a
star — open an issue on the repo.

---

## Try it

```sh
git clone https://github.com/dlockamy/claude-cad-workbench && cd claude-cad-workbench
./install.sh && ./tools/doctor.sh
freecadcmd examples/mount-plate/mount_plate.py                       # passes, exit 0
MOUNT_PLATE_BREAK=1 freecadcmd examples/mount-plate/mount_plate.py   # fails, exit 1
```

Run the second one first, honestly. Seeing a model with a missing hole sail
through every topology check, and then watching your own script catch it, is the
fastest way I know to understand why the rest of this setup is shaped the way it
is.
