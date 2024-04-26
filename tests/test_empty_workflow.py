from gsi_wdl_tools.workflow_info import *


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
