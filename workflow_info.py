import os

import WDL


class Output:

    def __init__(self, name, wdl_type, description):
        self.name = name
        self.wdl_type = wdl_type
        self.description = description


class Input:

    def __init__(self, name, wdl_type, optional, default, description):
        self.name = name
        self.wdl_type = wdl_type
        self.optional = optional
        self.default = default
        self.description = description


class WorkflowInfo:

    def __init__(self, path):
        doc = WDL.load(path)
        self.name = doc.workflow.name
        self.description = doc.workflow.meta['description']
        self.filename = os.path.basename(doc.pos.uri)
        (self.required_inputs, self.optional_inputs, self.task_inputs) = WorkflowInfo.get_inputs(doc)
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
            wdl_type = output.value
            if isinstance(output, str):
                description = output_descriptions.get(output)
            elif isinstance(output, WDL.Env.Binding):
                val = output_descriptions.get(output.name)
                if val is not None:
                    description = val
                else:
                    output_file_name = output.info.expr.expr.name
                    description = output_descriptions.get(output_file_name)
            else:
                raise Exception('Unsupported input type')
            outputs.append(Output(name=name, wdl_type=wdl_type, description=description))
        return outputs

    @staticmethod
    def get_inputs(doc):
        param_descriptions = doc.workflow.parameter_meta
        for task in doc.tasks:
            param_descriptions.update(task.parameter_meta)

        required_params = []
        optional_params = []
        task_params = []
        for param in doc.workflow.available_inputs:
            name = param.name
            wdl_type = param.value.type
            optional = param.value.type.optional
            default = param.value.expr or ''
            description = param_descriptions.get(name, '')
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
