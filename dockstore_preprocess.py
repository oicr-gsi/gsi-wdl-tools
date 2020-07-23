#!/usr/bin/env python3

import argparse
import re
import WDL
import json

parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument("-w", "--input-wdl-path", required = True, help = "source wdl path")
parser.add_argument("-i", "--docker-image", required = False, help = "image name and tag")
parser.add_argument("-j", "--pull-json", required = False, help = "path to json containing which variables to pull; don't specify --pull-all at the same time")
parser.add_argument("-p", "--pull-all", required = False, type=bool, help = "whether to pull all variables; don't specify --pull-json at the same time")
parser.add_argument("-d", "--dockstore", required = False, type=bool, help = "whether to activate functions for dockstore")

args = parser.parse_args()

# loads the file as a WDL.Tree.Document object
doc = WDL.load(args.input_wdl_path)

# caller - converts all tabs to spaces for run compatibility
    # num_spaces: number of spaces to each tab
def tabs_to_spaces(num_spaces = 8):
    for index in range(len(doc.source_lines)):
        line = doc.source_lines[index].lstrip('\t')
        num_tabs = len(doc.source_lines[index]) - len(line)
        doc.source_lines[index] = " " * num_spaces * num_tabs + line

# helper - find index1 and index2 around a keyword that exists somewhere in a line
    # line: the string that holds the keyword
    # target: the keyword in the line
    # index1: the start of the keyword
    # index2: the end of the keyword
def find_indices(line, target):
    index1 = 0
    valid_front, valid_back = False, False
    while True:
        next_index = line[index1:].find(target)
        if next_index < 0:          # exit if target not in string
            return -1, -1
        index1 += next_index        # jump to the next match found

        valid_front = index1 == 0
        if index1 > 0:              # if there are characters in front of target
            valid_front = line[index1 - 1] in ", "  # only selected characters allowed
        index1 += len(target)       # jump to end of the found target
        valid_back = index1 == len(line)
        if index1 < len(line):      # if there are characters behind target
            valid_back = line[index1] in ":= "      # only selected characters allowed
        if valid_front and valid_back:
            break
    while line[index1] in " =:":    # move forward until at start of value assignment
        index1 += 1
    if '"' in line[index1:]:        # if var assignment is a string, ignore symbols
        index2 = line[index1:].find('"') + index1 + 1
        index2 = line[index2:].find('"') + index2 + 1
        return index1, index2
    if "'" in line[index1:]:        # if var assignment is a string or char, ignore symbols
        index2 = line[index1:].find("'") + index1 + 1
        index2 = line[index2:].find("'") + index2 + 1
        return index1, index2
    if "{" in line[index1:]:        # if var assignment contains a set, ignore brackets
        index2 = line[index1:].find("}") + index1 + 1
        return index1, index2
    index2 = len(line)
    for c in "} ,":                 # assignment ends at special characters
        index_temp = line[index1:].find(c) + index1
        index2 = index_temp if index_temp > -1 + index1 and index_temp < index2 else index2
    return index1, index2

# helper - find all nested calls within a workflow
    # call_list: list of all WDL.Tree.Call objects
def find_calls():
    call_list = []
    todo_bodies = []                        # list of scatters and conditionals to search in
    for body in doc.workflow.body:
        if isinstance(body, WDL.Tree.Call):
            call_list.append(body)
        if isinstance(body, WDL.Tree.Scatter) or isinstance(body, WDL.Tree.Conditional):
            todo_bodies.append(body)
    while todo_bodies:                      # breadth-first traversal until todos are done
        body = todo_bodies[0]
        todo_bodies = todo_bodies[1:]

        if isinstance(body, WDL.Tree.Call):
            call_list.append(body)
        if isinstance(body, WDL.Tree.Scatter) or isinstance(body, WDL.Tree.Conditional):
            todo_bodies.extend(body.body)   # add sub-content of the scatter or conditional to todo
    return call_list

# helper - add "task_var_name = workflow_var_name" to a call with multi-line inputs
    # call: the WDL.Tree.Call object
    # task_var_name: the variable name within the called task
    # workflow_var_name: the variable name within the workflow
def var_to_call_inputs_multiline(call, task_var_name = "docker", workflow_var_name = "docker"):
    # multi-line inputs will never be empty
    line_pos = call.pos.line - 1                    # line_pos at "call task {"
    if task_var_name not in call.inputs.keys():     # doesn't exist; add docker as new var
        line_pos += 1 if "input:" in doc.source_lines[line_pos + 1] else 0
        line = doc.source_lines[line_pos]           # the line containing "input:"
        next_line = doc.source_lines[line_pos + 1]
        num_spaces = len(next_line) - len(next_line.lstrip(' '))
        if num_spaces == 0:
            num_spaces = len(line) - len(line.lstrip(' ')) + 4
        if '=' in line:     # if "inputs:" and var assigment on same line, insert in-between
            index = line.find("input:") + len("input:")
            index += 1 if line[index] == ' ' else 0
            new_line = line[:index] + "\n" + " " * num_spaces + task_var_name + " = " + workflow_var_name + ",\n" + " " * num_spaces + line[index:]
            doc.source_lines[line_pos] = new_line
        else:               # go to the next line and prepend new var before assignment
            prepend = " " * num_spaces + task_var_name + " = " + workflow_var_name + ",\n"
            doc.source_lines[line_pos + 1] = prepend + next_line

    else:                   # know that keys() contains task_var_name somewhere; replace old docker var value
        while True:         # stops when line contains docker
            line_pos += 1
            line = doc.source_lines[line_pos]
            index1, index2 = find_indices(line = line, target = task_var_name)
            if index1 > -1 and index2 > -1:    # the right line is found
                line = line[:index1] + workflow_var_name + line[index2:]
                doc.source_lines[line_pos] = line
                break

# helper - add "docker = docker" to a call with a single line input section
    # call: the WDL.Tree.Call object
    # task_var_name: the variable name within the called task
    # workflow_var_name: the variable name within the workflow
def var_to_call_inputs_single_line(call, task_var_name = "docker", workflow_var_name = "docker"):
    line = doc.source_lines[call.pos.line - 1]
    if not call.inputs and "{" not in line:         # input section doesn't exist; add "input: task_var_name = workflow_var_name"
        # "{" not in line is for preprocess-added input sections not yet recognized by WDL; prevents duplicate additions
        line += " { input: " + task_var_name + " = " + workflow_var_name + " }"

    elif task_var_name not in call.inputs.keys():   # input not empty but no docker var; add it
        index = line.rfind('}')
        index -= (line[index - 1] == ' ')
        line = line[:index] + ", " + task_var_name + " = " + workflow_var_name + line[index:]

    else:                                           # input section exists and keys contain task_var_name; find the right line
        index1, index2 = find_indices(line = line, target = task_var_name)
        line = line[:index1] + workflow_var_name + line[index2:]

    doc.source_lines[call.pos.line - 1] = line

# helper - add String docker to workflow inputs
    # body: either a WDL.Tree.Workflow or WDL.Tree.Task object
    # var_type: the type of the variable
    # var_name: the name of the variable
    # expr: the value assigned to the variable
    # num_spaces: the indentation for adding a new inputs block
def var_to_workflow_or_task_inputs(body, var_type, var_name, expr, num_spaces = 4):    # where body is a workflow or task
    if not body.inputs:     # no input section; add new section
        line = doc.source_lines[body.pos.line - 1]
        line += '\n' + \
                ' ' * num_spaces + 'input {\n' + \
                ' ' * num_spaces * 2 + var_type + ' ' + var_name + (' = "' + expr + '"') * (expr != "None") + '\n' + \
                ' ' * num_spaces + '}\n'
        doc.source_lines[body.pos.line - 1] = line

    else:                   # input section exists but variable doesn't; add new variable
        docker_in_inputs = False
        for input in body.inputs:           # replace existing docker var if new expr is not empty
            if var_name == input.name and expr != "None":      # only replace if match name exactly
                line = doc.source_lines[input.pos.line - 1]
                index1, index2 = find_indices(line = line, target = var_name)
                line = line[:index1] + '"' + expr + '"' + line[index2:]
                doc.source_lines[input.pos.line - 1] = line
                docker_in_inputs = True

        if not docker_in_inputs:            # add new docker var
            line = doc.source_lines[body.inputs[0].pos.line - 1]
            num_spaces = len(line) - len(line.lstrip(' '))
            line = ' ' * num_spaces + var_type + ' ' + var_name + (' = "' + expr + '"') * (expr != "None") + '\n' + line
            doc.source_lines[body.inputs[0].pos.line - 1] = line

# helper - add docker to runtime or param meta
    # body: the WDL.Tree.Workflow or WDL.Tree.Task object
    # mode: the type of insert (section, replace, or add line)
    # index: the index of the source line to change
    # insert: what to replace the value with
    # target: the runtime variable name
    # section: whether it's a runtime or parameter_meta block
def docker_to_task_or_param(body, mode, index, insert, target = "docker", section = "runtime"):
    if mode == "section":
        line = doc.source_lines[index]
        num_spaces = len(line) - len(line.lstrip(' '))
        line = ' ' * num_spaces + section + ' {\n' + \
               ' ' * num_spaces * 2 + target + ': ' + insert + '\n' + \
               ' ' * num_spaces + '}\n\n' + line
        doc.source_lines[index] = line

    if mode == "replace":
        line = doc.source_lines[index]
        index1, index2 = find_indices(line = line, target = (target + ":"))
        line = line[:index1] + insert + line[index2:]
        doc.source_lines[index] = line

    if mode == "add line":
        line = doc.source_lines[index]
        num_spaces = len(line) - len(line.lstrip(' '))
        line = ' ' * num_spaces + target + ': ' + insert + '\n' + line
        doc.source_lines[index] = line

# helper - add docker to task runtime or replace existing var
    # task: the WDL.Tree.Task object
    # target: the runtime variable name
def docker_to_task_runtime(task, target = "docker"):
    if not task.runtime:
        docker_to_task_or_param(
            body = task,
            mode = "section",
            index = task.pos.line if not task.outputs else task.outputs[0].pos.line - 2,
            target = target,
            insert = '"~{docker}"',
            section = "runtime")

    else:
        if target in task.runtime.keys():
            docker_to_task_or_param(
                body = task,
                mode = "replace",
                index = task.runtime[target].pos.line - 1,
                target = target,
                insert = '"~{docker}"')

        else:
            docker_to_task_or_param(
                body = task,
                mode = "add line",
                index = task.runtime[list(task.runtime.keys())[0]].pos.line - 1,
                target = target,
                insert = '"~{docker}"')

# helper - add docker parameter meta to workflow or task
# not used: can't find .pos of type str
    # body: the WDL.Tree.Workflow or WDL.Tree.Task object
    # target: the parameter_meta variable name
def docker_param_meta(body, target = "docker"):
    if not body.parameter_meta:
        docker_to_task_or_param(
            body = body,
            mode = "section",
            index = body.pos.line if not body.outputs else body.outputs[0].pos.line - 2,
            target = "docker",
            insert = '"Docker container to run the workflow in"',
            section = "parameter_meta")

    else:
        if target in body.parameter_meta.keys():
            docker_to_task_or_param(
                body = body,
                mode = "replace",
                index = body.parameter_meta[target].pos.line - 1,
                target = target,
                insert = '"Docker container to run the workflow in"')

        else:
            docker_to_task_or_param(
                body = body,
                mode = "add line",
                index = body.parameter_meta[list(body.parameter_meta.keys())[0]].pos.line - 1,
                target = target,
                insert = '"Docker container to run the workflow in"')

# caller - add docker to every task and workflow explicitly
def docker_runtime():
    # exit if no image provided
    if not args.docker_image:
        return
    # add image to workflow inputs
    var_to_workflow_or_task_inputs(body = doc.workflow, var_type="String", var_name="docker", expr = args.docker_image)
    # docker_param_meta(doc.workflow, target = "docker")    # add docker parameter meta to workflow
    # add image to all task calls
    call_list = find_calls()
    for call in call_list:
        line = doc.source_lines[call.pos.line - 1]
        if '{' in line and '}' not in line:
            var_to_call_inputs_multiline(call = call, task_var_name="docker", workflow_var_name="docker")
        else:
            var_to_call_inputs_single_line(call = call, task_var_name="docker", workflow_var_name="docker")
    # add image to all task inputs and runtime
    for task in doc.tasks:
        var_to_workflow_or_task_inputs(body = task, var_type="String", var_name="docker", expr = args.docker_image)
        docker_to_task_runtime(task, target = "docker")
        # docker_param_meta(task, target = "docker")        # add docker parameter meta to tasks

# caller - pull json-specified task variables to the workflow that calls them
def pull_to_root():
    # exit if no json file provided
    if args.pull_all or not args.pull_json:     # only activate if pull_json is the only input
        return
    call_list = find_calls()    # get the list of all calls
    # read from pull_json for "task": ["var1", "var2"]
    # note: if task or var name doesn't exist, then gets ignored
    with open(args.pull_json) as f:
        pull = json.load(f)
    for task_name in pull.keys():
        task = [task_obj for task_obj in doc.tasks if task_obj.name == task_name]
        if len(task) == 0:      # if no corresponding task found
            continue            # look at the next task_name in pull
        task = task[0]          # else set task as the found Task object
        relevant_calls = [call for call in call_list if task_name == call.callee.name] # all calls referencing the task
        for var in pull[task_name]:             # iterate through list of variables to pull for that task
            extended_name = task_name + '_' + var
            for input in task.inputs:
                if input.name == var:           # if pulled variable exists
                    var_type = str(input.type).strip('"')
                    expr = str(input.expr).strip('"')
                    # add the var and default value to workflow inputs
                    var_to_workflow_or_task_inputs(body=doc.workflow, var_type=var_type, var_name=extended_name, expr = expr)
                    break
            for call in relevant_calls:
                if var in call.inputs.keys():   # skip the call if var in inputs already
                    continue
                line = doc.source_lines[call.pos.line - 1]
                if '{' in line and '}' not in line:
                    var_to_call_inputs_multiline(call = call, task_var_name=var, workflow_var_name=extended_name)
                else:
                    var_to_call_inputs_single_line(call = call, task_var_name=var, workflow_var_name=extended_name)

# caller - pull all task variables to the workflow that calls them
def pull_to_root_all():
    if args.pull_json or not args.pull_all:     # only activate if pull_all is the only input
        return
    call_list = find_calls()                    # get the list of all calls
    for task in doc.tasks:                      # for each task, find relevant_calls
        relevant_calls = [call for call in call_list if task.name in call.callee.name]
        for input in task.inputs:
            extended_name = task.name + '_' + input.name
            var_type = str(input.type).strip('"')
            expr = str(input.expr).strip('"')
            var_to_workflow_or_task_inputs(body=doc.workflow, var_type=var_type, var_name=extended_name, expr=expr)
            for call in relevant_calls:
                if input.name in call.inputs.keys():    # skip the call if var in inputs already
                    continue
                line = doc.source_lines[call.pos.line - 1]
                if '{' in line and '}' not in line:
                    var_to_call_inputs_multiline(call=call, task_var_name=input.name, workflow_var_name=extended_name)
                else:
                    var_to_call_inputs_single_line(call=call, task_var_name=input.name, workflow_var_name=extended_name)

# caller - source .bashrc and load required modules for each task
def source_modules():
    for task in doc.tasks or []:
        for input in task.inputs or []:
            index = doc.source_lines[input.pos.line - 1].find("String modules")
            if index > -1:  # if the task does use modules
                pos = task.command.pos.line
                num_spaces = len(doc.source_lines[pos]) - len(doc.source_lines[pos].lstrip(' '))
                prepend = ' ' * num_spaces + 'source /home/ubuntu/.bashrc \n' + ' ' * num_spaces + '~{"module load " + modules + " || exit 20; "} \n\n'
                doc.source_lines[pos] = prepend + doc.source_lines[pos]

# caller - final outputs to stdout or a file with modified name
def write_out():
    name_index = args.input_wdl_path.rfind('/')
    prepend = "dockstore_" if args.dockstore else "pull_"
    output_path = args.input_wdl_path[:name_index + 1] + prepend + args.input_wdl_path[name_index + 1:]
    with open(output_path, "w") as output_file:
        output_file.write("\n".join(doc.source_lines))

tabs_to_spaces()                            # convert tabs to spaces
pull_to_root()                              # pull json-specified task variables to the workflow that calls them
pull_to_root_all()                          # pull all task variables to the workflow that calls them
if args.dockstore:
    source_modules()                        # add source; module if "modules" var exists, else don't
    docker_runtime()                        # applies the below functions in the appropriate places
            # find_indices(line, target)        # find start and end of variable's assignment
            # find_calls()                      # find all nested calls in a workflow
            # var_to_call_inputs_multiline()    # add or convert docker for multi-line call
            # var_to_call_inputs_single_line()  # add or convert docker for single-line call
        # var_to_workflow_or_task_inputs()      # add or convert docker for workflow or task inputs
        # docker_to_task_runtime()              # add docker to task runtime or replace existing val
            # docker_to_task_or_param()         # given a mode, inserts new value after the target
        # docker_param_meta()                   # not used: can't find .pos of param string
write_out()                                 # write out to a new wdl file
