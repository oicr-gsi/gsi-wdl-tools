import subprocess as sb

def test_dockstore_preprocess(shared_datadir):
    workflow_path = (shared_datadir / 'workflow1.wdl').as_posix()
    #sb.Popen(['ls',  '-l', workflow_path])
    sb.Popen(['python3', '$PWD/scripts/dockstore_preprocess.py', '--input-wdl-path', workflow_path, '--pull-all', 'true', '--dockstore', 'true'])
    assert 0
