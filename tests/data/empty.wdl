version 1.0

workflow empty {
  input {	
    Int exitCode = 0
    Int n = 10
  }
  parameter_meta {
    exitCode: "Exit code"
    n: "Number of lines to log to stderr"
  }
  call log {
    input:
      exitCode = exitCode,
      n = n
  }
  output {
    File err = log.err
   
  }
  meta {
    author: "Jenniffer Meng"
    email: "jenniffer.meng@oicr.on.ca"
    description: "Workflow for testing infrastructure"
    output_meta: {
      err: {
        description: "Gzipped and sorted index ...",
        vidarr_label: "counts"
      }
      
    }
    dependencies: [
            {
                name: "dependency_name",
                url: "dependency_url"
            }
        ]
  }
}

task log {
  input {
    Int exitCode
    Int n
    Int mem = 1
    Int timeout = 1
  }
  command <<<
    set -euo pipefail
    # Output n lines to stderr
    for (( i = 1; i <= ~{n}; i++ )) ; do
      echo "This is a place holder stderr line ${i}" 1>&2
    done
    exit ~{exitCode}
  >>>
  runtime {
    memory: "~{mem} GB"
    timeout: "~{timeout}"
  }
  output {
    File err = stderr()
  }
  parameter_meta {
    exitCode: "Integer used to fail as appropriate"
    n: "Number of lines to log to stderr"
    mem: "Memory (in GB) to allocate to the job"
    timeout: "Maximum amount of time (in hours) the task can run for"
  }
  meta {
    output_meta: {
      err: "stderr lines produced"
    }
  }
}
