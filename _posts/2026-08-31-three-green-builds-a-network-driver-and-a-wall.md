---
layout: post
title: "Three green builds, a network driver that never got reached, and a wall I stopped at"
date: 2026-08-31
categories: [devops, benixos]
tags: [benixos, jenkins, yocto, kconfig, proxmox, qemu, rust, mingw-w64, ci-cd]
excerpt: "The weekly post is late because the week ended with three consecutive green Jenkins builds that each deploy to and boot a real VM on Proxmox — after four source-level bugs, a Kconfig merge that silently unset the network stack, and a Jenkins theory I was proudly wrong about. Then a cross-platform kernel-primitives crate that ran on real Windows through the QEMU guest agent. Then a wall I walked up to and stopped at."
author: Douglas Lockamy
ai_assisted: true
---

The weekly post is late, which is on me. The honest reason is that the
back half of the week turned into one focused push on BenixOS — a
side-project OS build, not a change in priority and not a platform I'm
launching — and the push didn't reach a resting place worth writing about
until the 30th. So this covers the 24th through the 30th, with most of the
story living in the last two days.

The headline is small and specific: as of the 29th and 30th, three
consecutive Jenkins builds — #26, #27, #28 on jenkins.softsurve.com —
went green, and "green" here means something I'd wanted to be able to say
for a while. Our CI pipeline deploys to and boots a real VM on Proxmox,
end to end, and the VM comes up with real DHCP networking. Not a build
artifact that *would* boot if you did the rest by hand. The pipeline does
the rest.

One thing I want to be precise about before anything else, because the
distinction matters: the thing that booted this week was a hypervisor
guest on Proxmox, not physical hardware. "Our CI boots a real VM" is the
claim. "BenixOS runs on real hardware" is not a claim I'm making here, and
if you read it into the above I'd rather correct it now than let it ride.
It's also a console/SSH-only image — there is no graphical stack in this
build, and nothing below should be read as implying one.

## Getting to three greens

Getting the first green was four bugs deep, and I'm glad I made myself
root-cause them at the source instead of papering over each one to get the
build unstuck. All four lived in `slash-builder/core`.

**One.** The Jenkins agent was missing its workspace path — the build had
nowhere to actually put the tree it was assembling. Unglamorous, fixed,
moving on.

**Two.** The GPT boot partition was typed `0700` instead of `EF00`. OVMF,
looking for an EFI System Partition, simply didn't find one and said
nothing useful about why — it just didn't boot. A one-hex-digit typo that
presents as a silent no-op is exactly the kind of bug this site exists to
write down. I need to be careful about how I describe the fix, though,
because it isn't really fixed: what's in place is a deploy-time
workaround. Every deploy re-types the partition with `sgdisk` so the image
that lands on Proxmox has the right `EF00`. The actual upstream generator
that produces this board's boot config still emits `0700`, and that's
still open. So — patched at deploy time; the real fix upstream is still
outstanding. Not the same thing as fixed.

**Three.** `SERIAL_CONSOLES` wasn't actually propagating into this board's
`grub.cfg`. The setting was there; the console wasn't. Fixed by going
through `APPEND` instead, which does land in the generated config.

**Four**, and this is the one worth the whole section. The image had
`CONFIG_VIRTIO_NET=y` set, which is the correct thing to want — it's the
virtio network driver, the thing that gives a Proxmox guest a NIC. No
network. I spent a while assuming the driver was present and misbehaving,
because the config plainly said it was on. It wasn't misbehaving. It was
never being reached. Reading the actual generated `.config` on the build
agent — not the fragment I'd written, the merged result Kconfig actually
produced — showed `CONFIG_NET_CORE` silently unset earlier in the merge
chain. With the network core gone, the driver underneath it is
unreachable code; you can set `VIRTIO_NET=y` all day and it compiles to
nothing that ever runs. Fixed the merge so the core stayed on, rebuilt,
and the next boot pulled a real DHCP lease. That lease is the whole
confirmation. Not "the config looks right now" — an actual address handed
out to an actual booted guest.

The general lesson I keep relearning: a Kconfig symbol set to `y` is a
statement of intent, not a guarantee it survived the merge. Read the
`.config` the build actually generated, not the one you think you wrote.

## The part where I was wrong out loud

Early in the session I built a whole theory. jenkins.softsurve.com was, I
became convinced, a split brain — two Jenkins instances, one of them
stale, and I was chasing behavior that came from whichever one I wasn't
looking at. It was a satisfying theory. It explained things. It was also
wrong, and I found out it was wrong within the same session because
someone corrected me and I actually checked instead of defending it. The
second hostname was legacy, left over, and completely unused. There was
one Jenkins the entire time. I'd invented a distributed-systems problem to
explain what was just my own stale mental model, and the fastest way out
was to drop the theory the moment the evidence didn't back it. Writing it
down here because the retraction is the useful part, not the theory.

Also in this stretch, and quickly because it's plumbing: Jupiter — the
Proxmox hypervisor — got JumpCloud-enrolled mid-session, and a scoped,
permanent `jbot` sudoers grant replaced a one-hour temporary root grant
I'd been leaning on. That closed out SOF-27, an access ticket that had
been open longer than I'd like. Scoped and permanent beats broad and
temporary; the temp-root habit is the kind of thing that quietly becomes
permanent by accident.

## benix-base, and a binary that ran on Windows through the guest agent

The next day I kept going, into something more fun and honestly more
satisfying: `benix-base` / `libbenix`, a small cross-platform
kernel-primitives crate. The primitives are Thread, Area, Port, and
Semaphore — the lineage here is the BeOS Kernel Kit, which is where the
naming and the shape come from. The plan was to build a C reference
implementation first, get the ABI right, then port it.

The C reference built, and then it did the thing I actually wanted to see:
cross-compiled to native Windows via mingw-w64, pushed through Proxmox's
QEMU guest agent onto a Windows 10 VM, and *executed there* — exit code 0,
all primitives behaving correctly. There's something very concrete about
watching a binary you cross-compiled on one OS run correctly on another
one it was shipped into over a hypervisor's guest channel. No RDP, no file
share; the guest agent carried the binary in and ran it.

Then the Rust port. The goal was zero FFI overhead while exporting the
identical 17-symbol C ABI — same symbols, same contract, so anything
linking against the C version links against the Rust version unchanged. I
verified the exported symbol set with `nm` and `objdump` on macOS and
confirmed it again through a real Windows cross-compile, because "the ABI
matches" is a claim you check with the tools, not one you assert.

The port earned its keep by catching bugs the C version couldn't. Three of
them, all real, all before anything shipped:

- A C-ABI parity break in `benix_free` — the Rust side disagreed with the
  C side about the contract, and the symbol comparison surfaced it.
- A `windows-sys` feature-gating gotcha, where the feature I needed wasn't
  pulled in the way I assumed and the build told me so.
- A non-`Send` closure that the Rust compiler rejected at compile time —
  a threading mistake that C's equivalent has no way to catch at all. In C
  it would have compiled cleanly and gone wrong at runtime, on someone
  else's schedule.

That last one is the argument for the port in a single bug: the same
mistake is a silent runtime hazard in C and a compile error in Rust.

## The wall

Same night, I tried to prototype first-boot device claiming — the
beginning of a Quickring pairing flow, where a freshly booted image would
come up and surface enough for a device to be claimed. It doesn't work.
Not "in progress," not "almost there" — it doesn't work yet.

Here's exactly where it stands, because a vague version of this would be
worse than useless. DHCP succeeds cleanly on every boot; the networking
half is solid. But `/etc/issue` never updates with the IP and claim
information the way it's supposed to. I made two independent attempts at
fixing it and neither took. At that point I was genuinely stuck without
deeper disk and login access to the running image than I had in the
session, and I made the call to stop rather than keep guessing at it.
Stopping when the next move is a guess is a skill I'm still learning to
value; the alternative is an hour of confidently wrong changes and no more
knowledge than I started with. So: the pairing prototype is a wall I
walked up to and stopped at. It'll be there next time with better access.

## The rest of the week, briefly

The first half of the week — the 24th through the 28th — was the Kit
Extraction Push: pulling shared primitives out into their own kits so the
build stops copy-pasting the same foundations, which is a lot of the
reason `benix-base` even existed to work on by the 30th. Necessary,
un-dramatic, and mostly the setup for the part above. (There was also some
internal repo-org and ticket bookkeeping in the background; none of it is
reader-facing and I'll spare you.)

---

So the week's ledger, honestly kept: three green builds that deploy to and
boot a real Proxmox VM with working DHCP; four source-level bugs
root-caused instead of worked around, with the boot-partition one honestly
labeled as a deploy-time patch over a still-open upstream bug; a
kernel-primitives crate that runs correctly as C on Windows and as
zero-overhead Rust with a matching 17-symbol ABI; a Jenkins theory I
retracted the moment it stopped holding up; and one prototype that plainly
doesn't work yet, stopped on purpose. That last item isn't a blemish on
the list — it's the point of keeping the list this way.
