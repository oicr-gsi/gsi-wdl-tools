import logging
import os
from dataclasses import dataclass

import WDL

logging.basicConfig(format='%(levelname)s %(message)s')
log = logging.getLogger(__name__)


@dataclass
class Output:
    name: str
    wdl_type: str
    description: str
    vidarr_label: list[str]


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
        doc = WDL.load(path)
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
                    description = val
                else:
                    raise Exception(f"output description is missing for {name}")
            else:
                raise Exception('Unsupported input type')             
                
            vidarr_label = [] 
                       
            # Check if 'vidarr_label' exists in the output description
            if 'vidarr_label' in output_descriptions[output.name]:
                vidarr_label.append(('vidarr_label', output_descriptions[output.name]['vidarr_label']))
                # If vidarr_label exists, should convert file to file-with-labels
                if wdl_type == "File":
                    wdl_type = "Pair[File,Map[String,String]]"
                elif wdl_type == "Pair[File,Map[String,String]]":
                    # Extracting existing entries from output.info.expr.right
                    existing_entries = output.info.expr.right.items

                    # Iterate through the items
                    for key, value in existing_entries:
                        key_eval = str(key.eval(None, None))
                        value_eval = str(value.eval(None, None))          
                        vidarr_label.append((key_eval, value_eval))
            
            outputs.append(Output(name=name, wdl_type=wdl_type, description=description, vidarr_label=vidarr_label))
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
