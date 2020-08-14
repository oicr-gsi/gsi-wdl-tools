import os

def test_dockstore_preprocess(shared_datadir):
    os.system("ls -l " + shared_datadir + "/workflow1.wdl")
    #eval "python3 $preprocess --input-wdl-path $file $args";
    assert 0
