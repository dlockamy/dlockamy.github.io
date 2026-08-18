pipeline {
  // `agent any` was landing on agents with no docker (e.g. a macOS agent —
  // see build #1/#2 failures: "docker: command not found"), which the
  // per-stage `docker { ... reuseNode true }` blocks then fail on. Pin to
  // a docker-capable Linux agent, matching the convention used by
  // quickring/hub's Jenkinsfile.cd and courier's release pipeline.
  agent { label 'linux-build' }

  environment {
    NEXUS_URL = 'https://nexus.softsurve.com'
  }

  stages {

    stage('Pre-flight') {
      steps {
        script {
          def msg = sh(script: 'git log -1 --pretty=%B', returnStdout: true).trim()
          if (msg.contains('[skip ci]')) {
            currentBuild.result = 'NOT_BUILT'
            error('Commit contains [skip ci] — aborting.')
          }
        }
      }
    }

    stage('Build') {
      agent {
        docker {
          image 'ruby:3.1-slim'
          reuseNode true
          // The agent's default docker run uses a fixed non-root UID, which
          // can't write /var/lib/apt/lists — apt-get update failed with
          // "Permission denied" (build #3), silently (no `set -e` in the sh
          // block below), so build-essential never installed and the json
          // gem's native extension had no compiler to build with. Matches
          // why quickring/hub's release Jenkinsfile runs its Linux stage
          // `.inside('-u root')` too.
          args '-u root'
        }
      }
      steps {
        sh '''
          apt-get update -qq && apt-get install -y -qq build-essential
          bundle install --path vendor/bundle
          bundle exec jekyll build
        '''
      }
      post {
        success {
          archiveArtifacts artifacts: '_site/**', allowEmptyArchive: false
        }
      }
    }

    // Publish built site as a versioned gem to Nexus RubyGems
    // (allows Jekyll theme assets to be consumed by other repos)
    stage('Publish Gem') {
      agent {
        docker {
          image 'ruby:3.1-slim'
          reuseNode true
          // The agent's default docker run uses a fixed non-root UID, which
          // can't write /var/lib/apt/lists — apt-get update failed with
          // "Permission denied" (build #3), silently (no `set -e` in the sh
          // block below), so build-essential never installed and the json
          // gem's native extension had no compiler to build with. Matches
          // why quickring/hub's release Jenkinsfile runs its Linux stage
          // `.inside('-u root')` too.
          args '-u root'
        }
      }
      when {
        branch 'master' // this repo's actual default branch — was 'main', never matched
      }
      steps {
        withCredentials([usernamePassword(
          credentialsId: 'nexus-credentials',
          usernameVariable: 'NEXUS_USER',
          passwordVariable: 'NEXUS_PASS'
        )]) {
          sh '''
            apt-get update -qq && apt-get install -y -qq build-essential
            # Only publish if a gemspec exists
            if ls *.gemspec 1>/dev/null 2>&1; then
              gem build *.gemspec
              gem push *.gem \
                --host "${NEXUS_URL}/repository/rubygems-hosted/" \
                --key "${NEXUS_USER}:${NEXUS_PASS}"
            else
              echo "No gemspec found — skipping gem publish. Site build artifact archived above."
            fi
          '''
        }
      }
    }

  }

  post {
    always { cleanWs() }
  }
}
