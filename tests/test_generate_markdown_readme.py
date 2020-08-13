from gsi_wdl_tools.workflow_info import *


def test_workflow_info(shared_datadir):
    info = WorkflowInfo((shared_datadir / 'workflow1.wdl').as_posix())
    assert info.filename == "workflow1.wdl"
    assert info.description == "Workflow description."
    assert info.dependencies == [
        {'name': 'tool1/1.0', 'url': 'http://url'}, {'name': 'tool2/1.0', 'url': 'http://url'}]
    assert info.required_inputs == [
        Input(
            name='myFile',
            wdl_type='File',
            optional=False,
            default='None',
            description='The input file.')]
    assert info.optional_inputs == [
        Input(
            name='optionalString',
            wdl_type='String',
            optional=True,
            default='"default"',
            description='The output file name prefix.')]
    assert info.task_inputs == [
        Input(
            name='myTask.memory',
            wdl_type='Int',
            optional=True,
            default='8',
            description='Memory to allocate to job.')]
    assert info.outputs == [
        Output(
            name='outputFile',
            wdl_type='File',
            description='Text output file')]
