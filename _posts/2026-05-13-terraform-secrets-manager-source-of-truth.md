---
layout: post
title: "AWS Secrets Manager as the single source of truth for Terraform"
date: 2026-05-13
categories: [devops, infrastructure]
tags: [terraform, aws, secrets-manager, jenkins, self-hosted]
excerpt: "Most guides still inject secrets as env vars or Jenkins credentials. Here's a cleaner pattern: one shared Terraform module, secrets baked in at apply time, nothing sensitive on the host at runtime."
author: Douglas Lockamy
ai_assisted: true
---

Most guides on secrets management in Terraform still reach for the same two approaches: `TF_VAR_` environment variables passed at the command line, or credentials stored in the CI system's UI and injected at runtime. Both work. Neither is clean.

Here's the pattern I landed on for the Sol network — a self-hosted infrastructure stack running Jenkins, Nexus, and Grafana on a private home server. AWS Secrets Manager as the single source of truth. No secrets in env vars. No secrets in the Jenkins credentials UI. Nothing sensitive on the host at runtime. One IAM key pair in Jenkins, and it gates everything else.

## The problem with the usual approaches

**Environment variables** (`TF_VAR_nexus_admin_password=...`) require whoever's running the pipeline to have the secrets locally, or require your CI system to have them injected as masked env vars. They show up in process listings. They're easy to accidentally log. And when you have eight secrets across three services, you end up with a fragile wall of `TF_VAR_` declarations that needs to be maintained everywhere the pipeline runs.

**Jenkins credentials UI** is better — at least they're encrypted at rest and masked in logs. But now your secrets live in two places: whatever your source of truth is, and Jenkins. Rotating a credential means updating it in both. And if you ever re-provision Jenkins (which you will), you have to remember to re-enter every credential by hand.

## The pattern: a shared secrets module

The key insight is that the AWS provider can fetch from Secrets Manager at `terraform plan/apply` time. That means secrets can be resolved once, in one place, and threaded through as sensitive Terraform outputs — never stored in state as plaintext, never passed on the command line.

The shared module lives at `modules/secrets/` and looks like this:

```hcl
# modules/secrets/main.tf

terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

data "aws_secretsmanager_secret_version" "nexus_admin_password" {
  secret_id = "sol/nexus/admin-password"
}

data "aws_secretsmanager_secret_version" "jenkins_admin_password" {
  secret_id = "sol/jenkins/admin-password"
}

# ... all eight secrets
```

```hcl
# modules/secrets/outputs.tf

output "nexus_admin_password" {
  value     = data.aws_secretsmanager_secret_version.nexus_admin_password.secret_string
  sensitive = true
}
```

Every service module calls it the same way:

```hcl
# services/nexus/main.tf

module "secrets" {
  source     = "../../modules/secrets"
  aws_region = var.aws_region
}

provider "ssh" {
  host        = var.ssh_host
  user        = var.ssh_user
  private_key = module.secrets.jenkins_io_ssh_key  # resolved from SM
}
```

## JCasC: bake in at deploy time, not inject at runtime

This is where the pattern pays off most clearly. Jenkins Configuration as Code supports `${SECRET_VAR}` syntax for injecting credentials at container startup — but that means the secret has to be present as an environment variable on the host, which brings us back to the same problem.

The alternative: use Terraform's `templatefile()` to render the JCasC YAML with secrets resolved at `terraform apply` time, then write the rendered file to the host via SSH before the container starts.

```hcl
resource "ssh_resource" "jcasc_config" {
  host        = var.ssh_host
  user        = var.ssh_user
  private_key = module.secrets.jenkins_io_ssh_key

  file {
    content = templatefile("${path.module}/jcasc/jenkins.yaml.tpl", {
      admin_password = module.secrets.jenkins_admin_password
      nexus_user     = module.secrets.jenkins_nexus_user
      nexus_password = module.secrets.jenkins_nexus_password
      github_token   = module.secrets.jenkins_github_token
      io_ssh_key     = module.secrets.jenkins_io_ssh_key
    })
    destination = "/opt/sol/jenkins/jcasc/jenkins.yaml"
    permissions = "0600"
  }
}
```

The JCasC template uses plain `${var}` interpolation:

```yaml
# jcasc/jenkins.yaml.tpl
credentials:
  system:
    domainCredentials:
      - credentials:
          - usernamePassword:
              id: nexus-credentials
              username: "${nexus_user}"
              password: "${nexus_password}"
```

When the container starts, it reads a static YAML file. No env vars. No secret resolution at runtime. The container itself is clean.

## The one credential in Jenkins

The only thing that lives in the Jenkins credentials UI is `aws-sol-deploy` — an IAM key pair with `secretsmanager:GetSecretValue` on `sol/*`. This is deliberate: it's what accesses Secrets Manager, so it can't itself come from Secrets Manager. Everything else flows from it.

```groovy
// Jenkinsfile
withCredentials([
  usernamePassword(
    credentialsId: 'aws-sol-deploy',
    usernameVariable: 'AWS_ACCESS_KEY_ID',
    passwordVariable: 'AWS_SECRET_ACCESS_KEY'
  )
]) {
  sh '''
    export AWS_DEFAULT_REGION="${AWS_REGION}"
    cd services/${SERVICE}
    terraform init
    terraform apply -auto-approve tfplan-${SERVICE}
  '''
}
```

Rotate `aws-sol-deploy` and you rotate access to everything. Add a new secret to SM and it's available to Terraform immediately — no Jenkins UI changes, no pipeline updates, no env var declarations.

## Secret paths

A consistent naming convention makes this maintainable:

```
sol/nexus/admin-user
sol/nexus/admin-password
sol/jenkins/admin-password
sol/jenkins/nexus-user
sol/jenkins/nexus-password
sol/jenkins/github-token
sol/jenkins/io-ssh-key
sol/grafana/admin-password
```

`sol/` prefix scopes the IAM policy cleanly. The `<service>/<key>` structure makes it obvious where each secret belongs and keeps the policy simple:

```json
{
  "Effect": "Allow",
  "Action": "secretsmanager:GetSecretValue",
  "Resource": "arn:aws:secretsmanager:us-east-1:*:secret:sol/*"
}
```

## Provisioning secrets the first time

The bootstrap question: how do you put secrets *into* SM before Terraform can read them out? A small interactive shell script handles this once:

```bash
#!/usr/bin/env bash

upsert_secret() {
  local path="$1" description="$2" value="$3"

  if aws secretsmanager describe-secret --secret-id "$path" &>/dev/null; then
    aws secretsmanager put-secret-value --secret-id "$path" --secret-string "$value"
  else
    aws secretsmanager create-secret --name "$path" \
      --description "$description" --secret-string "$value"
  fi
}

read -rsp "Nexus admin password: " NEXUS_PASS; echo
upsert_secret "sol/nexus/admin-password" "Nexus admin password" "$NEXUS_PASS"
# ... repeat for all secrets
```

Run it once from a machine with AWS credentials. After that, everything is driven from SM.

## What this solves

- **Rotation:** update a secret in SM, re-run `terraform apply`. Done.
- **Re-provisioning:** spin up a new Jenkins instance, run the pipeline. All credentials are restored from SM automatically.
- **Auditability:** CloudTrail logs every `GetSecretValue` call. You know exactly when and from where each secret was accessed.
- **Surface area:** one IAM key in Jenkins. Everything else is managed infrastructure.

The approach adds a dependency on AWS, which is a tradeoff worth naming. For a homelab or small team this is fine — SM is cheap and the IAM model is solid. For an air-gapped environment, the same pattern works with HashiCorp Vault as the backend, swapping the `aws` provider for the `vault` provider.

The full implementation lives in the [softsurve/sol](https://github.com/softsurve/sol) repo.
