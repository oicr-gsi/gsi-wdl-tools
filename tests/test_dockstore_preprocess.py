import subprocess as sb

# def test_dockstore_preprocess(shared_datadir):
#     workflow_path = (shared_datadir / 'workflow1.wdl').as_posix()
#     #sb.Popen(['ls',  '-l', workflow_path])
#     sb.Popen(['cd', 'scripts/'])
#     sb.Popen(['pwd'])
#     sb.Popen(['python3', 'dockstore_preprocess.py', '--input-wdl-path', workflow_path, '--pull-all', 'true', '--dockstore', 'true'])
#     assert 0

from diagnose import *

def test_diagnose(shared_datadir):
    print("import successful")
    assert 0