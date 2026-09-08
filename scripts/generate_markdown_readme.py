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

    with open(args.input_wdl_path, 'r') as w:
        wdl_content = w.read()
        my_commands = re.findall(r'<<<.*?>>>', wdl_content, re.DOTALL)

    commands_section = (
        f"## Commands\n"
        f"This section lists command(s) run by {info.name} workflow\n"
        f"\n"
        f"* Running {info.name}\n"
        f"\n"
    )
    for com in my_commands:
        com = com.replace('\r', '')
        # Replace <<< with ``` at start of captured string
        com_converted = re.sub(r'<<<', "```", com)
        # Replace >>> (possibly with leading whitespace on its line) with ``` at start of line
        com_converted = re.sub(r'\n[ \t]*>>>', "\n```", com_converted)
        com_converted = re.sub(r'^>>>', "```", com_converted)
        commands_section += com_converted + "\n"

    # Always write/overwrite commands.txt
    with open(command_file, 'w') as out_file:
        out_file.write(commands_section)
    print(f"{command_file} written.", file=sys.stderr)

    # Print to stdout (feeds README.md when stdout is redirected)
    print(commands_section)

    return dir_name, commands_section


def update_readme_with_commands(dir_name, commands_section):
    readme_file = "./README.md" if dir_name == "" else dir_name + "/README.md"
    sys.stdout.flush()

    if not os.path.isfile(readme_file):
        return

    with open(readme_file, 'r') as f:
        readme_content = f.read()

    if '## Commands' in readme_content:
        replacement = commands_section.rstrip()
        readme_content = re.sub(
            r'## Commands.*?(?=\n## |\Z)',
            lambda m: replacement,
            readme_content,
            flags=re.DOTALL
        )
    elif '## Support' in readme_content:
        readme_content = readme_content.replace('## Support', commands_section + '## Support', 1)
    else:
        readme_content += '\n' + commands_section

    with open(readme_file, 'w') as f:
        f.write(readme_content)
    print(f"{readme_file} updated with commands section.", file=sys.stderr)

# header
print(f"# {info.name}\n")

# overview
# The workflow's meta.description IS the overview text, so the heading has to be printed
# before it. Printing the description first left "## Overview" as an empty section with its
# content stranded above it.
print("## Overview\n")
print(f"{info.description}\n")
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

# Extract commands from WDL, write commands.txt, and print commands section
dir_name, commands_section = process_commands(args.input_wdl_path)

# Print Support information
print("""## Support

For support, please file an issue on the [Github project](https://github.com/oicr-gsi) or send an email to gsi@oicr.on.ca .
""")

print(f"_Generated with generate-markdown-readme (https://github.com/oicr-gsi/gsi-wdl-tools/)_")

# Insert/update commands section in README.md directly
update_readme_with_commands(dir_name, commands_section)


# The module body above is the program; this exists only as the console-script entry point,
# which runs after the import has already done the work.
def main():
    pass
