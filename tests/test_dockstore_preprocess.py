import subprocess as sb

def test_dockstore_preprocess(shared_datadir):
    workflow_path = (shared_datadir / 'workflow1.wdl').as_posix()
    sb.Popen(['ls',  '-l', workflow_path])
    sb.Popen(['pwd'])

    #eval "python3 $preprocess --input-wdl-path $file $args";
    assert 0
