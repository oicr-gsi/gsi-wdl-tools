#!/usr/bin/env python3

import argparse
import os
import re
import sys

from gsi_wdl_tools.workflow_info import *

parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument("--input-wdl-path", required=True)
parser.add_argument("--default-parameter-description",
                    help="Use this to provide a default description for parameters that have not be documented yet in the WDL file's parameter_meta section.",
                    required=False)

args = parser.parse_args()

try:
    info = WorkflowInfo(args.input_wdl_path, args.default_parameter_description)
except Exception as e:
    if hasattr(e, "pos"):
        print(f"WDL parsing error at line {e.pos.line}: {e}")
        raise SystemExit(1)
    raise (e)

def process_commands(wdl_file):
    dir_name = os.path.dirname(args.input_wdl_path)
    command_file = "./commands.txt" if dir_name == "" else dir_name + "/commands.txt"

    if not os.path.isfile(command_file):
        with open(args.input_wdl_path, 'r') as w:
            wdl_lines = w.readlines()
            multi_line = "".join(wdl_lines)
            my_commands = re.findall(r'<<<.*?>>>', multi_line, re.DOTALL)

        with open(command_file, 'a') as out_file:
            out_file.write('''## Commands
This section lists command(s) run by WORKFLOW workflow

* Running WORKFLOW

=== Description here ===.''')
            out_file.write("\n\n")
            for com in my_commands:
                out_file.write(com)
                out_file.write("\n")

        print(command_file + " created, please MANUALLY edit it and re-run this script!!!", file=sys.stderr)
    else:
        print(command_file + " found, printing out the content...", file=sys.stderr)
        with open(command_file, 'r') as c:
            for row in c:
                print(row, end = " ")

# header
print(f"# {info.name}\n")
print(f"{info.description}\n")

# overview
print("## Overview\n")
# generate docs/summary.png
# print("![Summary dot plot](./docs/summary.png)\n")

# dependencies
print("## Dependencies\n")
for dep in info.dependencies:
    print(f"* [{' '.join(dep['name'].split('/'))}]({dep['url']})")
print('\n')

# usage
print("## Usage\n")
print("### Cromwell")
print("```")
print(f"java -jar cromwell.jar run {info.filename} --inputs inputs.json")
print("```\n")

print("### Inputs\n")

# required
print("#### Required workflow parameters:")
print("Parameter|Value|Description")
print("---|---|---")
for param in info.required_inputs:
    print(f"`{param.name}`|{param.wdl_type}|{param.description}")
for param in info.task_inputs:
    if param.optional == False and param.default == "None":
        print(f"`{param.name}`|{param.wdl_type}|{param.description}")
print('\n')

# optional
print("#### Optional workflow parameters:")
print("Parameter|Value|Default|Description")
print("---|---|---|---")
for param in info.optional_inputs:
    print(f"`{param.name}`|{param.wdl_type}|{param.default}|{param.description}")
print('\n')

# task optional
print("#### Optional task parameters:")
print("Parameter|Value|Default|Description")
print("---|---|---|---")
for param in info.task_inputs:
    if param.optional == True or param.default != 'None':
        print(f"`{param.name}`|{param.wdl_type}|{param.default}|{param.description}")
print('\n')

# outputs
print("### Outputs\n")
print("Output | Type | Description | Labels")
print("---|---|---|---")
for output in info.outputs:
    label_string = os.linesep.join(f"{l[0]}: {l[1]}" for l in output.labels)
    print(f"`{output.name}`|{output.wdl_type}|{output.description}|{label_string}")
print('\n')

# check if commands file exists, if not - print out all commands from wdl and instruct to process manually
process_commands(args.input_wdl_path)

# Print Support information
print("""## Support

For support, please file an issue on the [Github project](https://github.com/oicr-gsi) or send an email to gsi@oicr.on.ca .
""")

print(f"_Generated with generate-markdown-readme (https://github.com/oicr-gsi/gsi-wdl-tools/)_")
