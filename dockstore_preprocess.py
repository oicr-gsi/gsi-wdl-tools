#!/usr/bin/env python3

import argparse
import WDL

parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument("--input-wdl-path", required=True)  # works!
args = parser.parse_args()

# find all params that need to be replaced, for example:
w = WDL.load(args.input_wdl_path)   # '/home/ubuntu/repos/starfusion/starFusion.wdl'
for input in w.workflow.inputs:     # for each line in the workflow inputs
    index = str(input).find("File? chimeric")
    if index > -1:      # if that line is found
        print(index)
        newInput = ' ' * index + 'File? chimeric = "/some/run/file/"'   # change it and add spaces in front
        w.source_lines[input.pos.line - 1] = newInput   # replace the original with the new line
# write out to new wdl file
print("\n".join(w.source_lines))    # print the new workflow, or write to the new wdl file