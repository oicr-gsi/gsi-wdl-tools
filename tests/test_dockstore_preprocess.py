import subprocess
import WDL
from scripts.dockstore_preprocess import *

doc = WDL.load(args.input_wdl_path)

def test_dockstore_preprocess(shared_datadir):
    workflow_path = (shared_datadir / 'workflow1.wdl').as_posix()
    stdout, stderr = subprocess.Popen(['ls',  '-l', workflow_path]).communicate()
    #eval "python3 $preprocess --input-wdl-path $file $args";
    assert 0
