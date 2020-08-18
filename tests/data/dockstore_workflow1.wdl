version 1.0

workflow workflow1 {

    input {
        String docker = "g3chen/wgsPipeline:2.0"
        Int myTask_memory = 8
        File myFile
        String optionalString = "default"
    }

    call myTask {
        input:
            docker = docker,
            memory = myTask_memory,
            inputFile = myFile,
            fileName = optionalString
    }

    output {
        File outputFile = myTask.outputFile
    }

    parameter_meta {
        docker: "Docker container to run the workflow in"
        myTask_memory: "Memory to allocate to job."
        myFile: "The input file."
        optionalString: "The output file name prefix."
    }

    meta {
        author: "author"
        email: "email"
        description: "Workflow description."
        dependencies: [
            {
                name: "tool1/1.0",
                url: "http://url"
            }, {
                name: "tool2/1.0",
                url: "http://url"
            }]
    }
}

task myTask {
    input {
        String docker = "g3chen/wgsPipeline:2.0"
        File inputFile
        String fileName
        Int memory = 8
    }

    command <<<
        ls -l ~{inputFile} > ~{fileName}.out
    >>>

    runtime {
        docker: "~{docker}"
        memory: "~{memory} G"
    }

    output {
        File outputFile = "~{fileName}.out"
    }

    parameter_meta {
        docker: "Docker container to run the workflow in"
        inputFile: "The input file."
        fileName: "The output file name prefix."
        memory: "Memory to allocate to job."
    }

    meta {
        output_meta: {
            outputFile: "Text output file"
        }
    }
}