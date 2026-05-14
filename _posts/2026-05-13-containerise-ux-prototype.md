---
layout: post
title: "Containerise your UX prototype so non-technical stakeholders can actually run it"
date: 2026-05-13
categories: [devops, design]
tags: [docker, ux, prototyping, stakeholder, nginx, design-handoff]
excerpt: "A Figma link is fine for static mocks. But when a product owner needs to feel the interaction flow, a live prototype running on their machine is worth ten screen recordings. Here's the one-command pattern I use."
author: Douglas Lockamy
ai_assisted: true
---

Design handoff has a friction problem. You build an interactive prototype. You want the product owner to click through it, feel the flow, and give you real feedback. So you send them a Figma link, or a screen recording, or a link to a deployed staging environment they need a VPN to access.

None of these are great. Figma links require an account and feel like design files, not products. Screen recordings kill interactivity. Staging environments have dependencies and don't work offline.

The alternative: a self-contained Docker container. One command, no dependencies beyond Docker Desktop, runs anywhere, works offline. Here's the pattern.

## The scenario

For a recent collaboration — a management suite for a specialised industrial domain — I built a three-screen interactive HTML prototype from Canva wireframes. Home dashboard, item view, new quote form. Real interactions: clickable navigation, radio button selection, form inputs.

The goal was to give the product owner something they could run locally, click through at their own pace, and use to make concrete decisions about layout, terminology, and workflow. Not a static mock. Not a hosted URL. Something they own on their machine.

## The prototype

The prototype is a single `index.html` — all CSS and JavaScript inline, no external dependencies except Google Fonts. Self-contained by design. It works by opening the file directly in a browser, but the container approach adds a few things:

- A consistent URL (`http://localhost:8080`) rather than a `file://` path
- No-cache headers so changes are picked up immediately when iterating
- A clean distribution artifact that works the same on any OS

## The Dockerfile

Dead simple:

```dockerfile
FROM nginx:alpine

RUN rm -rf /usr/share/nginx/html/*

COPY index.html /usr/share/nginx/html/index.html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
```

The nginx config is equally minimal:

```nginx
server {
    listen 80;
    server_name localhost;
    root /usr/share/nginx/html;
    index index.html;

    # No caching — pick up changes immediately when iterating
    add_header Cache-Control "no-store, no-cache, must-revalidate";
    add_header Pragma "no-cache";
    expires 0;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location = /favicon.ico {
        return 204;
        access_log off;
        log_not_found off;
    }
}
```

The `no-store` cache header matters during iteration. Without it, you update the prototype, rebuild the container, and the browser serves the cached old version. Annoying to debug the first time you hit it.

## docker-compose.yml

```yaml
services:
  prototype:
    build: .
    container_name: ux-prototype
    ports:
      - "8080:80"
    restart: unless-stopped
```

## Running it locally

```bash
git clone https://github.com/your-org/your-repo.git
cd your-repo/demo
docker compose up --build
# Open http://localhost:8080
```

Docker Desktop is the only prerequisite. No Node, no Ruby, no Python, no package managers. Clone-to-running time is under two minutes on a decent connection.

To stop it:

```bash
docker compose down
```

To iterate — edit `index.html`, then:

```bash
docker compose up --build
```

The `--build` flag forces a rebuild. Since `index.html` is `COPY`'d into the image (not volume-mounted), the build step is required for changes to be reflected. The build is fast — alpine base image, single file copy, no dependencies to install.

## For truly rapid iteration

If you're making changes every few minutes and the rebuild loop feels slow, volume-mount the file instead:

```bash
docker run -p 8080:80 \
  -v $(pwd)/index.html:/usr/share/nginx/html/index.html \
  nginx:alpine
```

Now changes to `index.html` are reflected on next browser refresh, no rebuild needed. The tradeoff is that this doesn't use your `nginx.conf` (including the no-cache headers), so you may need to hard-refresh.

## What goes in the prototype

I embedded UX annotation blocks directly in the HTML — amber-bordered callouts that explain design decisions and flag things for the product owner to review:

```html
<div class="flow-note">
  ↳ Each item links to the product's project management page —
    Smartsheet-style step view with assigned users.
    Confirm integration names with the product owner.
</div>
```

These serve the same purpose as comment pins in Figma but they travel with the prototype. Open it anywhere and the annotations are there. No separate document to cross-reference.

The annotations reference Jira ticket numbers directly, so when the product owner has a question or decision, there's a clear path back to the tracking system.

## The review checklist

The container alone isn't enough. Shipping a prototype to a product owner without a structured review guide is leaving feedback quality to chance. I include a review checklist in the repo alongside the prototype:

```markdown
## Screen 2 — Item view

[ ] Left panel navigation links — are these correct and complete?
    Current: Product information, CAD, Specifications, Ink & Tooling History,
             Shipping Information, Spec History
    Missing or wrong: _______________________________________________

[ ] The volume chart shows MSF (Thousand Square Feet) by month.
    Is MSF the right unit? _______________________________________________
```

The checklist is fillable — markdown checkboxes with blank lines for answers. The reviewer works through it while running the prototype, fills in their answers, and sends it back. The engineering team gets structured feedback they can act on directly.

## Why not just deploy it somewhere

The hosted approach has real advantages — shareable link, no setup, accessible from anywhere. But for an early-stage prototype with a single primary reviewer, local is better:

- **No auth to manage.** A hosted prototype needs access control, or you're publishing it publicly.
- **Works offline.** The reviewer can work through it anywhere, no network required.
- **Doesn't need a server.** You don't need a staging environment for a prototype that might be replaced in a week.
- **Feels local.** There's something about running software on your own machine that changes how you interact with it. The feedback tends to be more considered.

Once the prototype stabilises and needs broader review, add a deployment step to the Jenkinsfile and push to a staging URL. The container is already built.

## The broader pattern

The three-file structure (`index.html`, `Dockerfile`, `docker-compose.yml`) is reusable for any HTML prototype. Copy it into any project and update `index.html`. The engineering overhead is near zero.

For more complex prototypes with multiple pages, multiple assets, or JavaScript dependencies, the same pattern works — just `COPY` the full directory structure rather than a single file, and make sure the nginx config routes correctly.
