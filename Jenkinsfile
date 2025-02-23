// This file relates to internal XMOS infrastructure and should be ignored by external users

@Library('xmos_jenkins_shared_library@v0.34.0') _

getApproval()

pipeline {
  agent {
    label 'documentation&&linux&&x86_64'
  }
  options {
    buildDiscarder(xmosDiscardBuildSettings())
    skipDefaultCheckout()
  }
  parameters {
    string(
      name: 'TOOLS_VERSION',
      defaultValue: '15.3.0',
      description: 'The XTC tools version'
    )
    string(
      name: 'XMOSDOC_VERSION',
      defaultValue: 'v6.1.3',
      description: 'The xmosdoc version'
    )
    string(
        name: 'INFR_APPS_VERSION',
        defaultValue: 'v2.0.1',
        description: 'The infr_apps version'
    )
  }
  environment {
    REPO = 'lib_ethernet'
    PIP_VERSION = "24.0"
    PYTHON_VERSION = "3.12.1"
  }
  stages {
    stage('Checkout') {
      steps {
        println "Stage running on: ${env.NODE_NAME}"
        dir("${REPO}") {
          checkout scm
          createVenv()
          installPipfile(false)
        }
      }
    }  // Get sandbox

    stage('Build examples') {
      steps {
        withTools(params.TOOLS_VERSION) {
          dir("${REPO}/examples") {
            script {
              // Build all apps in the examples directory
              sh "cmake -B build -G\"Unix Makefiles\" -DDEPS_CLONE_SHALLOW=TRUE"
              sh "xmake -j 32 -C build"
            } // script
          } // dir
        } //withTools
      } // steps
    }  // Build examples

    stage('Library checks') {
      steps {
        warnError("lib checks") {
          runLibraryChecks("${WORKSPACE}/${REPO}", "${params.INFR_APPS_VERSION}")
        }
      }
    }

    stage('Documentation') {
      steps {
        dir("${REPO}") {
          warnError("Docs") {
            buildDocs()
          }
        }
      }
    }

    stage('Simulator tests') {
      steps {
      	sh "git clone --branch v2.0.0 git@github.com:xmos/test_support.git"
      	dir("${REPO}") {
	      withVenv {
	      	sh "pip install -e ../test_support"
	      	withTools(params.TOOLS_VERSION) {
      		  dir("tests") {
      		    script {
      		      // Build all apps in the examples directory
      		      sh "cmake -B build -G\"Unix Makefiles\" -DDEPS_CLONE_SHALLOW=TRUE"
      		      sh "xmake -j 32 -C build"
      		    } // script
                runPytest('-vv')
	      	  }
	      	}
      	  }
      	}
      }
    }

  } // stages
  post {
    cleanup {
      xcoreCleanSandbox()
    } // cleanup
  } // post
} // pipeline
