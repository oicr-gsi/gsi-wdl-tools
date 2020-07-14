#!/usr/bin/env python3

import argparse
import WDL

parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument("--input-wdl-path", required=True)
args = parser.parse_args()

doc = WDL.load(args.input_wdl_path)     # loads the entire document

# find all params that need to be replaced, for example:
def test():
    for input in doc.workflow.inputs:       # for each line in the workflow inputs
        index = doc.source_lines[input.pos.line - 1].find("File? chimeric")   # now it detects the number of spaces in front
        if index > -1:      # if that line is found
            print(index)
            newInput = ' ' * index + 'File? chimeric = "/some/run/file/"'   # change it and add spaces in front
            doc.source_lines[input.pos.line - 1] = newInput   # replace the original with the new line

# final outputs to stdout or a file with modified name
def write_out():
    # print("\n".join(w.source_lines))      # prints the entire workflow to stdout

    name_index = args.input_wdl_path.rfind('/')
    output_path = args.input_wdl_path[:name_index + 1] + "dockstore_" + args.input_wdl_path[name_index + 1:]
    with open(output_path, "w") as output_file:
        output_file.write("\n".join(w.source_lines))
test()
write_out()