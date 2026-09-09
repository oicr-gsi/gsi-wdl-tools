version 1.0

import "other.wdl" as helper

workflow nesting {
    input {
        Array[File] bams
        String? label
        Int threads = 4
    }

    call prepare { input: n = length(bams) }

    if (defined(label)) {
        scatter (b in bams) {
            call perShard { input: bam = b, hint = prepare.hint }
        }
        # a dependency threaded through an intermediate declaration
        Array[File] shardOut = select_all(perShard.out)
        call gather { input: parts = shardOut }
    }

    # multi-line scatter expression, and a multi-line call input block
    scatter (pair in zip(
                 bams,
                 bams)) {
        call pairwise {
            input:
                left = pair.left,
                right = pair.right
        }
    }

    call helper.imported { input: x = prepare.hint }

    output {
        File? merged = gather.merged
        Array[File] pairs = pairwise.out
    }
}

task prepare {
    input { Int n }
    command <<<
        # this block contains decoys: call fake { } and if ( and scatter (
        echo "call notARealCall"
    >>>
    output { String hint = "x" }
}

task perShard {
    input { File bam
            String hint }
    command { echo "another decoy: call alsoFake" }
    output { File out = "o" }
}

task gather {
    input { Array[File] parts }
    command <<< echo g >>>
    output { File merged = "m" }
}

task pairwise {
    input { File left
            File right }
    command <<< echo p >>>
    output { File out = "o" }
}
