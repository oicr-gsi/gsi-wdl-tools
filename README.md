# gsi-wdl-tools

A collection of tools for working with WDL.

## Installation

gsi-wdl-tools requires Python 3.7

1. Install pipenv
```
pip install --user pipenv
```

1. Install dependencies
```
cd gsi-wdl-tools
pipenv install
```

1. Run tests
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
python3 generate_markdown_readme.py --input-wdl-path [workflow.wdl]
```

Or without using `pipenv run`:
```
pipenv run python3 ./generate_markdown_readme.py --input-wdl-path [workflow.wdl]
```
