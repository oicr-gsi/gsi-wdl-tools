import pytest

from gsi_wdl_tools.workflow_info import *

# WorkflowInfo should be the same for the following:
# workflow 1: output description in task meta output_meta
# workflow 2: output description in workflow meta output_meta
@pytest.mark.parametrize("workflow_file", ["workflow1.wdl", "workflow2.wdl"])
def test_workflow_info(shared_datadir, workflow_file):
    info = WorkflowInfo((shared_datadir / workflow_file).as_posix())
    assert info.filename == workflow_file
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
            description='Text output file',
            vidarr_label="")]


def test_empty_workflow(shared_datadir):
    info = WorkflowInfo((shared_datadir / 'empty.wdl').as_posix())
    assert info.filename == "empty.wdl"
    assert info.description == "Workflow for testing infrastructure"
    assert info.dependencies == [{'name': 'dependency_name', 'url': 'dependency_url'}]
    assert info.required_inputs == []
    assert info.optional_inputs == [
        Input(
            name='exitCode',
            wdl_type='Int',
            optional=True,
            default='0',
            description='Exit code'
        ),
        Input(
            name='n',
            wdl_type='Int',
            optional=True,
            default='10',
            description='Number of lines to log to stderr'
        )
    ]
    assert info.task_inputs == [
        Input(
            name='log.mem',
            wdl_type='Int',
            optional=True,
            default='1',
            description='Memory (in GB) to allocate to the job'
        ),
        Input(
            name='log.timeout',
            wdl_type='Int',
            optional=True,
            default='1',
            description='Maximum amount of time (in hours) the task can run for'
        )
    ]
    assert info.outputs == [
        Output(
            name='err',
            wdl_type='File',
            description="Gzipped and sorted index ...",
            vidarr_label=[('vidarr_label', 'counts')]
        )
    ]
