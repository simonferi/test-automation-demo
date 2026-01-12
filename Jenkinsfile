// Jenkinsfile for Smoke Test Pipeline

pipeline {
    agent any
    
    parameters {
        choice(
            name: 'SPEC_FILE',
            choices: [
                'specs/payments.yaml',
                'specs/commerce.yaml',
                'specs/flights.yaml'
            ],
            description: 'OpenAPI specification to test'
        )
        string(
            name: 'REST_PORT',
            defaultValue: '9101',
            description: 'REST API port for mock server'
        )
        choice(
            name: 'OUTPUT_FORMAT',
            choices: ['json', 'rich', 'plain'],
            description: 'Test output format'
        )
        booleanParam(
            name: 'KEEP_MOCK_RUNTIME',
            defaultValue: false,
            description: 'Keep mock server running after tests'
        )
    }
    
    environment {
        CONSOLE_OUTPUT_FORMAT = "${params.OUTPUT_FORMAT}"
        PYTHON_VERSION = '3.12'
    }
    
    stages {
        stage('Setup') {
            steps {
                echo "Setting up environment for ${params.SPEC_FILE}"
                sh '''
                    # Install uv if not present
                    if ! command -v uv &> /dev/null; then
                        curl -LsSf https://astral.sh/uv/install.sh | sh
                        export PATH="$HOME/.cargo/bin:$PATH"
                    fi
                    
                    # Sync dependencies
                    uv sync
                '''
            }
        }
        
        stage('Run Smoke Tests') {
            steps {
                script {
                    def keepMockFlag = params.KEEP_MOCK_RUNTIME ? '--keep-mock' : ''
                    
                    sh """
                        python scripts/run-smoke-pipeline.py \\
                            --spec ${params.SPEC_FILE} \\
                            --port ${params.REST_PORT} \\
                            --output-format ${params.OUTPUT_FORMAT} \\
                            ${keepMockFlag}
                    """
                }
            }
        }
        
        stage('Parse Results') {
            steps {
                script {
                    // Find latest run directory
                    def latestRun = sh(
                        script: 'ls -td runs/*/ | head -1',
                        returnStdout: true
                    ).trim()
                    
                    if (latestRun) {
                        def reportFile = "${latestRun}/execution-report.json"
                        
                        if (fileExists(reportFile)) {
                            def report = readJSON file: reportFile
                            
                            echo """
                                ===========================
                                Smoke Test Results
                                ===========================
                                Status: ${report.summary.status}
                                Total:  ${report.summary.total_scenarios}
                                Passed: ${report.summary.passed_scenarios}
                                Failed: ${report.summary.failed_scenarios}
                                ===========================
                            """
                            
                            // Fail build if tests failed
                            if (report.summary.status != 'passed') {
                                error("Smoke tests failed!")
                            }
                        }
                    }
                }
            }
        }
    }
    
    post {
        always {
            // Archive test results
            archiveArtifacts artifacts: 'runs/**/*', allowEmptyArchive: true
            
            // Publish test results if JUnit format available
            junit testResults: 'runs/**/junit-report.xml', allowEmptyResults: true
            
            // Clean workspace
            cleanWs()
        }
        
        success {
            echo 'Smoke tests passed successfully!'
        }
        
        failure {
            echo 'Smoke tests failed. Check the archived artifacts for details.'
        }
    }
}


// Multibranch Pipeline Alternative
// Use this for testing multiple specs in parallel

pipeline {
    agent any
    
    stages {
        stage('Parallel Smoke Tests') {
            parallel {
                stage('Payments') {
                    steps {
                        sh '''
                            python scripts/run-smoke-pipeline.py \\
                                --spec specs/payments.yaml \\
                                --port 9101 \\
                                --output-format json
                        '''
                    }
                }
                
                stage('Commerce') {
                    steps {
                        sh '''
                            python scripts/run-smoke-pipeline.py \\
                                --spec specs/commerce.yaml \\
                                --port 9102 \\
                                --output-format json
                        '''
                    }
                }
                
                stage('Flights') {
                    steps {
                        sh '''
                            python scripts/run-smoke-pipeline.py \\
                                --spec specs/flights.yaml \\
                                --port 9103 \\
                                --output-format json
                        '''
                    }
                }
            }
        }
    }
    
    post {
        always {
            archiveArtifacts artifacts: 'runs/**/*'
        }
    }
}
