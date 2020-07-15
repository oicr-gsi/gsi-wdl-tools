#!/usr/bin/env python3

import argparse
import re
import WDL

parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument("--input-wdl-path", required=True)
parser.add_argument("--docker-image", required=False)
args = parser.parse_args()

doc = WDL.load(args.input_wdl_path)         # loads the entire document

# converts all tabs to spaces for compatibility
def tabs_to_spaces(num_spaces):     # what about multiple tabs, or tab is in a string?
    for index in range(len(doc.source_lines)):
        line = doc.source_lines[index].lstrip('\t')     # strips leading tabs
        num_tabs = len(doc.source_lines[index]) - len(line)     # how many tabs were stripped away
        doc.source_lines[index] = " " * num_spaces * num_tabs + line

# add docker to every task and workflow explicitly
def docker_runtime():
    # exit if use doesn't want to add a docker image
    if not args.docker_image:
        return

    # add image to workflow inputs
    if "docker" not in doc.workflow.inputs:
        print("placeholder")
        # append args.docker_image with docker: "~{docker}"
    else:
        print("placeholder")
        # replace old docker with docker: "~{docker}"

    # add image to all calls "docker = docker"
    # think about whether add comma
    for input in doc.workflow.available_inputs:
        print("placeholder")
        # all call inputs stored in available_inputs, prefixed with namespace

    # add image to all tasks
    for task in doc.tasks:
        if("docker" not in task.runtime):   # need to add docker to runtime, inputs, and call
            # @@@@@@@@@@@@@@@
            print("placeholder")

# pull all task variables to the workflow that calls them
def pull_to_root():
    print("placeholder")

# source .bashrc and load required modules for each task
def source_modules():
    for task in doc.tasks or []:
        for input in task.inputs or []:
            index = doc.source_lines[input.pos.line - 1].find("String modules")
            if index > -1:  # if the task does use modules
                position = task.command.pos.line
                num_spaces = doc.source_lines[position].rfind("  ") + 2
                append = ' ' * num_spaces + 'source /home/ubuntu/.bashrc \n' + ' ' * num_spaces + '~{"module load " + modules + " || exit 20; "} \n\n' + ' ' * num_spaces
                doc.source_lines[position] = append + doc.source_lines[position][num_spaces:]  # replace old command with the new

# find all params that need to be replaced, for example:
def test():
    for part in doc.workflow.body:
        if isinstance(part, WDL.Tree.Call):
            print(part.name)

# final outputs to stdout or a file with modified name
def write_out():
    name_index = args.input_wdl_path.rfind('/')
    output_path = args.input_wdl_path[:name_index + 1] + "dockstore_" + args.input_wdl_path[name_index + 1:]
    with open(output_path, "w") as output_file:
        output_file.write("\n".join(doc.source_lines))

# tabs_to_spaces(8) # tested
# docker_runtime()
# pull_to_root()
# source_modules()  # need testing after changes
test()
write_out()     # tested