---
layout: post
title: "Jenkins Configuration as Code: bake credentials in at deploy time, not runtime"
date: 2026-05-13
categories: [devops, ci-cd]
tags: [jenkins, jcasc, terraform, secrets, self-hosted]
excerpt: "Most JCasC tutorials inject credentials as environment variables at container startup. There's a cleaner approach: render the YAML with Terraform's templatefile() at apply time so the container starts with a static config and needs nothing from the host environment."
author: Douglas Lockamy
ai_assisted: true
---

Jenkins Configuration as Code (JCasC) is genuinely good — declarative Jenkins configuration, version-controlled, no more clicking through the UI to set up credentials and tools. But almost every guide I've seen for handling secrets in JCasC lands on the same approach: store credentials as environment variables, reference them with `${SECRET_VAR}` syntax in the YAML, and inject them at container startup.

It works. It's also not great. Here's why, and what I do instead.

## The problem with env var injection

The JCasC `${SECRET_VAR}` syntax resolves variables from the container's environment at startup. That means your secrets need to be present as environment variables when the container starts. In practice this means one of:

- Passing them via `docker run -e SECRET_VAR=value` — plaintext in shell history and `docker inspect` output
- Writing them to an `.env` file on the host — secrets on disk
- Pulling them from a secrets manager at startup via an entrypoint script — more moving parts, more failure modes

Any of these approaches means the secrets have to exist on the host in some form before the container starts. The host becomes a secrets surface.

## The alternative: templatefile() at apply time

Terraform's `templatefile()` function renders a template with variable substitution at `terraform apply` time. If your secrets are already in Terraform (fetched from AWS Secrets Manager, Vault, or similar), you can render the complete JCasC YAML — credentials and all — before the container starts.

The template uses standard HCL interpolation:

```yaml
# jcasc/jenkins.yaml.tpl
credentials:
  system:
    domainCredentials:
      - credentials:

          - usernamePassword:
              scope: GLOBAL
              id: nexus-credentials
              description: "Nexus artifact repository"
              username: "${nexus_user}"
              password: "${nexus_password}"

          - basicSSHUserPrivateKey:
              scope: GLOBAL
              id: io-ssh-key
              description: "SSH deploy key"
              username: "deploy"
              privateKeySource:
                directEntry:
                  privateKey: |
                    ${indent(20, io_ssh_key)}

          - usernamePassword:
              scope: GLOBAL
              id: github-token
              description: "GitHub PAT"
              username: "dlockamy"
              password: "${github_token}"
```

Note the `indent()` call for the SSH key — multiline strings in YAML require careful indentation, and Terraform's `indent()` function handles this cleanly.

The Terraform resource that renders and deploys it:

```hcl
resource "null_resource" "jcasc_config" {
  connection {
    type        = "ssh"
    host        = var.ssh_host
    user        = var.ssh_user
    private_key = module.secrets.jenkins_io_ssh_key
  }

  provisioner "remote-exec" {
    inline = ["mkdir -p /opt/sol/jenkins/jcasc"]
  }

  provisioner "file" {
    content = templatefile("${path.module}/jcasc/jenkins.yaml.tpl", {
      admin_user     = var.jenkins_admin_user
      admin_password = module.secrets.jenkins_admin_password
      nexus_user     = module.secrets.jenkins_nexus_user
      nexus_password = module.secrets.jenkins_nexus_password
      github_token   = module.secrets.jenkins_github_token
      io_ssh_key     = module.secrets.jenkins_io_ssh_key
    })
    destination = "/opt/sol/jenkins/jcasc/jenkins.yaml"
  }

  provisioner "remote-exec" {
    inline = ["chmod 0600 /opt/sol/jenkins/jcasc/jenkins.yaml"]
  }
}
```

The rendered file lands on the host at `0600`. The container mounts it read-only:

```hcl
resource "docker_container" "jenkins" {
  depends_on = [null_resource.jcasc_config]

  env = [
    "CASC_JENKINS_CONFIG=/var/jenkins_home/casc_configs",
    "JAVA_OPTS=-Djenkins.install.runSetupWizard=false"
    # No secret env vars — credentials are in the rendered YAML
  ]

  volumes {
    host_path      = "/opt/sol/jenkins/jcasc"
    container_path = "/var/jenkins_home/casc_configs"
    read_only      = true
  }
}
```

When the container starts, it reads a static YAML file. No environment variable resolution. No entrypoint scripts. No secrets in `docker inspect`.

## What the container needs at runtime

With this approach, the container's environment is clean:

```yaml
env:
  - CASC_JENKINS_CONFIG=/var/jenkins_home/casc_configs
  - JAVA_OPTS=-Djenkins.install.runSetupWizard=false
  - DOCKER_HOST=tcp://docker:2376
  - DOCKER_CERT_PATH=/certs/client
  - DOCKER_TLS_VERIFY=1
```

No `NEXUS_PASS`, no `GITHUB_TOKEN`, no `JENKINS_ADMIN_PASSWORD`. The container doesn't know its own credentials. They're baked into the config file it reads.

## The full JCasC template

Beyond credentials, JCasC configures everything declaratively:

```yaml
jenkins:
  systemMessage: |
    Jenkins CI/CD — managed by JCasC.
    Changes must be made in the infrastructure repo.

  numExecutors: 4
  securityRealm:
    local:
      allowsSignup: false
      users:
        - id: "${admin_user}"
          password: "${admin_password}"

  authorizationStrategy:
    loggedInUsersCanDoAnything:
      allowAnonymousRead: false

tool:
  terraform:
    installations:
      - name: terraform-1.7
        properties:
          - installSource:
              installers:
                - terraformInstaller:
                    id: "1.7.0-linux-amd64"

jobs:
  - script: >
      pipelineJob('sol-infrastructure') {
        definition {
          cpsScm {
            scm {
              git {
                remote {
                  url('https://github.com/softsurve/sol.git')
                  credentials('github-token')
                }
                branch('*/main')
              }
            }
            scriptPath('Jenkinsfile')
          }
        }
      }
```

The `jobs` section seeds pipeline jobs automatically on first boot. No manual job creation.

## Rotating credentials

Update the credential in AWS Secrets Manager, then re-run `terraform apply` on the Jenkins module. Terraform fetches the new value, re-renders the JCasC YAML, and writes it to the host. Reload JCasC in the Jenkins UI to pick it up without a full restart.

No Jenkins UI interaction required for the credential itself.

## The tradeoff

The rendered YAML file contains plaintext credentials on the host filesystem at `0600`. This is less bad than it sounds — if you have root on the host, you already own the running container and can read credentials from the process environment anyway. The permissions are defence in depth, not a hard boundary.

The threat model is: no credentials in the CI environment at runtime, no credentials in env vars or process listings. It's not: no credentials anywhere on the machine.

The full implementation is in [softsurve/sol](https://github.com/softsurve/sol) under `services/jenkins/`.
