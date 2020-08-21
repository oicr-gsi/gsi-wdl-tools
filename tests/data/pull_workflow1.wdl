version 1.0

workflow workflow1 {

    input {
        Int myTask_memory = 8
        File myFile
        String optionalString = "default"
    }

    call myTask {
        input:
            memory = myTask_memory,
            inputFile = myFile,
            fileName = optionalString
    }

    output {
        File outputFile = myTask.outputFile
    }

    parameter_meta {
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
        File inputFile
        String fileName
        Int memory = 8
    }

    command <<<
        ls -l ~{inputFile} > ~{fileName}.out
    >>>

    runtime {
        memory: "~{memory} G"
    }

    output {
        File outputFile = "~{fileName}.out"
    }

    parameter_meta {
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