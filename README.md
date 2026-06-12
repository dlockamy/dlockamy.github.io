# dlockamy.github.io

> Douglas Lockamy's personal portfolio (dlockamy.com) — Jekyll, 'Mission Console' theme.

<!-- LS-UNIFORM:START -->

## Subprojects

| Path | What it is |
|------|-----------|
| `_layouts/, _includes/, _sass/` | Jekyll theme. |
| `_posts/` | Blog posts. |
| `_data/` | Site data. |
| `assets/, css/, js/, images/` | Static assets. |
| `about.md, blog.md, connect.md, projects.md` | Content pages. |

## Build & CI

- **Stack:** Jekyll (Ruby) static site; Docker
- **CI:** Jenkins (`Jenkinsfile`) at `jenkins.softsurve.com`; artifacts publish to Nexus (`nexus.softsurve.com`).
- **Container:** `Dockerfile`.
- **Tasks:** `Makefile`.
- **Site:** Jekyll (`_config.yml`); GitHub Pages.
- **Secrets:** AWS Secrets Manager, prefix `sol/` (never committed).

## Links

- Reference: [`CONTEXT.md`](./CONTEXT.md)
- Workspace index: [`../../WORKSPACE.md`](../../WORKSPACE.md)
- **Business unit:** Studio overhead

## License

Apache-2.0 (source) per studio policy. Specs CC-BY-4.0 or Apache. Brand/trademarks reserved.

---
*Part of the Lockamy Studios workspace — uniform README pattern. See [`WORKSPACE.md`](../../WORKSPACE.md).*

<!-- LS-UNIFORM:END -->

<!-- LS-PLANS:START -->

## Plans & Design

> This section makes the repo **self-contained**: a developer can clone it and have the studio context, the design decisions, and the cross-cutting plans that govern this work — without needing the rest of the workspace. Repo-specific design files (below) ship in the clone; studio-wide strategy and the relevant decision records are mirrored inline.

### Repo design files (in this clone)

- [`CONTEXT.md`](./CONTEXT.md) — repo reference/context

<details>
<summary><strong>Studio context</strong> — open for the studio-wide essentials every repo shares</summary>

### Studio essentials (mirrored from `WORKSPACE.md`)

**Owner:** Douglas Lockamy (DJ), Lockamy Studios, Cary NC. Jira: `fairmerce.atlassian.net` (cloudId `f3b17209-1a42-468b-bb7a-73087ac5e6b8`).

**Founding principle — open source first.** Income comes from *executing* ideas (built + hosted software; manufactured + supported hardware), not from owning IP. Source is Apache-2.0; specs CC-BY-4.0 or Apache; contributions under DCO/CLA. Carve-outs that stay closed: brand & trademarks (`bitchain`, `Quickring`, `Current`, `Courier`, `Lockamy Studios`), customer data & telemetry, abuse/fraud/security signals, and embargoed security fixes.

**Brand architecture.** Two registers, one studio. **Lockamy Studios** is the open heart (OSS identity, community register, maker hardware, developer tools `clusterzer0`, agent OS, spec-first products). **Thunderhead Systems** is the premium finished-product brand, held until the Production hardware tier is real.

**Business units.** Foundations (Sol, Digital Zen) · Personal Computing (DeviceNix, BenixOS, Thunderhead, Quickring, the kits) · Developer Tools (bitchain, Refraction, slashbuilder — org `clusterzer0`) · Games (Pogo Pops, i95north — dormant). Ventures: Spec-Up (Miette Lewis, `SPEC`), Nodeul (Neptune Valentin, `NOD`).

**Language convention (locked 2026-05-30).** Rust everywhere except the Flutter/Dart UI facade. Dart reaches Rust via `flutter_rust_bridge`; native bindings via `uniffi`; C ABI via `cbindgen`. Every Flutter app builds on Design Kit. Refraction pivoted Go/Gin → Rust/axum on 2026-05-30.

**Kit model (BeOS-style, locked 2026-05-30).** Kits are reusable libraries with stable APIs (Rust crates / Dart packages); Products compose Kits. New kits use the `-kit` suffix; legacy `devicenix`/`benixos` single-token kit names remain. All GitHub repo names are lowercase.

**Shared infrastructure.** CI: Jenkins (`jenkins.softsurve.com`) — every repo has a Jenkinsfile. Artifacts: Nexus (`nexus.softsurve.com`) — Cargo, Docker, RubyGems, APT, Dart. Secrets: AWS Secrets Manager, prefix `sol/` (never committed). Jenkins credential IDs: `nexus-credentials`, `github-token`, `io-ssh-key`, `aws-sol-deploy`. Sol network naming: network = Sol; servers = planets (io, mars, jupiter); virtual hosts = moons/asteroids (nexus, jenkins, grafana).

**Design system.** Digital Zen — stone neutrals, sage green, golden tab motif; Fraunces (display) + DM Sans (body) + IBM Plex Mono (data). Applies to all user-facing surfaces.

**Hardware platforms.** Aether family (Pi 5 / CM5) carries Cumulus / Wisp / Halcyon. Forge family (micro-ATX 244×244mm) carries Anvil / Squall (and eventual Stratus). Four-tier hardware ladder: Maker → Kit → Assembled → Production.

</details>

---
*Plans & Design pack — generated for repo self-containment. Canonical sources: [`WORKSPACE.md`](../../WORKSPACE.md) and `softsurve/sol/weekly/`.*

<!-- LS-PLANS:END -->
