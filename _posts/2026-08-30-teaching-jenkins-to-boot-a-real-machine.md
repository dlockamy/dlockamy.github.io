---
layout: post
title: "Teaching Jenkins to boot a real machine"
date: 2026-08-30
categories: [devops, benixos]
tags: [benixos, jenkins, yocto, proxmox, kvm, kconfig, wic, ci-cd, sudoers]
excerpt: "For a while my BenixOS pipeline could build an image and hand it to a local QEMU smoke boot. What I wanted was Jenkins deploying to a real Proxmox VM that comes all the way up on its own — no doing the last mile by hand. Getting there was four source-level bugs, a Jenkins theory I retracted out loud, a pile of deploy-plumbing gotchas that had nothing to do with the OS, and one prototype I walked up to and stopped at."
author: Douglas Lockamy
ai_assisted: true
---

For a while now the BenixOS pipeline could do most of a thing. Jenkins
would build the image, and a local QEMU smoke boot would tell me the image
was plausibly bootable. What it could not do was the part I actually cared
about: take that image, put it on a real virtualized machine, and have that
machine come all the way up on its own — no human doing the last mile by
hand. A QEMU smoke boot in the build agent is a useful signal, but it's the
build environment marking its own homework. I wanted the pipeline to deploy
to a managed KVM guest on the hypervisor and prove it booted there, with
real networking on the real LAN.

The night of the 29th into the 30th, it did. Three consecutive green
builds — `BenixOS-Thunderhead-AMD64` #26, #27, and #28 on
`jenkins.softsurve.com` (Jenkins 2.555.1) — each build the image, deploy it
to VM 260 (`benixos-ci-test-1`) on Jupiter, and boot it end to end.

One precision note before anything else, because I'd rather correct it now
than let a reader inflate it: the thing that boots is a Proxmox KVM guest,
not physical hardware. "Real virtualized hardware, not the QEMU dev loop" is
the claim — a managed VM with virtio devices, a real DHCP lease on the LAN,
provisioned by CI. "BenixOS runs on bare metal" is not a claim I'm making,
and this is a console/SSH-only image with no graphical stack. Everything
below lives inside those lines.

## The theory I was proud of and wrong about

Early in the session I built a beautiful theory. I'd convinced myself that
`jenkins.softsurve.com` was a split brain — two Jenkins instances quietly
disagreeing, one of them a stale `europa` box that `build.softsurve.com` was
proxying to, and I was chasing behavior that came from whichever instance I
wasn't looking at. It was a genuinely satisfying explanation. It accounted
for the inconsistencies. It was also wrong.

`build.softsurve.com` is legacy and unused. `jenkins.softsurve.com` is the
one real instance, and it always was. I found this out inside the same
session, because someone corrected me and I checked instead of defending the
theory. What I'd actually done was invent a distributed-systems problem to
explain a stale mental model of my own, which is a much more flattering bug
to have than the one I really had. I'm writing it down because the retraction
is the useful part. When the evidence stops backing a theory, the fastest
path forward is to drop the theory, not to reinforce it.

## Four bugs, root-caused against the artifacts

Getting the first green was four bugs deep. I made myself root-cause every
one against the actual generated artifact rather than guess and re-run, and
that discipline is the only reason the fixes were real fixes.

**One — the agent workspace that wasn't there.** The `europa` agent carried
the `yocto` label, so Jenkins happily scheduled the build onto it, but the
workspace path the job expected — `/data/delta/jenkins/...` — didn't exist on
that node. The build had the right label and nowhere to write, so it died
with an `AccessDeniedException`. Unglamorous, and a good reminder that a
matching label is a claim about a node's role, not proof the node is actually
set up for the work.

**Two — a one-hex-digit partition type that UEFI refused to see.** The GPT
boot partition was being typed `0700` instead of `EF00`. `EF00` is the EFI
System Partition type GUID; `0700` is basic-data. UEFI firmware looking for
an ESP simply never found one and said nothing useful about it — no error,
just no boot. This is a genuine Yocto `wic` bug: the `wic.ks` for this board
emits the wrong type. I need to be careful about how I describe the fix,
because it is not fixed. What's in place is a **deploy-time workaround** —
the deploy step re-types the partition with `sgdisk -t 1:ef00` after the
image is written, so what lands on the VM has a real ESP. The upstream
`wic.ks` change is still open. So: patched where I deploy, not fixed where
it's generated. Those are different sentences and I'm not going to collapse
them.

**Three — a serial console that never made it into `grub.cfg`.** My first
attempt leaned on `SERIAL_CONSOLES`, on the assumption that it's the standard
OE variable for this and would propagate. It didn't — not into this BSP's
generated `grub.cfg`, anyway. The setting was set and the console still
wasn't there. What actually worked was `APPEND += "console=ttyS0,115200"`,
which does land in the generated config. The assumption that a "standard"
variable is honored by a given BSP is exactly the kind of thing that reads as
obviously true right up until you diff the generated file.

**Four — the network driver that was never reached.** The image had
`CONFIG_VIRTIO_NET=y`, which is the correct thing to want; it's the driver
that gives a Proxmox guest its NIC. And there was no network. I spent a while
assuming the driver was present and misbehaving, because the config plainly
said it was on. It wasn't misbehaving — it was never being compiled in.
Reading the *merged* `.config` the build actually produced, not the fragment
I'd written, showed `CONFIG_NET_CORE` silently unset earlier in the Kconfig
merge chain. With the network core gone, the driver above it is unreachable;
you can set `VIRTIO_NET=y` all day and it compiles to nothing that runs. This
is the same failure class as a `CONFIG_ATA_SFF` gotcha already documented in
this same `.cfg` — a dependency getting dropped upstream in the merge and
quietly taking its dependents down with it. Fixed the merge so the core
stayed on, rebuilt, and the very next boot pulled a real DHCP lease:
`192.168.50.103`. That lease is the confirmation. Not "the config looks right
now" — an actual address handed to an actual booted guest.

The lesson I keep relearning: a Kconfig symbol set to `y` is a statement of
intent, not a guarantee it survived the merge. Read the `.config` the build
generated, not the one you think you wrote.

The trail for all of this, in order, on `slash-builder/core` main:
`372b560` → `8339360` → `4ae5d6b` → `666c4d4` → `f350002`.

## The plumbing that had nothing to do with the OS

Once the image was correct, most of the remaining fight was the deploy path
itself — the machinery that gets an image onto VM 260 and reads its console
back out. None of it is about BenixOS and all of it was load-bearing.

**The macOS "network" problem that was a code-signing gate.** Early on, the
control-side tooling running from my Mac would fail to open a raw socket in a
way that looked exactly like a network fault. It wasn't. Apple's system
`/usr/bin/python3` is code-signed and entitled in ways a Homebrew Python
isn't, and the raw-socket operation the deploy needed was being gated by that
signing/entitlement difference — not by anything on the wire. Once I stopped
reading it as a connectivity issue and started reading it as a permissions
gate on the interpreter, it was obvious. Chasing it as a network problem
first cost me real time; the tell was that nothing else on the box had any
trouble reaching anything.

**Proxmox's dynamic `termproxy` port.** To capture the guest console over the
API you open a `termproxy` session, and the port it hands you is dynamic —
you get a fresh one each time, along with a single-use ticket. You cannot
hardcode it, cache it, or assume the last one still works. Every capture has
to ask for the port and the ticket, then connect immediately.

**Console-capture ordering.** Getting a clean boot log off the VM turned out
to be sequence-sensitive in a way I had to nail down by trial: `stop` → sleep
→ `start` → sleep → request a *fresh* ticket → open the websocket. Skip a
sleep and you attach to a console that isn't ready and miss the early boot
output — which is precisely the output that tells you whether the ESP was
found and whether the kernel came up. The whole point of the capture is the
first few seconds, so racing them defeats it.

**The sudoers whitelist matches literal absolute paths, only.** This bit me
until I internalized it: a `sudoers` command specification matches on the
exact literal command string, absolute path included. A relative path, a
different-but-equivalent invocation, or a slightly different argument shape
does not match the rule and gets denied. That's the correct, conservative
behavior — it's just unforgiving, and it means the grant and the deploy
script have to agree character-for-character on how each command is spelled.

## Standing up the infrastructure to do this safely

Two pieces of real infra got stood up so this could run as something other
than a root free-for-all.

Jupiter — the Proxmox hypervisor — got JumpCloud-enrolled mid-session, so
its access is managed like everything else now instead of being a snowflake.

And the deploy identity got a proper, narrow grant. I'd been leaning on a
one-hour temporary root grant to get the pipeline moving, which is exactly
the kind of "temporary" that quietly becomes permanent if you let it. I
replaced it with a scoped, permanent grant at
`/etc/sudoers.d/jbot-benixos-deploy`, limited to the specific `qm`
subcommands the deploy actually issues plus the exact loop-device, partition,
and mount commands it needs — and nothing else. Scoped-and-permanent beats
broad-and-temporary every time. That closed out SOF-27, an access ticket
that had been open longer than I'd have liked.

One more cleanup worth recording, because it's the kind of thing that
otherwise rots into a standing over-grant: at one point I'd widened the
Proxmox API token's ACL to allow disk writes, on the theory the deploy might
drive image placement through the API. In the end the real mechanism turned
out to be SSH plus the scoped `sudo`, not the API token, so I deliberately
reverted the token's ACL back to minimal. If a permission isn't the thing
actually doing the work, it shouldn't keep the grant just in case.

## The wall

Same night, I tried to prototype first-boot device claiming — the front edge
of a Quickring pairing flow, where a freshly booted image would come up and
surface enough of an identity and address for a device to be claimed, with
the IP and claim banner landing in `/etc/issue` so it's visible on the
console. It does not work. Not "in progress," not "nearly there" — it does
not work yet.

Here is exactly where it stands, because a vague version of this is worse
than useless. DHCP succeeds cleanly on every boot; the networking half is
solid, and that's the `192.168.50.103` lease from above. But `/etc/issue`
never updates with the IP and claim information the way it's supposed to. I
made two independent attempts at it and neither took. At that point the
correct next move was clearly a real design pass — this touches identity and
device trust, which means it wants `security-engineer` eyes and a
conversation with `gateway-pm` and `quickring-pm` about what the claim flow
should even be — not a third late-night guess from me. So I parked it. I want
to be clear that parking it was the right call and not a failure I'm dressing
up: the alternative was another hour of confidently wrong changes and no more
knowledge than I started the hour with. Stopping when the next move is a
guess is a skill I'm still learning to actually value.

---

The honest ledger for the night: three green builds that build, deploy to,
and boot a real Proxmox VM with working DHCP; four source-level bugs
root-caused against the actual artifacts instead of papered over, with the
boot-partition one labeled truthfully as a deploy-time workaround over a
still-open upstream `wic` bug; a Jenkins split-brain theory retracted the
moment it stopped holding up; a deploy path hardened down to a narrow,
permanent sudoers grant with the leftover API ACL reverted; and one pairing
prototype that plainly doesn't work yet, stopped on purpose and handed to a
design pass. That last line isn't a blemish on the list — keeping it on the
list the honest way is the whole reason I keep the list.
