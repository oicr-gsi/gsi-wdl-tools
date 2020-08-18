import scripts.dockstore_preprocess as dp
import argparse
import sys
import filecmp

def test_dockstore_preprocess(shared_datadir):
    workflow_path = (shared_datadir / 'workflow1.wdl').as_posix()
    pull_path = (shared_datadir / 'gen_pull_workflow1.wdl').as_posix()
    dockstore_path = (shared_datadir / 'gen_dockstore_workflow1.wdl').as_posix()

    args_d = ['--input-wdl-path', str(workflow_path),
              '--tab-size', '4',
              '--pull-all',
              '--dockstore',
              '--docker-image', 'g3chen/wgsPipeline:2.0',
              '--output-wdl-path', str(dockstore_path)]
    parsed = vars(dp.parse_inputs(args_d))
    assert parsed['input_wdl_path'] == str(workflow_path)
    assert parsed['tab_size'] == '4'
    assert parsed['pull_all'] == True
    assert parsed['pull_json'] == None
    assert parsed['dockstore'] == True
    assert parsed['docker_image'] == 'g3chen/wgsPipeline:2.0'
    assert parsed['import_metas'] == False
    assert parsed['output_wdl_path'] == str(dockstore_path)

    args_p = ['--input-wdl-path', str(workflow_path),
              '--tab-size', '4',
              '--pull-all',
              '--output-wdl-path', str(pull_path)]
    parsed = vars(dp.parse_inputs(args_p))
    assert parsed['input_wdl_path'] == str(workflow_path)
    assert parsed['tab_size'] == '4'
    assert parsed['pull_all'] == True
    assert parsed['pull_json'] == None
    assert parsed['dockstore'] == False
    assert parsed['docker_image'] == None
    assert parsed['import_metas'] == False
    assert parsed['output_wdl_path'] == str(pull_path)

    dp.main(args_d)     # generate dockstore_WDL
    dp.main(args_p)     # generate pull_WDL

    assert filecmp.cmp((shared_datadir / 'dockstore_workflow1.wdl').as_posix(), dockstore_path)
    assert filecmp.cmp((shared_datadir / 'pull_workflow1.wdl').as_posix(), pull_path)