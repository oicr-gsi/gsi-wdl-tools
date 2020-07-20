#!/usr/bin/env python3

import argparse
import re
import WDL
import json

parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument("--input-wdl-path", required=True)
parser.add_argument("--docker-image", required=False)
parser.add_argument("--pull-json", required=False)
args = parser.parse_args()

doc = WDL.load(args.input_wdl_path)     # loads the entire document

# converts all tabs to spaces for compatibility
def tabs_to_spaces(num_spaces = 8):     # what about multiple tabs, or tab is in a string?
    for index in range(len(doc.source_lines)):
        line = doc.source_lines[index].lstrip('\t')     # strips leading tabs
        num_tabs = len(doc.source_lines[index]) - len(line)     # how many tabs were stripped away
        doc.source_lines[index] = " " * num_spaces * num_tabs + line

# find index1 and index2 around a keyword that exists somewhere in a line
def find_indices(line, target):
    index1 = 0
    valid_front, valid_back = False, False
    while True:
        next_index = line[index1:].find(target)
        if next_index < 0:  # target not in string
            return -1, -1
        index1 += next_index  # jump to head of found target

        valid_front = index1 == 0
        if index1 > 0:  # if there are characters in front of target
            valid_front = line[index1 - 1] in ", "  # other characters like [a-z][0-9][_$#*] etc. not allowed
        index1 += len(target)  # jump to tail of found target: doesn't repeatedly find the same word
        valid_back = index1 == len(line)
        if index1 < len(line):  # if there are characters behind target
            valid_back = line[index1] in ":= "
        if valid_front and valid_back:
            break

    while line[index1] in " =:":  # move forward until at start of assignment
        index1 += 1
    if '"' in line[index1:]:  # if var assignment is a string, ignore symbols
        index2 = line[index1:].find('"') + index1 + 1
        index2 = line[index2:].find('"') + index2 + 1
        return index1, index2
    if "'" in line[index1:]:  # if var assignment is a string, ignore symbols
        index2 = line[index1:].find("'") + index1 + 1
        index2 = line[index2:].find("'") + index2 + 1
        return index1, index2
    if "{" in line[index1:]:  # if var assignment contains a set, ignore brackets
        index2 = line[index1:].find("}") + index1 + 1
        return index1, index2
    index2 = len(line)  # initialize at end of line
    for c in "} ,":  # value ends in ,/ /} whichever is smallest but must > -1
        index_temp = line[index1:].find(c) + index1
        index2 = index_temp if index_temp > -1 + index1 and index_temp < index2 else index2
    return index1, index2

# find all nested calls within a workflow
def find_calls():
    # change inputs for calls within scatters and conditionals
    call_list = []      # list of call objects found
    todo_bodies = []     # list of scatters and conditions to search in
    for body in doc.workflow.body:      # tested - able to delegate multi- and single insert
        if isinstance(body, WDL.Tree.Call):
            call_list.append(body)
        if isinstance(body, WDL.Tree.Scatter) or isinstance(body, WDL.Tree.Conditional):
            todo_bodies.append(body)

    while todo_bodies:
        body = todo_bodies[0]           # pop the first element
        todo_bodies = todo_bodies[1:]

        if isinstance(body, WDL.Tree.Call):
            call_list.append(body)
        if isinstance(body, WDL.Tree.Scatter) or isinstance(body, WDL.Tree.Conditional):
            todo_bodies.extend(body.body)       # add sub-content of the scatter or conditional to todo

    return call_list

# helper function: add "docker = docker" to a call with a multi-line input section
def var_to_call_inputs_multiline(call, task_var_name = "docker", workflow_var_name = "docker"):
    # either multi-line has docker or hasn't, but will not be empty (that's single line)
    line_pos = call.pos.line - 1
    if task_var_name not in call.inputs.keys():  # add docker as new var
        line_pos += 2 if "input:" in doc.source_lines[line_pos + 1] else 1   # first line with input vars
        line = doc.source_lines[line_pos]
        num_spaces = len(line) - len(line.lstrip(' '))
        prepend = " " * num_spaces + task_var_name + " = " + workflow_var_name + ",\n"
        doc.source_lines[line_pos] = prepend + line

    # line_pos at "call task {"
    else:   # replace old docker var value; know that keys() contains task_var_name somewhere
        while True:     # stops when line contains docker
            line_pos += 1   # next line
            line = doc.source_lines[line_pos]
            index1, index2 = find_indices(line = line, target = task_var_name)
            if index1 > -1 and index2 > -1:    # the right line is found
                line = line[:index1] + workflow_var_name + line[index2:]
                doc.source_lines[line_pos] = line
                break

# helper function: add "docker = docker" to a call with a single line input section
def var_to_call_inputs_single_line(call, task_var_name = "docker", workflow_var_name = "docker"):
    line = doc.source_lines[call.pos.line - 1]
    if not call.inputs:     # if input section empty, add "input: docker"
        index = len(line) - 1                   # if call doesn't have {}, set index to end of line
        line += " { input: " + task_var_name + " = " + workflow_var_name + " }"

    elif task_var_name not in call.inputs.keys():    # if input not empty but no docker var: add it
        index = line.rfind('}')
        index -= (line[index - 1] == ' ')       # move one back if " }"
        line = line[:index] + ", " + task_var_name + " = " + workflow_var_name + line[index:]

    else:   # knows that inputs section exists and keys contain task_var_name, just have to find it
        index1, index2 = find_indices(line = line, target = task_var_name)
        line = line[:index1] + workflow_var_name + line[index2:]

    doc.source_lines[call.pos.line - 1] = line

# add String docker to workflow inputs
def var_to_workflow_or_task_inputs(body, var_type = "String", var_name = "docker", expr = args.docker_image, num_spaces = 4):    # where body is a workflow or task
    if not body.inputs:
        line = doc.source_lines[body.pos.line - 1]
        line += '\n' + \
                ' ' * num_spaces + 'input {\n' + \
                ' ' * num_spaces * 2 + var_type + ' ' + var_name + ' = "' + expr + '"\n' + \
                ' ' * num_spaces + '}\n'
        doc.source_lines[body.pos.line - 1] = line

    else:   # if inputs section does exist
        docker_in_inputs = False
        for input in body.inputs:           # replace existing docker var
            if var_name == input.name:      # only replace if match name exactly
                line = doc.source_lines[input.pos.line - 1]
                index1, index2 = find_indices(line = line, target = var_name)
                line = line[:index1] + '"' + expr + '"' + line[index2:]
                doc.source_lines[input.pos.line - 1] = line
                docker_in_inputs = True

        if not docker_in_inputs:            # add new docker var
            line = doc.source_lines[body.inputs[0].pos.line - 1]
            num_spaces = len(line) - len(line.lstrip(' '))
            line = ' ' * num_spaces + var_type + ' ' + var_name + ' = "' + expr + '"\n' + line
            doc.source_lines[body.inputs[0].pos.line - 1] = line

# add docker to runtime or param meta
    # body - the task or workflow
    # mode - the type of insert
    # index - the index of the source line to change
    # insert - what to replace the value with
def docker_to_task_or_param(body, mode, index, insert, target = "docker", section = "runtime"):
    if mode == "section":
        line = doc.source_lines[index]
        print(line)
        num_spaces = len(line) - len(line.lstrip(' '))
        line = ' ' * num_spaces + section + ' {\n' + \
               ' ' * num_spaces * 2 + target + ': ' + insert + '\n' + \
               ' ' * num_spaces + '}\n\n' + line
        doc.source_lines[index] = line
        print(line + "\n")

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

# add docker to task runtime or replace existing var
def docker_to_task_runtime(task, target = "docker"):   # all tested
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

# add docker parameter meta to workflow or task
# not used: can't find .pos of type str
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

# add docker to every task and workflow explicitly
def docker_runtime():
    # exit if user doesn't want to add a docker image
    if not args.docker_image:
        return

    # add image to workflow inputs
    var_to_workflow_or_task_inputs(body = doc.workflow, var_type="String", var_name="docker", expr = args.docker_image)

    # add docker parameter meta to workflow
    # docker_param_meta(doc.workflow, target = "docker")

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
        # docker_param_meta(task, target = "docker")

# pull all task variables to the workflow that calls them
def pull_to_root():
    if not args.pull_json:
        return

    # get the list of all calls
    call_list = find_calls()

    # read from pull_json for "task": ["var1", "var2"]
    # note: if task or var name doesn't exist, then gets ignored
    with open(args.pull_json) as f:
        pull = json.load(f)
    for task in pull.keys():
        task_obj = (obj for obj in doc.tasks if obj.name == task)[0]     # the WDL.Tree.Task object
        relevant_calls = [call for call in call_list if task in call.callee_id] # all calls referencing the task

        for var in pull[task]:
            extended_name = task + '_' + var
            for input in task_obj.inputs:
                if input.name == var:
                    var_type = str(input.type)
                    expr = str(input.expr)
                    break       # stop looking at the next input

            # add the var and default value to workflow inputs
            var_to_workflow_or_task_inputs(body=doc.workflow, var_type=var_type, var_name=extended_name, expr = expr)

            for call in relevant_calls:
                var_to_call_inputs_multiline(call = call, task_var_name=var, workflow_var_name=extended_name)
                var_to_call_inputs_single_line(call = call, task_var_name=var, workflow_var_name=extended_name)

# source .bashrc and load required modules for each task
def source_modules():
    for task in doc.tasks or []:
        for input in task.inputs or []:
            index = doc.source_lines[input.pos.line - 1].find("String modules")
            if index > -1:  # if the task does use modules
                pos = task.command.pos.line
                num_spaces = len(doc.source_lines[pos]) - len(doc.source_lines[pos].lstrip(' '))
                prepend = ' ' * num_spaces + 'source /home/ubuntu/.bashrc \n' + ' ' * num_spaces + '~{"module load " + modules + " || exit 20; "} \n\n'
                doc.source_lines[pos] = prepend + doc.source_lines[pos]

# TEST FUNCTION
def test():
    if not args.pull_json:
        return

    # get the list of all calls
    call_list = find_calls()

    # read from pull_json for "task": ["var1", "var2"]
    # note: if task or var name doesn't exist, then gets ignored
    with open(args.pull_json) as f:
        pull = json.load(f)
    for task_name in pull.keys():
        task = [task_obj for task_obj in doc.tasks if task_obj.name == task_name][0]     # the WDL.Tree.Task object
        relevant_calls = [call for call in call_list if task_name in call.callee_id] # all calls referencing the task
        print([call.callee_id for call in relevant_calls])

        #
        # for var in pull[task]:
        #     extended_name = task + '_' + var
        #     for input in task_obj.inputs:
        #         if input.name == var:
        #             var_type = str(input.type)
        #             expr = str(input.expr)
        #             break       # stop looking at the next input
        #
        #     # add the var and default value to workflow inputs
        #     var_to_workflow_or_task_inputs(body=doc.workflow, var_type=var_type, var_name=extended_name, expr = expr)
        #
        #     for call in relevant_calls:
        #         var_to_call_inputs_multiline(call = call, task_var_name=var, workflow_var_name=extended_name)
        #         var_to_call_inputs_single_line(call = call, task_var_name=var, workflow_var_name=extended_name)

# final outputs to stdout or a file with modified name
def write_out():
    name_index = args.input_wdl_path.rfind('/')
    output_path = args.input_wdl_path[:name_index + 1] + "dockstore_" + args.input_wdl_path[name_index + 1:]
    with open(output_path, "w") as output_file:
        output_file.write("\n".join(doc.source_lines))

tabs_to_spaces()                            # tested - convert tabs to spaces
# docker_runtime()                            # tested - applies the below functions in the appropriate places
        # find_indices(line, target)        # tested -  find start and end of variable's assignment
        # find_calls()                      # tested - find all nested calls in a workflow
        # var_to_call_inputs_multiline()    # tested -  add or convert docker for multi-line call
        # var_to_call_inputs_single_line()  # tested -  add or convert docker for single-line call
    # var_to_workflow_or_task_inputs()      # tested -  add or convert docker for workflow or task inputs
    # docker_to_task_runtime()              # tested -  add docker to task runtime or replace existing val
        # docker_to_task_or_param()         # tested - given a mode, inserts new value after the target
    # docker_param_meta()                   # not used: can't find .pos of param string
# pull_to_root()
# source_modules()                            # tested - add source; module if "modules" var exists, else don't
test()
write_out()                                 # tested - write out to a new wdl file
