version 1.0

workflow workflow1 {

    input {
        File myFile
        String optionalString = "default"
    }

    call myTask {
        input:
            inputFile = myFile,
            fileName = optionalString
    }

    output {
        File outputFile = myTask.outputFile
    }

    parameter_meta {
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
        output_meta: {
            outputFile: "Text output file"
        }
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