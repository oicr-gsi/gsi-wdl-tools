import subprocess

def test_dockstore_preprocess(shared_datadir):
    workflow_path = shared_datadir + "/workflow1.wdl"
    stdout, stderr = subprocess.Popen(['ls',  '-l', workflow_path]).communicate()
    #eval "python3 $preprocess --input-wdl-path $file $args";
    assert 0
