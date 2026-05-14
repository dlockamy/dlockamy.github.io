---
layout: post
title: "Self-hosted artifact registries in 2026: Nexus 3 with Cargo, Dart, Docker, RubyGems, and APT"
date: 2026-05-13
categories: [devops, infrastructure]
tags: [nexus, self-hosted, cargo, rust, dart, flutter, docker, rubygems, apt, terraform]
excerpt: "Five package formats, one Nexus instance, REST API provisioning via Terraform. The Dart/pub piece is barely documented anywhere — here's how it actually works."
author: Douglas Lockamy
ai_assisted: true
---

Running a private artifact registry is one of those infrastructure decisions that pays for itself quickly once you have more than a couple of projects. Build times drop because dependencies resolve locally. You get a pull-through cache for public registries. And you have a place to publish your own packages without going through npmjs, crates.io, or pub.dev.

For the Sol network — a self-hosted home lab running Lockamy Studios projects — I needed a single registry that could handle five different package formats: Docker images, Rust crates (Cargo), Ruby gems (Jekyll themes), Debian packages (APT), and Dart packages (pub.dev). Nexus 3 handles all of them, but the documentation for some formats — especially Dart — is thin. Here's what actually works.

## The setup

Nexus 3 runs as a Docker container deployed via Terraform. The full deployment is in the [softsurve/sol](https://github.com/softsurve/sol) repo, but the container configuration is straightforward:

```hcl
resource "docker_container" "nexus" {
  name    = "nexus"
  image   = "sonatype/nexus3:3.68.0"
  restart = "unless-stopped"

  env = [
    "INSTALL4J_ADD_VM_PARAMS=-Xms1200m -Xmx1200m -XX:MaxDirectMemorySize=2g ...",
    "NEXUS_SECURITY_RANDOMPASSWORD=false"
  ]

  ports {
    internal = 8081
    external = 8081   # Web UI
  }
  ports {
    internal = 5000
    external = 5000   # Docker registry
  }
  ports {
    internal = 5001
    external = 5001   # Dart/pub registry
  }
}
```

One thing worth noting: `vm.max_map_count=262144` is required on the host for Nexus to run without warnings. Set it in `/etc/sysctl.conf` or it'll bite you after a reboot.

## Repository provisioning via REST API

Nexus 3 has no official Terraform provider for repository management. The cleanest approach is a `null_resource` with a `remote-exec` provisioner that calls the Nexus REST API after the container is healthy.

The provisioner polls the health endpoint first:

```bash
for i in $(seq 1 40); do
  STATUS=$(curl -s -o /dev/null -w '%{http_code}' \
    http://localhost:8081/service/rest/v1/status)
  [ "$STATUS" = "200" ] && break
  sleep 15
done
```

Then creates repositories. The pattern for each format is the same — hosted (your packages), proxy (cache of the public registry), group (unified endpoint combining both):

```bash
nexus_api() {
  METHOD=$1; ENDPOINT=$2; BODY=$3
  HTTP=$(curl -s -o /tmp/resp.txt -w '%{http_code}' \
    -u "$NEXUS_USER:$NEXUS_PASS" \
    -X "$METHOD" -H 'Content-Type: application/json' \
    "http://localhost:8081/service/rest$ENDPOINT" \
    ${BODY:+-d "$BODY"})
  # 400 = already exists — treat as no-op for idempotency
  [ "$HTTP" = "201" ] || [ "$HTTP" = "200" ] || [ "$HTTP" = "400" ] || exit 1
}
```

## Docker

Docker needs two separate nginx endpoints — one for the web UI and one for the registry connector. Nexus exposes the Docker registry on a separate port (5000), and Docker clients need to talk to that directly.

```bash
nexus_api POST /v1/repositories/docker/hosted '{
  "name": "docker-hosted",
  "docker": { "v1Enabled": false, "forceBasicAuth": true, "httpPort": 5000 }
}'
```

In nginx, the Docker registry endpoint needs `proxy_buffering off` and `client_max_body_size 0` — image layers can be large and chunked transfer will break without these.

## Cargo (Rust)

Nexus has native Cargo support. Configure cargo to use the group endpoint in `.cargo/config.toml`:

```toml
[registries.lockamy]
index = "https://nexus.example.com/repository/cargo-hosted/"

[source.crates-io]
replace-with = "lockamy-group"

[source.lockamy-group]
registry = "https://nexus.example.com/repository/cargo-group/"
```

In the Jenkinsfile, credentials are written at build time:

```bash
mkdir -p ~/.cargo
cat >> ~/.cargo/config.toml <<EOF
[registries.lockamy]
index = "${NEXUS_URL}/repository/cargo-hosted/"
EOF
printf '[registries.lockamy]\ntoken = "%s:%s"\n' \
  "${NEXUS_USER}" "${NEXUS_PASS}" >> ~/.cargo/credentials.toml
chmod 0600 ~/.cargo/credentials.toml
cargo publish --registry lockamy
```

## RubyGems

Straightforward. Push to the hosted repo, pull from the group:

```bash
gem push mypackage-1.0.0.gem \
  --host https://nexus.example.com/repository/rubygems-hosted/ \
  --key admin:PASSWORD
```

In a Gemfile:

```ruby
source "https://nexus.example.com/repository/rubygems-group/"
```

## APT (Debian/Ubuntu packages)

The APT proxy is the most useful part for a homelab — it caches Ubuntu packages locally so you're not pulling from the upstream archive on every server provision.

One gotcha: the `distribution` field in the repository config (`jammy`, `focal`, etc.) has to match what your APT clients expect. Get it wrong and `apt-get update` will fail with a confusing error about missing `Release` files.

## Dart/pub — the underdocumented one

Nexus added native Dart/pub support in version 3.65. Before that, people were hacking around it with raw/generic repositories. As of 3.68, it works properly.

The Dart registry needs its own port connector, separate from the web UI. That means an additional port mapping on the container (5001 in this setup) and a separate nginx server block:

```nginx
server {
  listen 443 ssl;
  server_name dart.nexus.example.com;

  location / {
    proxy_pass http://127.0.0.1:5001;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-Proto $scheme;
  }
}
```

The repository creation:

```bash
nexus_api POST /v1/repositories/dart/hosted '{
  "name": "dart-hosted",
  "storage": { "blobStoreName": "default", "writePolicy": "allow" },
  "dart": {}
}'

nexus_api POST /v1/repositories/dart/proxy '{
  "name": "dart-pubdev-proxy",
  "proxy": { "remoteUrl": "https://pub.dev", "contentMaxAge": 1440 },
  "dart": {}
}'

nexus_api POST /v1/repositories/dart/group '{
  "name": "dart-group",
  "group": { "memberNames": ["dart-hosted", "dart-pubdev-proxy"] },
  "dart": {}
}'
```

To use it, set `PUB_HOSTED_URL` before any `flutter` or `dart pub` command:

```bash
export PUB_HOSTED_URL=https://dart.nexus.example.com/repository/dart-group/
flutter pub get
```

For publishing a package, point `publish_to` in `pubspec.yaml`:

```yaml
publish_to: https://dart.nexus.example.com/repository/dart-hosted/
```

## Nginx configuration

Each format gets its own server block. The critical settings that vary by format:

| Format | `client_max_body_size` | `proxy_buffering` | Notes |
|--------|----------------------|------------------|-------|
| Docker | `0` (unlimited) | `off` | Chunked transfer for image layers |
| Cargo | `0` | default | Crate files can be large |
| RubyGems | `0` | default | Gem files vary |
| APT | `0` | default | Package files can be large |
| Dart | `0` | default | Standard |

## Jenkins credential pattern

Every Jenkinsfile uses the same credential ID:

```groovy
withCredentials([usernamePassword(
  credentialsId: 'nexus-credentials',
  usernameVariable: 'NEXUS_USER',
  passwordVariable: 'NEXUS_PASS'
)]) {
  // push artifacts
}
```

One credential ID, consistent across every pipeline. When you rotate the Nexus admin password, you update it in one place and re-deploy Jenkins — all pipelines pick it up automatically.

## Version requirement

**Nexus ≥ 3.65.0 is required for native Dart/pub support.** Earlier versions will accept the repository creation API call but won't actually serve the Dart protocol correctly. Pin your image tag.
