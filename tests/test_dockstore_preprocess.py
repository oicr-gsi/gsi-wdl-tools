import scripts.dockstore_preprocess as dp
#import filecmp

def test_dockstore_preprocess(shared_datadir):
    workflow_path = (shared_datadir / 'workflow1.wdl').as_posix()
    #pull_path = (shared_datadir / 'pull_workflow1.wdl').as_posix()
    dockstore_path = (shared_datadir / 'dockstore_workflow1.wdl').as_posix()

    #print(str(workflow_path))
    #print(str(dockstore_path))

    args = ['--input-wdl-path', str(workflow_path),
            '--tab-size', '4'
            '--pull-all', 'True',
            '--dockstore', 'True',
            '--docker-image', '"g3chen/wgsPipeline:2.0"',
            '--import-metas', 'False',
            '--output-wdl-path', str(dockstore_path)]
    parsed = vars(dp.parse_inputs(args))

    assert parsed['input_wdl_path'] == str(workflow_path)
    assert parsed['tab_size'] == '4'
    print("here1")
    assert parsed['pull_all'] == 'True'
    print("here2")
    assert parsed['dockstore'] == 'True'
    print("here3")
    assert parsed['docker_image'] == 'g3chen/wgsPipeline:2.0'
    assert parsed['import_metas'] == 'False'
    assert parsed['output_wdl_path'] == str(dockstore_path)

    # preprocess workflow1 and put in same dir

    # compare content between fresh and old dockstore_.wdl
    #assert filecmp.cmp(@@@PULLED FILE, pull_path)
    #assert filecmp.cmp(@@@DOCKSTORE FILE, dockstore_path)