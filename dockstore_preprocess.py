#!/usr/bin/env python3

import argparse
import WDL

parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument("--input-wdl-path", required=True)
args = parser.parse_args()

doc = WDL.load(args.input_wdl_path)         # loads the entire document

# add docker to every task and workflow explicitly
def docker_runtime():
    for task in doc.tasks:
        if("docker" not in task.runtime):   # need to add docker to runtime, inputs, and call
            # @@@@@@@@@@@@@@@
            print("placeholder")

# source .bashrc and load required modules for each task
def source_modules():
    prepend = 'source /root/.bashrc \n ${"module load " + modules + " || exit 1; "} \n\n'
    for task in doc.tasks:
        for input in task.inputs:
            index = doc.source_lines[input.pos.line - 1].find("String modules")
            if index > -1:  # if the task does use modules
                doc.source_lines[task.command.pos.line - 1] = prepend + task.command.parts

# find all params that need to be replaced, for example:
def test():
    for task in doc.tasks:
        print(task.command.parts)

# final outputs to stdout or a file with modified name
def write_out():
    # print("\n".join(doc.source_lines))      # prints the entire workflow to stdout

    name_index = args.input_wdl_path.rfind('/')
    output_path = args.input_wdl_path[:name_index + 1] + "dockstore_" + args.input_wdl_path[name_index + 1:]
    with open(output_path, "w") as output_file:
        output_file.write("\n".join(doc.source_lines))

test()
# write_out()     # successfully creates / overwrites to the right destination
# source_modules()