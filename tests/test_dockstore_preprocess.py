import subprocess

def test_dockstore_preprocess(shared_datadir):
    stdout, stderr = subprocess.Popen(['ls',  '-l', shared_datadir + '/workflow1.wdl']).communicate()
    #eval "python3 $preprocess --input-wdl-path $file $args";
    assert 0
