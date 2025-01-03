# gsi-wdl-tools

A collection of tools for working with WDL.

## Installation

gsi-wdl-tools requires Python 3.12

1. Install pipenv
```
pip install --user pipenv
```

2. Install dependencies
```
cd gsi-wdl-tools
PIPENV_VENV_IN_PROJECT=1 PIP_IGNORE_INSTALLED=1 pipenv install

# you can see that the project's venv is in the repo
pipenv --venv
```

3. Run tests
```
pipenv run python3 -m pytest
```

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

Or with `pipenv shell`:
```
pipenv shell
python3 ./scripts/generate_markdown_readme.py --input-wdl-path [workflow.wdl]
```

Or without using `pipenv run`:
```
pipenv run python3 ./scripts/generate_markdown_readme.py --input-wdl-path [workflow.wdl]
```


### dockstore_preprocess.py
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
dockstore_preprocess --docker-image "g3chen/wgspipeline:2.0" --input-wdl-path [workflow.wdl] --pull-all --dockstore --tab-size 4 --output-wdl-path [dockstore_workflow.wdl]
```
```
dockstore_preprocess --input-wdl-path [workflow.wdl] --pull-all
```

Or with `pipenv shell`:
```
pipenv shell
python3 dockstore_preprocess.py --input-wdl-path [workflow.wdl]
```

Or without using `pipenv run`:
```
pipenv run python3 ./dockstore_preprocess.py --input-wdl-path [workflow.wdl]
```


### dockstore_preprocess_all.sh
When given a directory containing WDL files and arguments, calls dockstore_preprocess.py on all files using those args. "--input-wdl-path" is omitted.

#### Run Arguments
Index|Argument|Description
---|---|---
1|dockstore_preprocess.py|Path to dockstore_preprocess.py
2|WDL dir|Path to directory containing target WDL files
3+|preprocess args|Arguments for dockstore_preprocess.py, minus --input-wdl-path

#### Usage
```
dockstore_preprocess_all.sh [dockstore_preprocess.py] [WDL dir] [preprocess args]
```
For example:
```
dockstore_preprocess_all.sh dockstore_preprocess.py /.../wgsPipeline/imports/ --pull-all --tab-size 4
```
