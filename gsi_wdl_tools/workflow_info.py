import logging
import os
from dataclasses import dataclass
from typing import Tuple

import WDL

logging.basicConfig(format='%(levelname)s %(message)s')
log = logging.getLogger(__name__)


@dataclass
class Output:
    name: str
    wdl_type: str
    description: str
    labels: [Tuple[str, str]]


@dataclass
class Input:
    name: str
    wdl_type: str
    optional: bool
    default: str
    description: str


class ValidationError(Exception):
    pass


class WorkflowInfo:

    def __init__(self, path, default_parameter_description=None):
        try:
            doc = WDL.load(path)
        except (WDL.Error.MultipleValidationErrors, WDL.Error.SyntaxError, WDL.Error.ValidationError) as e:
            errors = e.exceptions if isinstance(e, WDL.Error.MultipleValidationErrors) else [e]
            error_messages = [f"Error {i + 1} at line={error.pos.line} and column={error.pos.column}:\n{error}" for i, error in enumerate(errors)]
            raise ValidationError(f"Unable to load {path} due to the following errors:\n{'\n'.join(error_messages)}") from e

        self.name = doc.workflow.name
        self.description = doc.workflow.meta['description']
        self.filename = os.path.basename(doc.pos.uri)
        (self.required_inputs, self.optional_inputs, self.task_inputs) = WorkflowInfo.get_inputs(doc, default_parameter_description)
        self.doc = doc

    @property
    def outputs(self):
        output_descriptions = {}

        # collect task output_meta
        for task in self.doc.tasks:
            task_name = task.name
            task_output_meta = task.meta.get('output_meta', {})
            for k, v in task_output_meta.items():
                output_descriptions[task_name + '.' + k] = v

        # collect workflow output_meta
        output_descriptions.update(self.doc.workflow.meta.get('output_meta', {}))

        outputs = []
        for output in self.doc.workflow.effective_outputs:
            name = output.name
            wdl_type = str(output.value)
            if isinstance(output, str):
                description = output_descriptions.get(output)
            elif isinstance(output, WDL.Env.Binding):
                val = output_descriptions.get(output.name)
                if val is not None:
                    if type(val) is dict:
                        description = val.get("description", "")
                    else:
                        description = val
                else:
                    output_file_name = str(output.info.expr)
                    description = output_descriptions.get(output_file_name)
            else:
                raise Exception('Unsupported input type')
            if not description:
                raise Exception(f"output description is missing for {name}")

            labels = []

            # Check if 'vidarr_label' exists in the output description
            # TODO: support for other labels
            if output.name in output_descriptions and 'vidarr_label' in output_descriptions[output.name]:
                labels.append(('vidarr_label', output_descriptions[output.name]['vidarr_label']))

                if wdl_type == "Pair[File,Map[String,String]]":
                    # Extracting existing entries from output.info.expr.right
                    existing_entries = output.info.expr.right.items

                    # Iterate through the items
                    for key, value in existing_entries:
                        key_eval = str(key.eval(None, None))
                        value_eval = str(value.eval(None, None))
                        labels.append((key_eval, value_eval))

            outputs.append(Output(name=name, wdl_type=wdl_type, description=description, labels=labels))
        return outputs

    @staticmethod
    def calls(element):
        for ch in element.children:
            if isinstance(ch, WDL.Call):
                yield ch
            elif isinstance(ch, WDL.WorkflowSection):
                yield from WorkflowInfo.calls(ch)

    @staticmethod
    def get_inputs(doc, default_parameter_description=None):

        # create a map of call names to task names
        # this is used for mapping an aliased call to its task
        call_to_task = {}
        for call in WorkflowInfo.calls(doc.workflow):
            if isinstance(call, WDL.Call):
                call_to_task[call.name] = call.callee.name
            elif isinstance(call, WDL.WorkflowSection):
                print(call.name)

        param_descriptions = doc.workflow.parameter_meta.copy()
        for task in doc.tasks:
            param_descriptions.update({task.name + "." + k: v for k, v in task.parameter_meta.items()})

        # get parameter_metas from imported subworkflows
        for imp in doc.imports:
            import_parameter_meta = imp.doc.workflow.parameter_meta
            param_descriptions.update({imp.doc.workflow.name + "." + k: v for k, v in import_parameter_meta.items()})
            # if imports contain task-level available_inputs, add the params for those
            for task in imp.doc.tasks:
                param_descriptions.update({imp.doc.workflow.name + "." + task.name + "." + k: v for k, v in task.parameter_meta.items()})

        required_params = []
        optional_params = []
        task_params = []
        for param in doc.workflow.available_inputs:
            name = param.name
            wdl_type = str(param.value.type)
            default = str(param.value.expr) or ''
            if param.value.expr is not None or param.value.type.optional:
                optional = True
            else:
                optional = False
            if param.value.type.optional and default != "None":
                raise ValidationError(f"Optional with default at line {param.value.pos.line}: {wdl_type} {name} = {default}")
            description = param_descriptions.get(name, '')
            if not description and len(name.split('.')) == 2:
                # this is an aliased call parameter, map call name to task name and get the task's description
                (call_name, param_name) = name.split('.')
                description = param_descriptions.get(f"{call_to_task.get(call_name, 'missing')}.{param_name}", '')
            if not description:
                if default_parameter_description is not None:
                    log.warn(f"Using default parameter meta description for missing parameter_meta {name} (line {param.value.pos.line})")
                    description = default_parameter_description
                else:
                    raise ValidationError(f"parameter_meta description is missing for {name} (line {param.value.pos.line})")
            input_param = Input(name=name, wdl_type=wdl_type, optional=optional, default=default,
                                description=description)
            if '.' not in input_param.name:
                if input_param.optional:
                    optional_params.append(input_param)
                else:
                    required_params.append(input_param)
            else:
                task_params.append(input_param)

        return required_params, optional_params, task_params

    @property
    def dependencies(self):
        return self.doc.workflow.meta.get('dependencies')
