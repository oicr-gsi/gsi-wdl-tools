version 1.0

# Imported by flowchart_nesting.wdl. The flowchart tool never draws what is inside an
# imported file, but the parser has to be able to load it.

task imported {
    input {
        String x
    }
    command <<< echo "~{x}" >>>
    output {
        File out = stdout()
    }
}
