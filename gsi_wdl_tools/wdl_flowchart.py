#!/usr/bin/env python3
"""Generate a structural flowchart for a WDL workflow, from the WDL text.

    generate-wdl-flowchart <workflow.wdl>... [--svg] [--png] [--check] [-o DIR]
    generate-wdl-flowchart --all <dir> [--svg]

Writes <DIR>/<workflow>.flow.dot, and with --svg/--png renders it via graphviz. `--check`
regenerates in memory and exits non-zero if the committed .dot differs, so a pre-commit
hook can stop a diagram going stale.

Nodes are calls, clusters are scatter/if blocks, edges are data dependencies. See
docs/wdl_flowchart.md for what the picture does and does not mean - the limitations are
not incidental, and reading a graph as more than it claims is the main way to be misled
by one.

Plumbing calls can be left out with --hide, or with a `<workflow>.flow.hide` file beside
the WDL. Hidden calls are contracted, not dropped: edges are spliced through them.
"""
import argparse
import os
import re
import subprocess
import sys

__version__ = "1.0.0"

# ---------------------------------------------------------------------------- lexing

IMPORT = re.compile(r'^\s*import\s+"([^"]+)"(?:\s+as\s+(\w+))?')
TOKEN = re.compile(
    r'^\s*(?:'
    r'(?P<workflow>workflow\s+(?P<wfname>\w+)\s*\{)'
    r'|(?P<task>task\s+(?P<taskname>\w+)\s*\{)'
    r'|(?P<scatter>scatter\s*\((?P<scexpr>.*?)\)\s*\{)'
    r'|(?P<ifblock>if\s*\((?P<ifexpr>.*)\)\s*\{)'
    r'|(?P<call>call\s+(?P<callee>[\w.]+)(?:\s+as\s+(?P<alias>\w+))?)'
    r')'
)
# A declaration: a type, a name, '='. Types include user structs, so any capitalised word
# qualifies; that is deliberately loose, and the cost is a stray entry, not a wrong edge.
DECL = re.compile(r'^\s*(?:Array|Map|Pair|File|String|Int|Float|Boolean|Object|[A-Z]\w*)'
                  r'[\w\[\]\?\+, ]*\s+(\w+)\s*=\s*(.*)$')
BARE_DECL = re.compile(r'^\s*(?:Array|Map|Pair|File|String|Int|Float|Boolean|Object|[A-Z]\w*)'
                       r'[\w\[\]\?\+, ]*\s+(\w+)\s*$')
REF = re.compile(r'\b(\w+)\.\w+')


def strip_comments(line):
    """Drop a trailing # comment, respecting quotes."""
    out, q = [], None
    for ch in line:
        if q:
            out.append(ch)
            if ch == q:
                q = None
        elif ch in '"\'':
            q = ch
            out.append(ch)
        elif ch == '#':
            break
        else:
            out.append(ch)
    return ''.join(out)


def lex(text):
    """Comments removed, command bodies removed, continuation lines joined.

    Command bodies must go FIRST: they hold arbitrary shell, so a line starting `call `
    or an unbalanced bracket inside one would otherwise derail both the tokeniser and the
    continuation joiner.
    """
    raw = text.split('\n')
    kept, i = [], 0
    while i < len(raw):
        line = raw[i]
        if re.match(r'^\s*command\s*<<<', line):
            kept.append(re.sub(r'command\s*<<<.*', 'command <<< STRIPPED >>>', line))
            i += 1
            while i < len(raw) and '>>>' not in raw[i]:
                i += 1
            i += 1
            continue
        if re.match(r'^\s*command\s*\{', line):
            depth = line.count('{') - line.count('}')
            kept.append(re.sub(r'command\s*\{.*', 'command { STRIPPED }', line))
            i += 1
            while i < len(raw) and depth > 0:
                depth += raw[i].count('{') - raw[i].count('}')
                i += 1
            continue
        kept.append(strip_comments(line))
        i += 1

    # join continuations: a line whose brackets are unbalanced continues onto the next
    joined, buf, bal = [], '', 0
    for line in kept:
        if not line.strip():
            if not buf:
                joined.append(line)
            continue
        piece = line if not buf else buf + ' ' + line.strip()
        bal = (piece.count('(') - piece.count(')')
               + piece.count('[') - piece.count(']'))
        if bal > 0:
            buf = piece
        else:
            joined.append(piece)
            buf = ''
    if buf:
        joined.append(buf)
    return joined


# ---------------------------------------------------------------------------- model

class Node:
    def __init__(self, alias, callee, imported):
        self.alias, self.callee, self.imported = alias, callee, imported
        self.display = alias          # differs from alias only for per-case clones
        self.deps = set()
        self.ifs = frozenset()        # `if` blocks enclosing this call; set by mark_conditional


class Block:
    def __init__(self, kind, label):
        self.kind, self.label = kind, label
        self.children, self.calls = [], []


class Workflow:
    def __init__(self):
        self.name = None
        self.root = Block('root', '')
        self.nodes = {}
        self.decls = {}
        self.inputs, self.outputs, self.imports = [], [], []
        self.hidden = []              # task names left out as technical detail
        # Names that look like dependencies but are not calls: scatter variables and import
        # aliases. Without these the "unresolved" count is all noise and tells you nothing.
        self.scatter_vars, self.unresolved = set(), set()


def parse(path):
    wf = Workflow()
    lines = lex(open(path).read())

    depth, stack, cur = 0, [], wf.root
    in_task, section = None, None
    pending, pending_depth = None, None

    for line in lines:
        if not line.strip():
            continue

        imp = IMPORT.match(line)
        if imp:
            alias = imp.group(2) or os.path.basename(imp.group(1))
            wf.imports.append(alias)

        m = TOKEN.match(line)
        if m:
            if m.group('workflow'):
                wf.name = m.group('wfname')
            elif m.group('task'):
                in_task = m.group('taskname')
            elif not in_task and m.group('scatter'):
                sc = m.group('scexpr').strip()
                v = re.match(r'(\w+)\s+in\s', sc)
                if v:
                    wf.scatter_vars.add(v.group(1))
                b = Block('scatter', sc)
                cur.children.append(b)
                stack.append((depth, cur))
                cur = b
            elif not in_task and m.group('ifblock'):
                b = Block('if', m.group('ifexpr').strip())
                cur.children.append(b)
                stack.append((depth, cur))
                cur = b
            elif not in_task and m.group('call'):
                callee = m.group('callee')
                alias = m.group('alias') or callee.split('.')[-1]
                n = Node(alias, callee, '.' in callee)
                cur.calls.append(n)
                wf.nodes[alias] = n
                pending, pending_depth = n, depth

        if not in_task:
            st = line.strip()
            if st.startswith('input {'):
                section = 'input'
            elif st.startswith('output {'):
                section = 'output'
            elif section and st == '}':
                section = None
            elif section == 'input':
                d = DECL.match(line) or BARE_DECL.match(line)
                if d:
                    wf.inputs.append(d.group(1))
            elif section == 'output':
                d = DECL.match(line)
                if d:
                    wf.outputs.append(d.group(1))
            else:
                d = DECL.match(line)
                if d:
                    wf.decls[d.group(1)] = d.group(2)

        if pending is not None:
            for ref in REF.findall(line):
                pending.deps.add(ref)
            for w in re.findall(r'\b(\w+)\b', line):
                if w in wf.decls:
                    pending.deps.add(w)

        closes = line.count('}')
        depth += line.count('{') - closes
        if pending is not None and closes and depth <= pending_depth:
            pending = None
        if in_task and depth == 0:
            in_task = None
        while stack and depth <= stack[-1][0]:
            _, cur = stack.pop()

    return wf


WRAP = re.compile(r'^\s*(?:select_all|select_first|flatten)\s*\((.*)\)\s*$')


def split_top(text):
    """Split on commas that are not inside brackets."""
    out, depth, cur = [], 0, ''
    for ch in text:
        if ch in '([':
            depth += 1
        elif ch in ')]':
            depth -= 1
        if ch == ',' and depth == 0:
            out.append(cur)
            cur = ''
        else:
            cur += ch
    if cur.strip():
        out.append(cur)
    return [x.strip() for x in out]


def scatter_cases(expr, decls, cap):
    """Element names if this scatter enumerates NAMED CASES, else None.

    A scatter over chromosomes is data parallelism: every shard does the same thing to
    different data, and one box is the honest picture. A scatter over
    `select_all([tumorInputGroup, normalInputGroup])` is something else - the array is a
    list of the conditions the workflow is contrasting, and a reader wants to see tumour
    and normal as separate branches even when they traverse identical calls.

    Telling them apart: only an explicit array literal of a FEW BARE IDENTIFIERS counts.
    That accepts [tumorInputGroup, normalInputGroup] and rejects a 25-element list of
    chromosome strings, a single-element select_first, and anything with a non-identifier
    member such as select_first([controls, []]).
    """
    m = re.match(r'\w+\s+in\s+(.*)$', expr.strip(), re.S)
    if not m:
        return None
    coll = m.group(1).strip()
    for _ in range(4):                       # unwrap select_all(...) etc, and declarations
        w = WRAP.match(coll)
        if w:
            coll = w.group(1).strip()
            continue
        if coll in decls:
            coll = decls[coll].strip()
            continue
        break
    lit = re.match(r'^\[(.*)\]$', coll, re.S)
    if not lit:
        return None
    parts = split_top(lit.group(1))
    if not 2 <= len(parts) <= cap:
        return None
    if not all(re.fullmatch(r'\w+', x) for x in parts):
        return None
    return parts


def expand_cases(wf, cap):
    """Replace each named-case scatter with one cluster per case.

    Calls are cloned per branch with suffixed ids so graphviz keeps them distinct, while
    the visible label stays the original call name. Dependencies WITHIN a branch are
    rewired to that branch's clones; dependencies crossing the boundary fan out to all of
    them, since a downstream consumer of a scattered call consumes the whole array.
    """
    def aliases_in(block):
        out = {c.alias for c in block.calls}
        for ch in block.children:
            out |= aliases_in(ch)
        return out

    def clone(block, suffix, inside):
        nb = Block(block.kind, block.label)
        for c in block.calls:
            n = Node(c.alias + suffix, c.callee, c.imported)
            n.display = c.alias
            n.deps = {d + suffix if d in inside else d for d in c.deps}
            nb.calls.append(n)
            wf.nodes[n.alias] = n
        for ch in block.children:
            nb.children.append(clone(ch, suffix, inside))
        return nb

    def walk(block):
        new_children = []
        for child in block.children:
            walk(child)
            cases = (scatter_cases(child.label, wf.decls, cap)
                     if child.kind == 'scatter' else None)
            if not cases:
                new_children.append(child)
                continue
            inside = aliases_in(child)
            var = re.match(r'(\w+)\s+in\s', child.label.strip())
            var = var.group(1) if var else 'x'
            for case in cases:
                nb = clone(child, '__' + case, inside)
                nb.kind, nb.label = 'case', f'{var} = {case}'
                new_children.append(nb)
            for a in inside:                        # originals are replaced by the clones
                wf.nodes.pop(a, None)
            for n in wf.nodes.values():             # consumers fan out to every branch
                if n.deps & inside:
                    n.deps = ((n.deps - inside)
                              | {d + '__' + c for d in n.deps & inside for c in cases})
        block.children = new_children

    walk(wf.root)


def coalesce(block):
    """Merge sibling `if` blocks that share a condition, depth first.

    A workflow often opens `if (defined(tumor))` several times at the same scope, once per
    processing stage. Each is a separate block in the text but they are the same condition,
    so drawing one cluster each fragments a logical branch into pieces and interleaves it
    with its neighbours. Merging them puts the whole branch in one box, which is what a
    reader means by "the tumour path".

    Scatters are NOT merged, even when their expressions are identical. Two
    `scatter (idx in range(length(chromosomes)))` blocks are two separate parallel stages
    that happen to shard the same way - in wisp one runs amber over the primary and the
    other over the plasma - and putting them in one box claims a relationship the workflow
    does not have. An `if` repeats a condition; a scatter repeats a shape.
    """
    merged, seen = [], {}
    for child in block.children:
        coalesce(child)
        key = (child.kind, child.label)
        if child.kind == 'if' and key in seen:
            target = seen[key]
            target.calls.extend(child.calls)
            target.children.extend(child.children)
        else:
            seen[key] = child
            merged.append(child)
    # a merge can bring together children that are themselves now duplicates
    for child in merged:
        if len(child.children) > 1:
            coalesce(child)
    block.children = merged


def resolve(wf):
    """Map dependency names onto call aliases, following declarations transitively.

    Without this a workflow that threads outputs through intermediate declarations
    (`File x = select_first([a.bam])` then `input: b = x`) would show almost no edges.
    """
    def calls_in(expr, seen):
        found = {r for r in REF.findall(expr) if r in wf.nodes}
        for w in re.findall(r'\b(\w+)\b', expr):
            if w in wf.decls and w not in seen:
                found |= calls_in(wf.decls[w], seen | {w})
        return found

    for n in wf.nodes.values():
        real = set()
        for d in n.deps:
            if d in wf.nodes:
                real.add(d)
            elif d in wf.decls:
                real |= calls_in(wf.decls[d], {d})
            elif (d in wf.inputs or d in wf.scatter_vars or d in wf.imports
                  or '.' in d):
                pass
            else:
                wf.unresolved.add(d)
        n.deps = real - {n.alias}


def hide_calls(wf, names):
    """Leave out calls that are plumbing, splicing dependencies through them.

    Some tasks are real work but not steps a reader is following: pulling a sample name
    out of a BAM, sharding an input by chromosome, merging those shards back. Each costs a
    box and a pair of edges, and a dozen of them bury the handful of calls the diagram
    exists to show. Which ones are plumbing cannot be read off the WDL - a merge task can
    be the point of a workflow or an implementation detail of one - so the list is a human
    judgement supplied from outside.

    A name matches a call by task name, by call alias, or by both, so `mergeAmberChromosomes`
    hides every call of that task while `amberPrimary` hides just the one.

    Hidden calls are CONTRACTED, not deleted: `a -> split -> b` becomes `a -> b`, so the
    reachability a reader takes from the picture still holds. Chains of hidden calls
    collapse in one pass. Deleting instead of contracting would leave disconnected islands,
    which misleads worse than the clutter it removes.

    Returns (number hidden, names that matched nothing).
    """
    hidden, matched = set(), set()
    for alias, n in wf.nodes.items():
        hit = names & {n.callee, n.display, alias}
        if hit:
            hidden.add(alias)
            matched |= hit
    if not hidden:
        return 0, names - matched

    def through(alias, seen):
        """Dependencies of alias, following hidden ones back to visible calls."""
        out = set()
        for d in wf.nodes[alias].deps:
            if d not in hidden:
                out.add(d)
            elif d not in seen:
                out |= through(d, seen | {d})
        return out

    for alias, n in wf.nodes.items():
        if alias not in hidden:
            n.deps = through(alias, {alias}) - {alias}

    def prune(block):
        block.calls = [c for c in block.calls if c.alias not in hidden]
        for child in block.children:
            prune(child)
        # a scatter whose every call was hidden is an empty box; drop it rather than
        # leaving a labelled cluster with nothing in it
        block.children = [c for c in block.children if c.calls or c.children]

    prune(wf.root)
    wf.hidden = sorted({wf.nodes[a].callee for a in hidden})
    for alias in hidden:
        del wf.nodes[alias]
    return len(hidden), names - matched


def hide_list(path, args):
    """Names to hide: --hide flags, plus a sidecar file beside the WDL.

    The sidecar is the durable half. Which calls are noise is a decision someone made once
    about this workflow; keeping it in the repo next to the committed .dot means it is
    reviewed, versioned, and applied identically by --check in a hook. A flag typed by
    whoever happens to run the tool is not.
    """
    if args.show_all:
        return set()

    names = set()
    for chunk in args.hide or []:
        names |= {x.strip() for x in chunk.split(',') if x.strip()}

    sidecar = args.hide_file
    if sidecar and not os.path.exists(sidecar):
        sys.exit(f"--hide-file {sidecar}: no such file")
    if not sidecar:
        beside = os.path.splitext(path)[0] + '.flow.hide'
        sidecar = beside if os.path.exists(beside) else None
    if sidecar:
        with open(sidecar) as fh:
            for line in fh:
                line = line.split('#')[0].strip()
                if line:
                    names.add(line)
    return names


# ---------------------------------------------------------------------------- emitting

HEADER = '''// Generated by generate-wdl-flowchart {ver} from {src}. DO NOT EDIT.
// Regenerate: generate-wdl-flowchart {src} --svg
//
// Calls are boxes, scatter/if are clusters, edges are data dependencies. This is a
// DECLARATION-level view: see docs/wdl_flowchart.md for what it cannot show.
{hidden}digraph {name} {{
  rankdir=TB;
  compound=true;
  bgcolor="white";
  nodesep=0.35;
  ranksep=0.5;
  node [fontname="Helvetica" fontsize=10 style="filled,rounded" shape=box
        fillcolor="#eef4fb" color="#7ba7d7"];
  edge [fontname="Helvetica" fontsize=9 color="#555555"];
  graph [fontname="Helvetica" fontsize=10 labeljust=l];
'''


def mark_conditional(wf):
    """Record which `if` blocks enclose each call.

    Run after coalesce/expand_cases, which rebuild the block tree, so the annotation
    reflects the blocks actually being drawn.
    """
    def walk(block, enclosing):
        for call in block.calls:
            call.ifs = enclosing
        for child in block.children:
            inner = (enclosing | {id(child)}) if child.kind == 'if' else enclosing
            walk(child, inner)

    walk(wf.root, frozenset())


def from_inputs(wf, n):
    """True if the workflow inputs can feed this call directly.

    A call with no dependencies plainly starts from the inputs. So does a call whose every
    dependency sits in an `if` block that does not also enclose the call: there is a run in
    which none of those calls happened, and the value comes from an input instead. That is
    the `select_first([optionalCall.out, someInput])` idiom, and it is a real path through
    the workflow - the one taken when the condition is false. Drawing no edge for it hides
    the fallback and makes the optional call look mandatory.

    A dependency in the SAME `if` as the consumer does not count: when that condition is
    false neither call runs, so there is no path to draw.
    """
    if not n.deps:
        return True
    deps = [wf.nodes[d] for d in n.deps if d in wf.nodes]
    return bool(deps) and all(d.ifs - n.ifs for d in deps)


def esc(s, limit=64):
    s = re.sub(r'\s+', ' ', s.replace('\\', ' ').replace('"', "'")).strip()
    return s if len(s) <= limit else s[:limit - 3] + '...'


def note_box(name, title, items, limit=12):
    shown = items[:limit]
    label = "\\n".join(shown) + ("\\n..." if len(items) > limit else "")
    return [f'  subgraph cluster_{name} {{',
            f'    label="{title}"; labeljust=c;',
            '    style="filled,rounded"; fillcolor="#f7f7f7"; color="#cccccc";',
            '    node [shape=note fillcolor="#ffffff" color="#888888"];',
            f'    {name.upper()} [label="{label}"]',
            '  }']


def emit(wf, src):
    # Record what was left out in the .dot itself: a reader diffing the committed file
    # should be able to see that the picture is deliberately partial, and which calls it
    # is missing, without going hunting for the .flow.hide file.
    note = ''
    if wf.hidden:
        note = ('//\n// Hidden as technical detail: '
                + ', '.join(wf.hidden) + '\n')
    out = [HEADER.format(ver=__version__, src=os.path.basename(src),
                         name=wf.name or 'workflow', hidden=note)]
    mark_conditional(wf)
    ctr = [0]

    def walk(b, indent='  '):
        for n in b.calls:
            label = (n.display if n.display == n.callee
                     else f"{n.display}\\n({n.callee})")
            extra = (' color="#9a6fb0" style="filled,rounded,diagonals"'
                     if n.imported else '')
            out.append(f'{indent}{n.alias} [label="{label}"{extra}]')
        for child in b.children:
            ctr[0] += 1
            if child.kind == 'scatter':
                fill = 'fillcolor="#fdf3e7" color="#e0a35c" style="filled,rounded"'
                lab = f'scatter ({esc(child.label)})'
            elif child.kind == 'case':
                # a named branch of a scatter over a small literal list
                fill = 'fillcolor="#eaf5ea" color="#5f9a5f" style="filled,rounded"'
                lab = esc(child.label)
            else:
                fill = 'fillcolor="#f6f6f6" color="#999999" style="filled,rounded,dashed"'
                lab = f'if ({esc(child.label)})'
            out.append(f'{indent}subgraph cluster_{ctr[0]} {{')
            out.append(f'{indent}  label="{lab}"; {fill};')
            walk(child, indent + '  ')
            out.append(f'{indent}}}')

    if wf.inputs:
        out += note_box('inputs', 'workflow inputs', wf.inputs)
    walk(wf.root)
    if wf.outputs:
        out += note_box('outputs', 'workflow outputs', wf.outputs)

    out.append('')
    for n in sorted(wf.nodes.values(), key=lambda x: x.alias):
        for d in sorted(n.deps):
            out.append(f'  {d} -> {n.alias}')

    roots = sorted(n.alias for n in wf.nodes.values() if from_inputs(wf, n))
    leaves = sorted(n.alias for n in wf.nodes.values()
                    if not any(n.alias in m.deps for m in wf.nodes.values()))
    for r in roots:
        if wf.inputs:
            out.append(f'  INPUTS -> {r} [style=dashed color="#bbbbbb"]')
    for lf in leaves:
        if wf.outputs:
            out.append(f'  {lf} -> OUTPUTS [style=dashed color="#bbbbbb"]')

    if wf.hidden:
        # The picture claims to be the workflow, so it has to admit what it omits.
        wrapped = "\\n".join(', '.join(wf.hidden[i:i + 3])
                            for i in range(0, len(wf.hidden), 3))
        out.append('')
        out.append('  legend_hidden [shape=note fontsize=9 style=filled '
                   'fillcolor="#f7f7f7" color="#888888" '
                   f'label="not shown, technical detail:\\n{wrapped}"]')

    if wf.imported_any():
        out.append('')
        out.append('  legend_imported [shape=box style="filled,rounded,diagonals" '
                   'fillcolor="#eef4fb" color="#9a6fb0" '
                   'label="hatched = call into an imported file;\\nits internals are not shown"]')

    out.append('}')
    return '\n'.join(out) + '\n'


Workflow.imported_any = lambda self: any(n.imported for n in self.nodes.values())


# ---------------------------------------------------------------------------- driver

# Formats a README can display, best first. The .dot is the source, not a picture, so it is
# not offered here.
FLOWCHART_FORMATS = ('svg', 'png')


def output_dirs(wdl_path):
    """Directories a chart for this WDL may live in, in the order they are preferred."""
    base = os.path.dirname(os.path.abspath(wdl_path))
    return (os.path.join(base, 'docs'), base)


def output_dir(wdl_path, outdir=None):
    """Where to write a chart: an explicit dir, else a sibling docs/, else beside the WDL."""
    if outdir:
        return outdir
    docs, base = output_dirs(wdl_path)
    return docs if os.path.isdir(docs) else base


def find_flowchart(wdl_path, workflow_name, formats=FLOWCHART_FORMATS, outdir=None):
    """Path of a chart already generated for this workflow, or None if there is none.

    Searches the directories the generator writes to, so a chart is found without being
    told where it was put.
    """
    dirs = (outdir,) if outdir else output_dirs(wdl_path)
    for d in dirs:
        for fmt in formats:
            path = os.path.join(d, f'{workflow_name}.flow.{fmt}')
            if os.path.isfile(path):
                return path
    return None


def render(dot_path, wf_name, outdir, fmt, extra):
    if not any(os.access(os.path.join(p, 'dot'), os.X_OK)
               for p in os.environ.get('PATH', '').split(os.pathsep)):
        print("graphviz 'dot' not on PATH; wrote .dot only", file=sys.stderr)
        return None
    target = os.path.join(outdir, f'{wf_name}.flow.{fmt}')
    subprocess.run(['dot', f'-T{fmt}'] + extra + [dot_path, '-o', target], check=True)
    return target


def process(path, args):
    wf = parse(path)
    if not wf.name:
        print(f"{path}: no workflow block, skipped", file=sys.stderr)
        return True
    coalesce(wf.root)
    resolve(wf)
    if args.expand_cases:
        expand_cases(wf, args.expand_cases)
    # after expand_cases: per-case clones carry the original name in .display, so a hide
    # entry matches every branch's copy
    n_hidden = 0
    names = hide_list(path, args)
    if names:
        n_hidden, unmatched = hide_calls(wf, names)
        for name in sorted(unmatched):
            print(f"{path}: nothing to hide named '{name}'", file=sys.stderr)
    dot = emit(wf, path)

    outdir = output_dir(path, args.outdir)
    dot_path = os.path.join(outdir, f'{wf.name}.flow.dot')

    if args.check:
        if not os.path.exists(dot_path):
            print(f"MISSING {dot_path} (run without --check to create it)", file=sys.stderr)
            return False
        if open(dot_path).read() != dot:
            print(f"STALE {dot_path} does not match {path}", file=sys.stderr)
            return False
        print(f"ok {dot_path}")
        return True

    os.makedirs(outdir, exist_ok=True)
    with open(dot_path, 'w') as fh:
        fh.write(dot)
    edges = sum(len(n.deps) for n in wf.nodes.values())
    extra = f", {len(wf.unresolved)} unresolved refs" if wf.unresolved else ""
    if n_hidden:
        extra = f", {n_hidden} hidden" + extra
    print(f"{dot_path}  ({len(wf.nodes)} calls, {edges} edges{extra})")
    if args.verbose and wf.unresolved:
        print(f"    unresolved: {' '.join(sorted(wf.unresolved))}", file=sys.stderr)
    for want, fmt, ex in ((args.svg, 'svg', []), (args.png, 'png', ['-Gdpi=150'])):
        if want:
            t = render(dot_path, wf.name, outdir, fmt, ex)
            if t:
                print(f"{t}")
    return True


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('wdl', nargs='*')
    ap.add_argument('--all', metavar='DIR',
                    help='process every .wdl found under DIR')
    ap.add_argument('-o', '--outdir',
                    help='output dir (default: a docs/ beside the WDL if it exists, '
                         'else beside the WDL)')
    ap.add_argument('--svg', action='store_true')
    ap.add_argument('--png', action='store_true')
    ap.add_argument('--check', action='store_true',
                    help='exit 1 if a committed .dot is stale; writes nothing')
    ap.add_argument('--expand-cases', type=int, default=4, metavar='N',
                    help='draw a scatter over a literal list of up to N named items as one '
                         'branch per item (default 4; 0 disables). Chromosome-style data '
                         'parallelism is never expanded.')
    ap.add_argument('--hide', action='append', metavar='NAME[,NAME...]',
                    help='leave these calls out as technical detail, by task name or by '
                         'call alias; dependencies are spliced through them. Repeatable.')
    ap.add_argument('--hide-file', metavar='FILE',
                    help='read hidden names from FILE, one per line, # comments allowed '
                         '(default: <workflow>.flow.hide beside the WDL, if it exists)')
    ap.add_argument('--show-all', action='store_true',
                    help='ignore --hide and any .flow.hide file; draw every call')
    ap.add_argument('-v', '--verbose', action='store_true',
                    help='list dependency names that could not be resolved')
    ap.add_argument('--version', action='version', version=__version__)
    args = ap.parse_args()

    targets = list(args.wdl)
    if args.all:
        for root, _, files in os.walk(args.all):
            targets += [os.path.join(root, f) for f in sorted(files)
                        if f.endswith('.wdl')]
    if not targets:
        ap.error('give at least one .wdl, or --all DIR')

    ok = True
    for t in targets:
        try:
            ok = process(t, args) and ok
        except Exception as exc:                                  # noqa: BLE001
            print(f"{t}: {type(exc).__name__}: {exc}", file=sys.stderr)
            ok = False
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
