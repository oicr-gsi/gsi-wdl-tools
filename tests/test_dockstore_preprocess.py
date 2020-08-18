import scripts.dockstore_preprocess as dp
import argparse
import sys
#import filecmp

def parse_inputs(args):
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("-i", "--input-wdl-path", required = True, help = "source wdl path")
    parser.add_argument("-d", "--docker-image", required = False, help = "image name and tag")
    parser.add_argument("-j", "--pull-json", required = False, help = "path to json containing which variables to pull; don't specify --pull-all at the same time")
    parser.add_argument("-o", "--output-wdl-path", required = False, help = "output wdl path")
    parser.add_argument("-t", "--tab-size", required = False, help = "number of spaces in a tab")
    parser.add_argument("-p", "--pull-all", required = False, type=bool, help = "whether to pull all variables; don't specify --pull-json at the same time")
    parser.add_argument("-s", "--dockstore", required = False, type=bool, help = "whether to activate functions for dockstore")
    parser.add_argument("-w", "--import-metas", required = False, type=bool, help = "whether to pull parameter_metas from imported subworkflows")
    return parser.parse_args(args)

def test_dockstore_preprocess(shared_datadir):
    workflow_path = (shared_datadir / 'workflow1.wdl').as_posix()
    #pull_path = (shared_datadir / 'pull_workflow1.wdl').as_posix()
    dockstore_path = (shared_datadir / 'dockstore_workflow1.wdl').as_posix()

    #print(str(workflow_path))
    #print(str(dockstore_path))

    args = ['--input-wdl-path', str(workflow_path),
            '--tab-size', '4'
            '--pull-all', 'true',
            '--dockstore', 'true',
            '--docker-image', '"g3chen/wgsPipeline:2.0"',
            '--import-metas', 'false',
            '--output-wdl-path', str(dockstore_path)]
    print("-----------direct parsing---------")
    print(parse_inputs(args))
    print("-----------passed to dockstore_preprocess--------------")
    print(dp.parse_inputs(args))    # should be the same as ^
    # print("-----------assignment-------------------")
    # parsed = vars(dp.parse_inputs(args))
    #
    # assert parsed['input_wdl_path'] == str(workflow_path)
    # assert parsed['tab_size'] == '4'
    # print("here1")
    # assert parsed['pull_all'] == 'True'
    # print("here2")
    # assert parsed['dockstore'] == 'True'
    # print("here3")
    # assert parsed['docker_image'] == 'g3chen/wgsPipeline:2.0'
    # assert parsed['import_metas'] == 'False'
    # assert parsed['output_wdl_path'] == str(dockstore_path)

    # preprocess workflow1 and put in same dir

    # compare content between fresh and old dockstore_.wdl
    #assert filecmp.cmp(@@@PULLED FILE, pull_path)
    #assert filecmp.cmp(@@@DOCKSTORE FILE, dockstore_path)
    assert 0