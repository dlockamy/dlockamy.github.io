---
layout: post
title: "Name your homelab after the solar system"
date: 2026-05-13
categories: [devops, homelab]
tags: [homelab, naming, infrastructure, self-hosted]
excerpt: "server1, service-prod-2, vps-us-east — these names tell you nothing useful when something breaks at midnight. Here's the naming convention I use and why a consistent hierarchy makes infrastructure easier to reason about."
author: Douglas Lockamy
ai_assisted: true
---

When something breaks at midnight, the last thing you want to be doing is decoding hostnames. `vps-us-east-3`, `server1`, `prod-web-02` — these names have structure, but it's the wrong kind. They encode deployment metadata (location, environment, sequence number) that changes over time and says nothing about what the machine actually does or how it relates to other machines.

I use a solar system naming convention for the Sol home network. Servers are named after planets. Virtual hosts and services are named after moons or asteroids. The network is called Sol. It's whimsical, but it's also genuinely useful — here's why.

## The hierarchy

```
Sol (network)
└── io.softsurve.com          (planet — physical server)
    ├── nexus.softsurve.com   (moon — Nexus artifact registry)
    ├── jenkins.softsurve.com (moon — Jenkins CI/CD)
    └── grafana.softsurve.com (moon — Grafana monitoring)
```

The naming tells you the relationship at a glance. If you see `nexus.softsurve.com`, you know immediately that it's a virtual host (moon), not a physical server, and it lives on `io`. If you see `io`, you know it's the primary host.

Future servers get planet names: `mars.softsurve.com`, `jupiter.softsurve.com`. Their services get moon names relative to that planet. The hierarchy is infinitely extensible without any naming conflicts.

## Why this beats descriptive names

The instinct is to encode function in the hostname: `nexus-server.home`, `jenkins-box`, `media-pi`. This feels helpful but creates problems:

**Services move.** When Nexus migrates from `io` to `mars`, a hostname like `nexus-on-io.softsurve.com` is wrong. A hostname like `nexus.softsurve.com` — where the subdomain is the service identity, not its location — is still correct. The DNS record changes; the name doesn't.

**Functions multiply.** `io` doesn't run just Nexus. It runs Jenkins, Grafana, and everything else in the Docker network. A name like `nexus-host` would be misleading the moment you add a second container.

**Descriptive names create implicit contracts.** If a server is called `database-server`, people assume it only runs databases. Rename it or add other services and you either have a misleading hostname or you rename it and update references everywhere.

## Why not use random names?

The counter-argument to themed naming is that random names (fruits, Greek gods, Tolkien characters) are even less misleading because they make no claims at all about function. This is a reasonable position, and a lot of large infrastructure uses it.

For a small network, I find that random names trade one problem for another. With the solar system scheme, the hierarchy is self-documenting. You can look at a list of hostnames and reconstruct the topology without a wiki:

```
io.softsurve.com
nexus.softsurve.com
jenkins.softsurve.com
grafana.softsurve.com
```

Versus a random scheme:

```
athena.softsurve.com
hermes.softsurve.com
zeus.softsurve.com
apollo.softsurve.com
```

The second list tells you nothing. You need a lookup table to know what anything does.

## The moon naming constraint

The constraint that virtual hosts are named after moons adds useful structure. It means:

- Moons are always subdomains, never bare hostnames
- A moon's parent planet is always discoverable by one level of DNS lookup
- You never accidentally give a service a planet name (implying physical hardware) or vice versa

In practice this means Terraform modules have a consistent pattern:

```hcl
# services/nexus/main.tf
# nexus is a moon — it lives on io
resource "docker_container" "nexus" {
  labels {
    label = "sol.service"
    value = "nexus"    # moon name
  }
  labels {
    label = "sol.host"
    value = "io"       # planet name
  }
}
```

And the nginx config is predictable:

```nginx
server {
  server_name nexus.softsurve.com;   # moon.network.tld
  proxy_pass http://127.0.0.1:8081;  # always on io
}
```

## Asteroids for experiments

The solar system gives you one more naming tier for free: asteroids. For experimental or temporary services that don't deserve a stable moon name:

- `ceres.softsurve.com` — staging instance, comes and goes
- `vesta.softsurve.com` — test deployment, probably gets deleted
- `juno.softsurve.com` — one-off tool, not permanent

This creates a useful signal in DNS records: if you see a planet or moon, it's stable infrastructure. If you see an asteroid, it might not be there tomorrow.

## DNS configuration

The full list of DNS records for the current Sol network:

```
io.softsurve.com              A     192.168.1.x   # primary host (planet)
nexus.softsurve.com           A     192.168.1.x   # artifact registry (moon)
docker.nexus.softsurve.com    A     192.168.1.x   # docker registry subdomain
dart.nexus.softsurve.com      A     192.168.1.x   # dart registry subdomain
jenkins.softsurve.com         A     192.168.1.x   # CI/CD (moon)
grafana.softsurve.com         A     192.168.1.x   # monitoring (moon)
```

Everything points to the same IP (io's LAN address) and nginx routes by hostname. The `*.softsurve.com` wildcard TLS cert covers all of them.

## On the whimsy

Naming things well is hard and naming things memorably is underrated. A name you can picture — `io`, the volcanic moon of Jupiter — sticks in a way that `prod-server-1` doesn't. When something goes wrong and you're communicating quickly ("io is down, nexus is unreachable"), the names carry meaning without explanation.

The Solar System has exactly the right number of planets for a homelab that might grow to five or six physical hosts. It has hundreds of named moons and thousands of named asteroids. The namespace will never run out.

The full network configuration is documented in [softsurve/sol](https://github.com/softsurve/sol).
