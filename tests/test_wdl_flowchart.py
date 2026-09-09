import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

import gsi_wdl_tools.wdl_flowchart as fc

REPO_ROOT = Path(__file__).resolve().parent.parent


def generate(wdl, outdir, **overrides):
    """Run the generator over one WDL and return the text of the .dot it wrote."""
    args = SimpleNamespace(outdir=str(outdir), svg=False, png=False, check=False,
                           expand_cases=4, hide=None, hide_file=None, show_all=False,
                           verbose=False)
    for name, value in overrides.items():
        setattr(args, name, value)
    assert fc.process(str(wdl), args)
    dots = sorted(Path(outdir).glob('*.flow.dot'))
    assert len(dots) == 1, f"expected one .dot in {outdir}, got {dots}"
    return dots[0].read_text()


def graph(wdl, **overrides):
    """Parse and resolve a WDL the way the generator does, without writing anything."""
    wf = fc.parse(str(wdl))
    fc.coalesce(wf.root)
    fc.resolve(wf)
    expand = overrides.get('expand_cases', 4)
    if expand:
        fc.expand_cases(wf, expand)
    return wf


# ------------------------------------------------------------------ nesting.wdl
#
# The fixture is built from constructs that have caused trouble: decoy call/if/scatter text
# inside both command-block styles, a scatter nested in an if, a multi-line scatter
# expression, a multi-line call input block, a dependency threaded through an intermediate
# declaration, and a call into an imported file.

@pytest.fixture
def nesting_dot(shared_datadir, tmp_path):
    return generate(shared_datadir / 'flowchart_nesting.wdl', tmp_path)


def test_nesting_counts(shared_datadir):
    wf = graph(shared_datadir / 'flowchart_nesting.wdl')
    assert wf.name == 'nesting'
    assert len(wf.nodes) == 5
    assert sum(len(n.deps) for n in wf.nodes.values()) == 3
    assert wf.unresolved == set()


def test_nesting_clusters_are_labelled(nesting_dot):
    assert 'label="if (defined(label))"' in nesting_dot
    # a scatter expression split over three source lines is joined into one label
    assert 'label="scatter (pair in zip( bams, bams))"' in nesting_dot


def test_scatter_cluster_sits_inside_the_if_cluster(nesting_dot):
    assert (nesting_dot.index('label="if (defined(label))"')
            < nesting_dot.index('label="scatter (b in bams)"'))


def test_imported_call_is_marked(nesting_dot):
    line = next(x for x in nesting_dot.splitlines()
                if x.strip().startswith('imported ['))
    assert 'diagonals' in line


def test_dependencies_are_drawn(nesting_dot):
    lines = nesting_dot.splitlines()
    # threaded through the intermediate `Array[File] shardOut` declaration
    assert '  perShard -> gather' in lines
    assert '  prepare -> imported' in lines


@pytest.mark.parametrize("decoy", ['notARealCall', 'fake', 'alsoFake'])
def test_command_block_decoys_are_not_calls(nesting_dot, decoy):
    assert decoy not in nesting_dot


def test_hidden_call_is_contracted_not_dropped(shared_datadir, tmp_path):
    dot = generate(shared_datadir / 'flowchart_nesting.wdl', tmp_path, hide=['perShard'])
    lines = dot.splitlines()
    assert '  perShard -> gather' not in lines
    # prepare -> perShard -> gather becomes prepare -> gather
    assert '  prepare -> gather' in lines
    assert 'not shown, technical detail' in dot


def test_hide_file_beside_the_wdl_is_found(shared_datadir, tmp_path):
    (shared_datadir / 'flowchart_nesting.flow.hide').write_text("# plumbing\nperShard\n")
    dot = generate(shared_datadir / 'flowchart_nesting.wdl', tmp_path)
    assert '  prepare -> gather' in dot.splitlines()


def test_show_all_overrides_the_hide_file(shared_datadir, tmp_path):
    (shared_datadir / 'flowchart_nesting.flow.hide').write_text("perShard\n")
    dot = generate(shared_datadir / 'flowchart_nesting.wdl', tmp_path, show_all=True)
    assert '  perShard -> gather' in dot.splitlines()


# -------------------------------------------------------------- named_cases.wdl
#
# A scatter over a literal list of named items is drawn as one branch per item; a scatter
# over interchangeable data shards stays a single box.

@pytest.fixture
def named_cases_dot(shared_datadir, tmp_path):
    return generate(shared_datadir / 'flowchart_named_cases.wdl', tmp_path)


def test_named_cases_become_one_branch_each(named_cases_dot):
    assert 'label="ig = tumorInputGroup"' in named_cases_dot
    assert 'label="ig = normalInputGroup"' in named_cases_dot
    assert 'annotate__tumorInputGroup [label="annotate"]' in named_cases_dot


def test_dependencies_stay_within_a_branch(named_cases_dot):
    lines = named_cases_dot.splitlines()
    assert '  annotate__tumorInputGroup -> filter__tumorInputGroup' in lines
    assert '  annotate__tumorInputGroup -> filter__normalInputGroup' not in lines
    # everything downstream fans in from every branch
    assert '  filter__normalInputGroup -> combine' in lines


def test_data_parallelism_is_not_expanded(named_cases_dot):
    assert 'label="scatter (chr in chromosomes)"' in named_cases_dot
    assert 'perChrom__chr' not in named_cases_dot


def test_expand_cases_zero_leaves_one_box(shared_datadir, tmp_path):
    dot = generate(shared_datadir / 'flowchart_named_cases.wdl', tmp_path, expand_cases=0)
    assert 'label="ig = tumorInputGroup"' not in dot


# ---------------------------------------------------------------------- --check

def test_check_accepts_a_fresh_dot(shared_datadir, tmp_path, capsys):
    wdl = shared_datadir / 'flowchart_nesting.wdl'
    generate(wdl, tmp_path)
    args = SimpleNamespace(outdir=str(tmp_path), svg=False, png=False, check=True,
                           expand_cases=4, hide=None, hide_file=None, show_all=False,
                           verbose=False)
    assert fc.process(str(wdl), args)


def test_check_rejects_a_stale_dot(shared_datadir, tmp_path):
    wdl = shared_datadir / 'flowchart_nesting.wdl'
    generate(wdl, tmp_path)
    dot = tmp_path / 'nesting.flow.dot'
    dot.write_text(dot.read_text() + "// tampered\n")
    args = SimpleNamespace(outdir=str(tmp_path), svg=False, png=False, check=True,
                           expand_cases=4, hide=None, hide_file=None, show_all=False,
                           verbose=False)
    assert not fc.process(str(wdl), args)


def test_check_rejects_a_missing_dot(shared_datadir, tmp_path):
    args = SimpleNamespace(outdir=str(tmp_path), svg=False, png=False, check=True,
                           expand_cases=4, hide=None, hide_file=None, show_all=False,
                           verbose=False)
    assert not fc.process(str(shared_datadir / 'flowchart_nesting.wdl'), args)


def test_task_only_wdl_is_skipped_not_failed(tmp_path):
    wdl = tmp_path / 'tasks.wdl'
    wdl.write_text('version 1.0\n\ntask lonely {\n  command <<< echo hi >>>\n}\n')
    args = SimpleNamespace(outdir=str(tmp_path), svg=False, png=False, check=False,
                           expand_cases=4, hide=None, hide_file=None, show_all=False,
                           verbose=False)
    assert fc.process(str(wdl), args)
    assert not list(tmp_path.glob('*.flow.dot'))


# ------------------------------------------------------------- find_flowchart

def test_find_flowchart_prefers_docs_over_the_wdl_directory(tmp_path):
    wdl = tmp_path / 'w.wdl'
    wdl.touch()
    (tmp_path / 'w1.flow.svg').touch()
    docs = tmp_path / 'docs'
    docs.mkdir()
    (docs / 'w1.flow.svg').touch()
    assert fc.find_flowchart(str(wdl), 'w1') == str(docs / 'w1.flow.svg')


def test_find_flowchart_falls_back_to_the_wdl_directory(tmp_path):
    wdl = tmp_path / 'w.wdl'
    wdl.touch()
    beside = tmp_path / 'w1.flow.svg'
    beside.touch()
    assert fc.find_flowchart(str(wdl), 'w1') == str(beside)


def test_find_flowchart_prefers_svg_to_png(tmp_path):
    wdl = tmp_path / 'w.wdl'
    wdl.touch()
    (tmp_path / 'w1.flow.png').touch()
    svg = tmp_path / 'w1.flow.svg'
    svg.touch()
    assert fc.find_flowchart(str(wdl), 'w1') == str(svg)


def test_find_flowchart_ignores_the_dot_source(tmp_path):
    wdl = tmp_path / 'w.wdl'
    wdl.touch()
    (tmp_path / 'w1.flow.dot').touch()
    assert fc.find_flowchart(str(wdl), 'w1') is None


def test_find_flowchart_returns_none_when_there_is_no_chart(tmp_path):
    wdl = tmp_path / 'w.wdl'
    wdl.touch()
    assert fc.find_flowchart(str(wdl), 'w1') is None


def test_find_flowchart_honours_an_explicit_directory(tmp_path):
    wdl = tmp_path / 'w.wdl'
    wdl.touch()
    (tmp_path / 'w1.flow.svg').touch()
    elsewhere = tmp_path / 'diagrams'
    elsewhere.mkdir()
    chart = elsewhere / 'w1.flow.svg'
    chart.touch()
    assert fc.find_flowchart(str(wdl), 'w1', outdir=str(elsewhere)) == str(chart)


# --------------------------------------------- generate_markdown_readme integration

def run_readme(wdl, *extra):
    env = dict(os.environ, PYTHONPATH=str(REPO_ROOT))
    result = subprocess.run(
        [sys.executable, str(REPO_ROOT / 'scripts' / 'generate_markdown_readme.py'),
         '--input-wdl-path', str(wdl), *extra],
        capture_output=True, text=True, env=env, check=True)
    return result.stdout


def draw_chart(wdl, subdir=None):
    """Put a flowchart where generate-wdl-flowchart would have left it."""
    outdir = Path(wdl).parent if subdir is None else Path(wdl).parent / subdir
    outdir.mkdir(exist_ok=True)
    chart = outdir / 'workflow1.flow.svg'
    chart.write_text('<svg xmlns="http://www.w3.org/2000/svg"/>')
    return chart


def test_readme_has_no_flowchart_section_without_a_chart(shared_datadir):
    assert '## Workflow Flowchart' not in run_readme(shared_datadir / 'workflow1.wdl')


def test_readme_flowchart_section_follows_overview(shared_datadir):
    draw_chart(shared_datadir / 'workflow1.wdl', 'docs')
    readme = run_readme(shared_datadir / 'workflow1.wdl')
    assert '![workflow1 workflow flowchart](./docs/workflow1.flow.svg)' in readme
    assert (readme.index('## Overview')
            < readme.index('## Workflow Flowchart')
            < readme.index('## Dependencies'))


def test_readme_links_a_chart_beside_the_wdl(shared_datadir):
    draw_chart(shared_datadir / 'workflow1.wdl')
    readme = run_readme(shared_datadir / 'workflow1.wdl')
    assert '![workflow1 workflow flowchart](./workflow1.flow.svg)' in readme


def test_readme_no_flowchart_flag(shared_datadir):
    draw_chart(shared_datadir / 'workflow1.wdl', 'docs')
    assert '## Workflow Flowchart' not in run_readme(
        shared_datadir / 'workflow1.wdl', '--no-flowchart')


def test_readme_flowchart_dir_overrides_the_search(shared_datadir):
    chart = draw_chart(shared_datadir / 'workflow1.wdl', 'diagrams')
    readme = run_readme(shared_datadir / 'workflow1.wdl',
                        '--flowchart-dir', str(chart.parent))
    assert '![workflow1 workflow flowchart](./diagrams/workflow1.flow.svg)' in readme


def test_existing_readme_gains_the_section_under_overview(shared_datadir):
    wdl = shared_datadir / 'workflow1.wdl'
    draw_chart(wdl, 'docs')
    readme_file = shared_datadir / 'README.md'
    readme_file.write_text("# workflow1\n\n## Overview\n\nHand written.\n\n"
                           "## Dependencies\n\n* nothing\n")
    run_readme(wdl)
    updated = readme_file.read_text()
    assert ("## Overview\n\nHand written.\n\n## Workflow Flowchart\n\n"
            "![workflow1 workflow flowchart](./docs/workflow1.flow.svg)\n\n"
            "## Dependencies") in updated

    # regenerating must not stack a second copy of the section
    run_readme(wdl)
    assert readme_file.read_text().count('## Workflow Flowchart') == 1
