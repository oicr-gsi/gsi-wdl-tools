version 1.0

# A scatter over a call's output, and an if on a call's output. The calls inside read only
# the scatter variable or workflow inputs, so the producers show up as dependencies of the
# blocks, not of the calls. The scatter collection goes through a declaration first.

workflow blockdeps {
    input {
        File bam
    }

    call prep { input: bam = bam }
    call split { input: f = prep.out }
    Array[File] pieces = split.pieces

    scatter (piece in pieces) {
        call work { input: piece = piece }
    }

    call check { input: x = bam }
    if (check.ok) {
        call extra { input: x = bam }
    }

    call merge { input: parts = work.out }

    output {
        File merged = merge.out
        File? extraOut = extra.out
    }
}

task prep {
    input { File bam }
    command <<< touch out >>>
    output { File out = "out" }
}

task split {
    input { File f }
    command <<< touch a b >>>
    output { Array[File] pieces = ["a", "b"] }
}

task work {
    input { File piece }
    command <<< touch out >>>
    output { File out = "out" }
}

task check {
    input { File x }
    command <<< echo true >>>
    output { Boolean ok = read_boolean(stdout()) }
}

task extra {
    input { File x }
    command <<< touch out >>>
    output { File out = "out" }
}

task merge {
    input { Array[File] parts }
    command <<< touch out >>>
    output { File out = "out" }
}
