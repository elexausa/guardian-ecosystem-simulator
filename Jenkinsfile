pipeline {
    agent any

    triggers {
        pollSCM('*/5 * * * 1-5')
    }

    options {
        skipDefaultCheckout(true)

        // Keep 10 most recent builds
        buildDiscarder(logRotator(numToKeepStr: '10'))
        timestamps()
    }

    environment {
      PATH="/opt/miniconda3/bin:$PATH"
      ELEXA_PYPI_REPO_URL = credentials('elexa-pypi-repo-url')
      ELEXA_PYPI_REPO_USER = credentials('elexa-pypi-repo-user')
      ELEXA_PYPI_REPO_PASS = credentials('elexa-pypi-repo-pass')
    }

    stages {
        stage ('Pull'){
            steps{
                checkout scm
            }
        }
        stage('Build environment') {
            steps {
                sh '''conda create --yes -n ${BUILD_TAG} python
                      conda activate ${BUILD_TAG}
                      pip install -r requirements.txt
                   '''
            }
        }
        stage('Test environment') {
            steps {
                sh '''conda activate ${BUILD_TAG}
                      pip list
                      which pip
                      which python
                   '''
            }
        }
        stage ('Build ges_pkg') {
            when {
                expression {
                    currentBuild.result == null || currentBuild.result == 'SUCCESS'
                }
            }
            steps {
                sh '''cd ges_pkg
                      python setup.py bdist_wheel
                   '''
            }
            post {
                always {
                    // Archive unit tests for the future
                    archiveArtifacts(allowEmptyArchive: true, artifacts: 'dist/*whl', fingerprint: true)
                }
            }
        }
        stage("Deploy to PyPI") {
            }
            steps {
                sh "twine upload --repository-url $ELEXA_PYPI_REPO_URL -u $ELEXA_PYPI_REPO_USER -p $ELEXA_PYPI_REPO_PASS dist/*"
            }
        }
    }
    post {
        always {
            echo 'Removing conda environment'
            sh 'conda remove --yes -n ${BUILD_TAG} --all'
        }
        success {
            echo 'This will run only if successful'
        }
        failure {
            echo 'This will run only if failed'
        }
        unstable {
            echo 'This will run only if the run was marked as unstable'
        }
        changed {
            echo 'This will run only if the state of the Pipeline has changed'
            echo 'For example, if the Pipeline was previously failing but is now successful'
        }
    }
}