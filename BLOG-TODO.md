# Blog TODO — queued posts

Captured 2026-07-25. Deliberately **not drafted yet** — all three describe
infrastructure that's written but not applied (Sirius, the oauth2-proxy
gate, the Jenkins MCP plugin — see `softsurve/sol` and `softsurve/sirius`).
Writing the deep-dive before the debug-and-deploy session actually runs
risks describing a design that changes shape once it meets `terraform
apply` for real. Pick these up **after** that session, not before — the
build-log voice this site runs in is worthless if it's narrating something
that hasn't happened yet.

`_posts/2026-07-25-what-ive-been-building-july.md` covers all three at
summary depth already, so none of this is unpublished info — these are the
"now go deeper" follow-ups.

## 1. Sol → Sirius: what actually happened when the naming convention met a real split

**Angle:** sequel to `2026-05-13-solar-system-homelab-naming.md`. That post
proposed the convention; this one is "did it survive contact with a real
architecture decision."

**Known beats to hit once it's deployed:**
- Why Sol's own "invisible when healthy" principle is *why* Sirius couldn't
  live there — not a hosting detail, a design constraint.
- The repo-split mechanics: what moved to `sirius/infra` (VPC, ALB core,
  ACM, ECS cluster, shared IAM) vs. what stayed product-owned (target
  groups, task defs, task roles) — and *why* that boundary, since it also
  answers "what triggers a redeploy" without a cross-repo webhook.
- The near-miss: an early pass would have relocated a VPC that's already
  live, holding the real EC2 instance — a `terraform state` mistake caught
  before it shipped. This is the strongest single beat in the whole post;
  don't bury it.
- Once deployed: what actually differed from the plan. There's always
  something — record it honestly, that's the whole value of writing this
  after rather than before.

## 2. Zero-trust-lite for a home lab: oauth2-proxy + Google Workspace instead of waiting on a VPN

**Angle:** practical how-to, same lane as the JCasC/Secrets-Manager/Nexus
posts — name the tool, the exact config, the gotcha.

**Known beats to hit once it's deployed:**
- Why the answer wasn't "just finish Tailscale" — SOF-5 has been "planned"
  since May; this shipped in the time it would have taken to keep waiting.
- The nginx `auth_request` mechanism itself — worth an actual config
  snippet once it's live and verified working, not just described.
- The exclusion list is the real content: Nexus's package-manager clients
  (Cargo/Dart/Maven), the Docker registry vhosts, and Jenkins's
  `/github-webhook/` path all had to stay ungated because none of them can
  complete a browser OAuth redirect. Concrete "here's what breaks if you
  don't think about this" material — best served with the actual failure
  observed, if one happened during rollout.
- Whatever the real Google Cloud OAuth-client setup friction turns out to
  be (redirect URI, Workspace-internal consent screen) — write it from the
  actual experience, not the plan.

## 3. Turning Jenkins into an MCP server

**Angle:** timely (MCP is a live topic), concrete plugin walkthrough with a
twist.

**Known beats to hit once it's deployed:**
- The correction story is the hook: asked to "add it to JCasC," turned out
  the plugin has no JCasC schema at all — Java system properties only. Good
  "the obvious answer was wrong" opener.
- The identity question — which Jenkins user/token an MCP client
  authenticates as — was deliberately left open rather than defaulted to
  the break-glass service account. Report what was actually decided.
- The twist: building this in the same batch as post #2 above meant hitting
  the identical "machine client can't do a browser OAuth redirect" problem
  twice in one sitting, for `/mcp-server/` this time instead of
  `/github-webhook/`. Same fix, same shape — worth naming the pattern
  explicitly once both posts exist, maybe with a cross-link.
- Once actually used for a while: what's it *for*, concretely? What did
  querying Jenkins via an AI client actually unblock, if anything real
  happened with it.
