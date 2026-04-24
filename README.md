# gsi-wdl-tools

A collection of tools for working with WDL.

## Installation

Install into user's environment:
```
cd gsi-wdl-tools
uv tool install .
```

List installed tools:
```
uv tool list
```

To uninstall:
```
uv tool uninstall gsi-wdl-tools
```


## Development

gsi-wdl-tools requires `uv`

1. Install uv
See https://github.com/astral-sh/uv/releases

2. Install dependencies
```
cd gsi-wdl-tools
uv sync --frozen
```

3. Run tests
```
uv run pytest
```

## Maintenance

1. Use uv to update all dependencies to their latest version:
```
uv sync --upgrade && uv run pytest
```
If tests pass, changes to uv.lock should be committed and a PR be made.


## Tools

### generate-markdown-readme

Generates a readme for a WDL file that has been described with the following meta sections:
1. workflow meta
```
workflow myWorkflow {

  input {
    String input1
    String input2
  }

...

  output {
    File output1
    File? output2
  }

  parameter_meta {
    input1: "What is input1?"
    input2: "What is input2?"
  }

  meta {
    author: "???"
    email: "???"
    description: "What does the workflow do?"
    dependencies: [
      {
        name: "package1/0.1",
        url: "https://url_to_software"
      },
      {
        name: "package2/0.1",
        url: "https://url_to_software"
      }
    ]
    output_meta: {
      output1: What is output1?.",
      output2: "What is output2?."
    }
  }
}
```

1. task parameter meta
```
task myTask {

  input {
    String message
    String? fileName
  }

...

  parameter_meta {
    message: "What is message?"
    fileName: "What is fileName?"
  }
}
```

#### Usage

```
generate-markdown-readme --input-wdl-path [workflow.wdl]
```

Or with `uv run`:
```
uv run generate-markdown-readme --input-wdl-path [workflow.wdl]
```

### generate-subworkflow-import
Preprocesses a WDL to be used as a subworkflow, either for a UGE-based or dockstore-based wrapper workflow. Main function is converting task-level parameters to workflow-level parameters (pulling).
Tested on all workflows in the WGS Pipeline, but might not catch edge case WDL formatting.

#### Run Arguments
Argument|Required?|Description
---|---|---
`--input-wdl-path`|True|Source WDL path
`--tab-size`|False|Number of spaces in a tab
`--pull-json`|False|Path to json specifing which task-level parameters to pull. Exclusive with `--pull-all`
`--pull-all`|False|Whether or not to pull all variables. Exclusive with `--pull-json`
`--dockstore`|False|Whether or not to preprocess the WDL for Dockstore. Prereq of `--docker-image`
`--docker-image`|False|Docker image name and tag (or sha digest)
`--import-metas`|False|Whether or not to pull parameter_meta section from subworkflows
`--output-wdl-path`|False|Custom output WDL path. Defaults to the source WDL path plus a file prefix

#### Usage
Common combinations:
```
generate-subworkflow-import --docker-image "g3chen/wgspipeline:2.0" --input-wdl-path [workflow.wdl] --pull-all --dockstore --tab-size 4 --output-wdl-path [dockstore_workflow.wdl]
```
```
generate-subworkflow-import --input-wdl-path [workflow.wdl] --pull-all
```

Or with `uv run`:
```
uv run generate-subworkflow-import --input-wdl-path [workflow.wdl]
```