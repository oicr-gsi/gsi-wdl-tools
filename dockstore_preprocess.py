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
doc = WDL.load(args.input_wdl_path)     # loads the file as a WDL.Tree.Document object
has_param_meta = []                     # names of tasks or workflow that have a parameter_meta section

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
        if next_index < 0:          # exit if target not in string at all
            return -1, -1
        index1 += next_index        # jump to the next match found (one match per loop)
        valid_front = index1 == 0
        if index1 > 0:              # if there are characters in front of target
            valid_front = line[index1 - 1] in ", "  # only selected characters allowed
        index1 += len(target)       # jump to end of the found target
        valid_back = index1 == len(line)
        if index1 < len(line):      # if there are characters behind target
            valid_back = line[index1] in ":= "      # only selected characters allowed
        if valid_front and valid_back:      # exit loop when exact match found
            break
    while line[index1] in " =:":    # move forward until at start of value assignment
        index1 += 1
    if '"' in line[index1:]:        # if var assignment is a string, jump to end of string
        index2 = line[index1:].find('"') + index1 + 1
        index2 = line[index2:].find('"') + index2 + 1
        return index1, index2
    if "'" in line[index1:]:        # if var assignment is a string or char, jump to end of string or char
        index2 = line[index1:].find("'") + index1 + 1
        index2 = line[index2:].find("'") + index2 + 1
        return index1, index2
    if "{" in line[index1:]:        # if var assignment contains a set, jump to the end of the first closing bracket
                                    # @@@@@@@@ IMPROVEMENT: DON'T RETURN UNTIL EQUAL NUMBER OF '{' AS '}'
        index2 = line[index1:].find("}") + index1 + 1
        return index1, index2
    index2 = len(line)              # if expr is not a string, char, or set, work backwards from end of line
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
        if expr != "None":      # if default expr needs to be pulled
            line += '\n' + \
                    ' ' * num_spaces + 'input {\n' + \
                    ' ' * num_spaces * 2 + var_type + ' ' + var_name + ' = ' + expr + '\n' + \
                    ' ' * num_spaces + '}\n'
        else:                   # if doesn't have a default expr, make input optional
            line += '\n' + \
                    ' ' * num_spaces + 'input {\n' + \
                    ' ' * num_spaces * 2 + var_type + ' ' + var_name + '\n' + \
                    ' ' * num_spaces + '}\n'
        doc.source_lines[body.pos.line - 1] = line

    else:                   # input section exists but variable doesn't; add new variable
        var_in_inputs = False
        for input in body.inputs:       # replace existing docker var if new expr is not empty
            if var_name == input.name and expr != "None":     # only replace if match name and have a value
                line = doc.source_lines[input.pos.line - 1]
                index1, index2 = find_indices(line = line, target = var_name)
                line = line[:index1] + expr + line[index2:]
                doc.source_lines[input.pos.line - 1] = line
                var_in_inputs = True

        if not var_in_inputs:           # add new docker var
            line = doc.source_lines[body.inputs[0].pos.line - 1]
            num_spaces = len(line) - len(line.lstrip(' '))
            if expr != "None":  # if default expr needs to be pulled
                line = ' ' * num_spaces + var_type + ' ' + var_name + ' = ' + expr + '\n' + line
            else:               # if doesn't have a default expr, make input optional
                line = ' ' * num_spaces + var_type + ' ' + var_name + '\n' + line
            doc.source_lines[body.inputs[0].pos.line - 1] = line

# helper - add variable to runtime or param meta
    # body: the WDL.Tree.Workflow or WDL.Tree.Task object
    # mode: the type of insert (section, replace, or add line)
    # index: the index of the source line to change
    # insert: what to replace the value with
    # target: the runtime variable name
    # section: whether it's a runtime or parameter_meta block
def var_to_runtime_or_param(body, mode, index, insert, target = "docker", section = "runtime"):
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
        var_to_runtime_or_param(
            body = task,
            mode = "section",
            index = task.pos.line if not task.outputs else task.outputs[0].pos.line - 2,
            target = target,
            insert = '"~{docker}"',
            section = "runtime")
    else:
        if target in task.runtime.keys():
            var_to_runtime_or_param(
                body = task,
                mode = "replace",
                index = task.runtime[target].pos.line - 1,
                target = target,
                insert = '"~{docker}"')
        else:
            var_to_runtime_or_param(
                body = task,
                mode = "add line",
                index = task.runtime[list(task.runtime.keys())[0]].pos.line - 1,
                target = target,
                insert = '"~{docker}"')

# helper - finding and updating parameter_metas
    # body: the task or workflow object
    # target: the target variable
    # description: the variable's meta description
def var_parameter_meta(body, target, description):
    if not body.parameter_meta and str(body.name) not in has_param_meta:    # need to add the entire section
        has_param_meta.append(str(body.name))                               # prevents adding again
        var_to_runtime_or_param(
            body=body,
            mode="section",
            index=body.pos.line if not body.outputs else body.outputs[0].pos.line - 2,
            target=target,
            insert=description,
            section="parameter_meta")
    else:
        indicator = ("workflow " if isinstance(body, WDL.Tree.Workflow) else "task ") + str(body.name)
        pos = 0
        for line in doc.source_lines:
            # indicator should match one and only one line
            # and line should not be a comment
            if indicator in line and (line.find('#') < 0 or line.find(indicator) < line.find('#')):
                break  # stop searching
            pos += 1  # if not found, increase index
        while doc.source_lines[pos].find("parameter_meta") < 0:  # find parameter_meta within that body section
            pos += 1  # tested
        if target in body.parameter_meta.keys():  # if replace existing description
            print("replacing existing description for " + target)
            index1, index2 = find_indices(line=doc.source_lines[pos], target=target)
            while index1 < 0 or index2 < 0:  # increment pos until at the line exactly containing target
                pos += 1  # knows that it's in the section somewhere because in keys
                index1, index2 = find_indices(line=doc.source_lines[pos], target=target)
            print("exact variable in line: /// " + doc.source_lines[pos])
            var_to_runtime_or_param(
                body=body,
                mode="replace",
                index=pos,
                target=target,
                insert='"Docker container to run the workflow in"')
        else:  # if add new description in front of the first description in meta
            print("adding new description for " + target)
            print("insert in front of line: /// " + doc.source_lines[pos + 1])
            var_to_runtime_or_param(
                body=body,
                mode="add line",
                index=pos + 1,
                target=target,
                insert='"Docker container to run the workflow in"')

# caller - add docker to every task and workflow explicitly
def docker_runtime():
    # exit if no image provided
    if not args.docker_image:
        return
    # add image to workflow inputs
    var_to_workflow_or_task_inputs(body = doc.workflow, var_type="String", var_name="docker", expr = args.docker_image)
    # var_param_meta(doc.workflow, target = "docker", description = '""')        # not used: miniWDL doesn't provide parameter_meta line pos
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
        # var_param_meta(task, target = "docker", description = '""')        # not used: miniWDL doesn't provide parameter_meta line pos

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
                    var_type = str(input.type)
                    expr = str(input.expr)
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

# helper - tests whether a var's default expr involves calling another variable
    # expr: the variable expression to evaluate
def var_gets(expr):
    if isinstance(expr, WDL.Expr.Get):
        return True
    tree = [expr]
    while tree:     # while goes deeper
        item = tree[0]      # pop the first item
        tree = tree[1:]
        if isinstance(item, WDL.Expr.Get):
            return True
        if isinstance(item, WDL.Expr.Apply):
            tree.extend(expr.arguments)
    return False    # couldn't find and Get in the tree

# caller - pull all task variables to the workflow that calls them
def pull_to_root_all():
    if args.pull_json or not args.pull_all:     # only activate if pull_all is the only input
        return
    call_list = find_calls()                    # get the list of all calls
    for item in doc.workflow.available_inputs or []:
        sep_index = item.name.find('.')
        if sep_index < 0:                       # if variable is already workflow-level (var instead of task.var)
            continue                            # skip to the next variable
        call_name = item.name[:sep_index]       # call name may be different from task name
        input = item.value
        if var_gets(input.expr):                # if variable refers to another variable
            continue                            # skip pulling it
        extended_name = call_name + "_" + str(input.name)
        var_type = str(input.type)
        expr = str(input.expr)
        var_to_workflow_or_task_inputs(body=doc.workflow, var_type = var_type, var_name=extended_name, expr = expr)
        call = [call for call in call_list if str(call_name) == str(call.name)][0]   # call names are unique, so only one call matches

        # get the original taskName throught the call object's call.callee_name or something like that
        # get the task object (maybe can get task object directly from the call)
        # get the old parameter_meta description from the task object
        # pass the new variable name (extended_name) and old parameter_meta to another function, which adds it to workflow parameter_meta

        # know that input is not in the call inputs already (else wouldn't be part of available_inputs)
        line = doc.source_lines[call.pos.line - 1]
        if '{' in line and '}' not in line:
            var_to_call_inputs_multiline(call = call, task_var_name=str(input.name), workflow_var_name=extended_name)
        else:
            var_to_call_inputs_single_line(call = call, task_var_name=str(input.name), workflow_var_name=extended_name)

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

def test():
    var_parameter_meta(body = doc.workflow, target = "task2_var1", description = "new description for task2_var1")  # add new line
    var_parameter_meta(body = doc.tasks[1], target = "var1", description = "new meta section + var1 description")   # add new section
    var_parameter_meta(body = doc.tasks[1], target = "var1", description = "replacement var1 description")          # replace description
    var_parameter_meta(body = doc.tasks[1], target = "var2", description = "add new var2 before var1")              # replace description

tabs_to_spaces()                            # convert tabs to spaces
#pull_to_root()                              # pull json-specified task variables to the workflow that calls them
#pull_to_root_all()                          # pull all task variables to the workflow that calls them
    # var_gets()                                # tests whether a var's default expr involves calling another variable
    # var_parameter_meta()                      # finding and updating parameter_metas
#if args.dockstore:
#    source_modules()                        # add source; module if "modules" var exists, else don't
#    docker_runtime()                        # applies the below functions in the appropriate places
            # find_indices(line, target)        # find start and end of variable's assignment
            # find_calls()                      # find all nested calls in a workflow
            # var_to_call_inputs_multiline()    # add or convert docker for multi-line call
            # var_to_call_inputs_single_line()  # add or convert docker for single-line call
        # var_to_workflow_or_task_inputs()      # add or convert docker for workflow or task inputs
        # docker_to_task_runtime()              # add docker to task runtime or replace existing val
            # var_to_runtime_or_param()         # add variable to runtime or param meta
test()
write_out()                                 # write out to a new wdl file
