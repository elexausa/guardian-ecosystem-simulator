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
      PATH = "/opt/miniconda3/bin:$PATH"
      ELEXA_PYPI_REPO_URL = credentials('elexa-pypi-repo-url')
      ELEXA_PYPI_REPO_USER = credentials('elexa-pypi-repo-user')
      ELEXA_PYPI_REPO_PASS = credentials('elexa-pypi-repo-pass')
    }

    stages {
        stage ('Pull') {
            steps {
                checkout scm
            }
        }
        stage('Build environment') {
            steps {
                sh '''conda create --yes -n ${BUILD_TAG} python
                      source activate ${BUILD_TAG}
                      pip install -r requirements.txt
                   '''
            }
        }
        stage('Test environment') {
            steps {
                sh '''source activate ${BUILD_TAG}
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
                slackSend (color: '#FFFF00', message: ":exclamation: Building `ges_pkg`...\n\n ${env.JOB_NAME} [${env.BUILD_NUMBER}] (${env.BUILD_URL})")

                sh '''cd ges_pkg
                      python setup.py bdist_wheel
                   '''
            }
            post {
                always {
                    archiveArtifacts(allowEmptyArchive: true, artifacts: 'ges_pkg/dist/*whl', fingerprint: true)
                }
                success {
                    slackSend (color: '#00FF00', message: ":heavy_check_mark: `ges_pkg` build succeeded!\n\n ${env.JOB_NAME} [${env.BUILD_NUMBER}] (${env.BUILD_URL})")
                }
                failure {
                    slackSend (color: '#FF0000', message: ":heavy_multiplication_x: `ges_pkg` build failed!\n\n ${env.JOB_NAME} [${env.BUILD_NUMBER}] (${env.BUILD_URL})")
                }
            }
        }
        stage ('Deploy develop ges_pkg') {
            when {
                branch 'develop'
            }
            steps {
                sh '''source activate ${BUILD_TAG}
                      twine upload --repository-url $ELEXA_PYPI_REPO_URL -u $ELEXA_PYPI_REPO_USER -p $ELEXA_PYPI_REPO_PASS ges_pkg/dist/*
                   '''
            }
            post {
                success {
                    slackSend (color: '#00FF00', message: "Deployed `ges_pkg` origin/develop build to pypi (${ELEXA_PYPI_REPO_URL})")
                }
            }
        }
        stage ('Deploy master ges_pkg') {
            when {
                branch 'master'
            }
            steps {
                sh '''source activate ${BUILD_TAG}
                      twine upload --repository-url $ELEXA_PYPI_REPO_URL -u $ELEXA_PYPI_REPO_USER -p $ELEXA_PYPI_REPO_PASS ges_pkg/dist/*
                   '''
            }
            post {
                success {
                    slackSend (color: '#00FF00', message: "Deployed `ges_pkg` origin/master build to pypi (${ELEXA_PYPI_REPO_URL})")
                }
            }
        }
    }
    post {
        always {
            echo 'Removing conda environment'
            sh 'conda remove --yes -n ${BUILD_TAG} --all'
        }
        success {
            echo 'Build succeeded'
            slackSend (color: '#00FF00', message: ":heavy_check_mark: `guardian_ecosystem_simulator build succeeded! \n\n ${env.JOB_NAME} [${env.BUILD_NUMBER}] (${env.BUILD_URL})")
        }
        failure {
            echo 'Build failed'
            slackSend (color: '#FF0000', message: ":heavy_multiplication_x: `guardian_ecosystem_simulator build failed! \n\n ${env.JOB_NAME} [${env.BUILD_NUMBER}] (${env.BUILD_URL})")
        }
        unstable {
            echo 'Unstable build'
        }
        changed {
            echo 'Pipeline changed state (failing->successful or vice versa)'
        }
    }
}