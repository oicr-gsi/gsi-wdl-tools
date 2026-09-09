version 1.0
workflow mutect2Consensus {
    input {
        InputGroup tumorInputGroup
        InputGroup normalInputGroup
        Array[String] chromosomes = ["chr1","chr2","chr3","chr4","chr5","chr6"]
    }
    Array[InputGroup] inputGroups = select_all([tumorInputGroup,normalInputGroup])
    scatter (ig in inputGroups) {
        call annotate { input: g = ig }
        call filter { input: v = annotate.out }
    }
    scatter (chr in chromosomes) {
        call perChrom { input: c = chr }
    }
    call combine { input: parts = filter.out, chrs = perChrom.out }
    output { File merged = combine.out }
}
task annotate { input { InputGroup g } command <<< echo a >>> output { File out = "o" } }
task filter { input { File v } command <<< echo f >>> output { File out = "o" } }
task perChrom { input { String c } command <<< echo p >>> output { File out = "o" } }
task combine { input { Array[File] parts
                       Array[File] chrs } command <<< echo c >>> output { File out = "o" } }
