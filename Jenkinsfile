pipeline {
  // `agent any` was landing on agents with no docker (e.g. a macOS agent —
  // see build #1/#2 failures: "docker: command not found"), which the
  // per-stage `docker { ... reuseNode true }` blocks then fail on. Pin to
  // a docker-capable Linux agent, matching the convention used by
  // quickring/hub's Jenkinsfile.cd and courier's release pipeline.
  agent { label 'earth' }

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
