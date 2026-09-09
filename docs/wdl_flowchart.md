# generate-wdl-flowchart

Generate a structural flowchart for a WDL workflow, straight from the WDL text.

```
generate-wdl-flowchart myWorkflow.wdl --svg
generate-wdl-flowchart --all ~/dev/workflow --svg    # sweep a tree of repos
generate-wdl-flowchart myWorkflow.wdl --check        # fail if the committed .dot is stale
generate-wdl-flowchart myWorkflow.wdl --hide extractName --svg   # leave plumbing out
```

Or with `uv run`, or straight from a checkout:

```
uv run generate-wdl-flowchart myWorkflow.wdl --svg
python3 ./scripts/wdl_flowchart.py myWorkflow.wdl --svg
```

The tool imports only the standard library, so the last form needs no virtualenv at all:
any `python3` runs it, and graphviz is needed only to render.

Writes `<workflow>.flow.dot` next to the WDL, or into a sibling `docs/` if one exists.
`--svg` / `--png` render it with graphviz. Calls are boxes, `scatter` and `if` are nested
clusters labelled with their real expressions, and edges are data dependencies.

The cluster colour says which kind of block it is:

- **orange** - a `scatter`, drawn as one box for all its shards
- **green** - one named case of a scatter that was expanded into branches (see below)
- **grey, dashed** - an `if`, labelled with its condition

A call box with a hatched purple border is a call into an imported WDL, whose internals are
not shown.

The `workflow inputs` and `workflow outputs` notes are joined by faint dashed edges. To
keep them from becoming a hairball they are not drawn to every call that happens to read an
input; an input edge means *this call can start with nothing else having run*. That covers
a call with no dependencies at all, and a call whose only dependencies are optional - all
of them inside an `if` that does not also contain the call, so there is a run where none of
them happened and the value comes from an input instead. That second case is the
`select_first([optionalCall.out, someInput])` idiom, and its edge is the path taken when
the condition is false.

Only graphviz (`dot`) is needed to render, and nothing at all to produce the `.dot`.

## Feeding generate-markdown-readme

`generate-markdown-readme` looks for a chart of the workflow it is documenting, and when it
finds one it writes a `Workflow Flowchart` section directly under `Overview`:

```markdown
## Workflow Flowchart

![myWorkflow workflow flowchart](./docs/myWorkflow.flow.svg)
```

It looks in the same places this tool writes to - a `docs/` beside the WDL first, then the
WDL's own directory - and takes the `.svg` over the `.png`. Nothing is drawn on demand, so
generate the chart first:

```
generate-wdl-flowchart myWorkflow.wdl --svg
generate-markdown-readme --input-wdl-path myWorkflow.wdl > README.md
```

With no chart on disk the section is left out entirely and the README is what it always was.
`--no-flowchart` suppresses the section even when a chart exists, and `--flowchart-dir DIR`
points the search somewhere else.

An existing `README.md` is also updated in place, the same way its `Commands` section is:
the flowchart section is inserted under `Overview` if it is missing and refreshed if it is
already there, so regenerating never stacks up copies.

## Why not `womtool graph`

`womtool` has a `graph` subcommand, and where it works the output is reasonable. But it
builds the full WOM graph first and throws when it cannot link a node. Measured across the
OICR-GSI workflow collection it failed on 2 of 4 tried, including
`java.util.NoSuchElementException: key not found: ScatterVariableNode(...)` on a scatter
over `select_first(...)` - a perfectly ordinary construct.

This tool parses the text instead. When it meets something it does not understand it
degrades to a less precise picture rather than to no picture, which is the right failure
mode for documentation tooling.

Exercised over 186 `.wdl` files in the GSI collection: 122 workflows produced a graph, 64
were task-only files correctly reported as `no workflow block, skipped`, and nothing
crashed.

## Two kinds of scatter

`scatter` gets used for two different things, and drawing them the same way loses the
distinction that matters most to a reader.

**Data parallelism.** `scatter (chr in chromosomes)` runs identical work on interchangeable
shards. One box is the honest picture: the shards differ only in which slice of data they
touch, and there is nothing to learn from seeing 25 copies.

**Named cases.** `scatter (ig in select_all([tumorInputGroup, normalInputGroup]))` is not
really parallelism over data; the array is the list of conditions the workflow is
contrasting. A reader wants to see tumour and normal as separate branches - that is what
they would draw by hand - even when both traverse identical calls, because the point being
made is *this workflow processes tumour and normal separately*, and often they diverge
later.

So a scatter whose collection resolves to an explicit array literal of a few bare
identifiers is drawn as one branch per element:

```
scatter (ig in inputGroups)          becomes      [ig = tumorInputGroup]   [ig = normalInputGroup]
  call annotate                                     call annotate            call annotate
  call filter                                       call filter              call filter
```

Calls are cloned per branch, dependencies inside a branch stay inside it, and anything
downstream fans in from every branch. Control it with `--expand-cases N` (default 4, `0`
disables). The literal-of-identifiers rule is what keeps chromosome-style scatters as one
box: a 25-element list of strings, a single-element `select_first`, or a member that is not
a plain identifier all fail it.

## Hiding plumbing calls

You give the tool a **list of task names** to leave out of the chart: the tasks that are
technical detail rather than steps a reader follows. The tool cannot choose them for you -
a merge task is the point of one workflow and an implementation detail of another - so the
list is yours to write.

There are two ways to supply that task list.

### 1. On the command line, for a single run

```bash
generate-wdl-flowchart myWorkflow.wdl --svg --hide <task1, task2...>
```

Repeat `--hide` or separate names with commas.

### 2. In a file beside the WDL, used automatically every time

Create a file named `<workflow>.flow.hide` next to the WDL, containing one task name per
line. The tool looks for it on its own - there is no flag to remember, and `--check` reads
it too, so a pre-commit hook regenerates exactly the chart you did:

```bash
cd /path/to/myWorkflow
cat > myWorkflow.flow.hide <<'EOF'
# one task name per line; blank lines and # comments ignored
extractName
splitPonByChromosome
EOF

generate-wdl-flowchart myWorkflow.wdl --svg  # no --hide needed, the file is found
```

This is the one to use for a workflow whose chart you will regenerate more than once. Both
ways can be combined: `--hide` adds to whatever the file already lists.

### Options

| option | effect |
| --- | --- |
| *(none)* | reads `<workflow>.flow.hide` beside the WDL, if that file exists |
| `--hide NAME[,NAME...]` | hide these too, just for this run; repeatable |
| `--hide-file FILE` | read the list from `FILE` instead of the default location |
| `--show-all` | ignore the file and `--hide`; draw every call |

### Which calls a name matches

- a **task** name hides every call of that task
- a **call alias** hides only that one call

In `wisp`, `mergeAmberChromosomes` is a task called twice, aliased `amberPrimary` and
`amberPlasma`; listing the task name hides both, listing `amberPrimary` hides only that
one. List the task name when you mean "this kind of step is never interesting".

### Reading the output

```
wisp.flow.dot  (12 calls, 15 edges, 6 hidden, 2 unresolved refs)
```

The chart carries a `not shown, technical detail:` note listing the hidden tasks, and the
same list is written into the `.dot` header, so a filtered diagram is never mistaken for a
complete one. A name that matches nothing prints `nothing to hide named 'x'` on stderr -
that is your warning that the list has drifted after a task was renamed.

Hidden calls are **contracted, not deleted**: `a -> hidden -> b` is drawn as `a -> b`, and
chains of hidden calls collapse in one step, so the reachability you read off the picture
still holds.

## Keeping it honest: `--check`

The reason workflow diagrams rot is that nobody regenerates them. `--check` regenerates in
memory and exits non-zero if the committed `.dot` differs:

```bash
# .git/hooks/pre-commit
generate-wdl-flowchart myWorkflow.wdl --check || exit 1
```

Commit the `.dot` and the `.svg`; the `.png` is only worth rendering on demand (it is
hundreds of kB of binary that changes on every edit, and Confluence is usually the only
thing that needs it).

## What the picture does NOT mean

These are not rough edges to be fixed later. They are consequences of reading a static
declaration, and mistaking the graph for more than it claims is the main way to be misled
by one. Even for a pure-WDL workflow, with no other engine involved:

1. **Cardinality is invisible.** A `scatter` is one box whether it fans out 2 ways or 2000.
   Worse, when the collection comes from a task output - `scatter (x in read_lines(prep.out))`
   - the width is not knowable from the text at all, at any effort. (The exception is a
   scatter used to enumerate named cases; see below.)

2. **Branches are drawn, not resolved.** Every `if` appears, so mutually exclusive paths sit
   side by side as though they all run. A workflow with a `mode` input shows every mode's
   subgraph at once. The cluster labels carry the condition, so the information is there, but
   the *shape* overstates what any single run does.

3. **Edges are inferred, not authoritative.** They come from matching `x.y` references and
   workflow-level declarations. A dependency that flows through an expression the
   declaration pattern does not match yields a *missing* edge; a call alias that collides
   with a variable name yields a *spurious* one. Run with `-v` to list names it could not
   classify. Treat the edges as "probably right", and check the WDL before relying on one.

4. **The file is the horizon.** `call other.task` is a single node, and an imported
   sub-workflow is one box no matter how many tasks it contains. `import` is not followed.
   Those nodes are drawn hatched, so at least you can see where the picture stops.

5. **Nothing about what a task does.** Command bodies are deliberately stripped - they are
   full of text that looks like workflow syntax. Two vaguely named tasks are
   indistinguishable in the graph.

6. **No resources, no time, no cost.** Nothing about memory, cpu, wall clock, or which step
   dominates a run. A 4-hour step and a 12-second step are the same size box.

7. **Layout is dependency order, not a schedule.** Independent branches run concurrently;
   top-to-bottom does not mean one-after-another. Cromwell runs whatever is ready, and call
   caching may mean a box does not execute at all.

8. **Optionality is not shown.** An `File?` output that a given mode never produces looks
   exactly like a required one.

And the case that motivated the tool: **a task that launches another workflow engine is one
box**, however many processes it really spawns. A WDL wrapping a Nextflow pipeline shows the
wrapper task, not the dozens of jobs Nextflow submits.

So this is a *declaration-level* view: reliable about which calls exist and how they nest,
approximate about edges, silent about everything above. It answers "is this diagram still
accurate?" It does not replace a hand-drawn diagram that answers "how should I think about
this workflow?" - the two are worth keeping side by side, the generated one because it cannot
drift, the hand-drawn one because it can say things the WDL does not.

## Tests

```
uv run pytest tests/test_wdl_flowchart.py
```

`tests/data/flowchart_nesting.wdl` is built from constructs that have actually caused trouble:
decoy `call` / `if` / `scatter` text inside both command-block styles, a scatter nested in an
`if`, a multi-line scatter expression, a multi-line call input block, a dependency threaded
through an intermediate declaration, and a call into an imported file. The suite also checks
that `--check` accepts a fresh `.dot` and rejects a tampered one, and that a chart on disk
turns into a Workflow Flowchart section in a generated README.
