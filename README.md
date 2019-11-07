# wdl_doc_gen

A markdown documentation generator for WDL (https://github.com/openwdl/wdl).

## Installation
1. Install pipenv
```
pip install --user pipenv
```

1. Install wdl_doc_gen dependencies
```
pipenv install
```

1. Run tests
```
pipenv run python3 -m pytest
```

## Usage
```
pipenv shell
python3 generate_markdown_readme.py --input-wdl-path [workflow.wdl]
```

```
pipenv run generate_markdown_readme.py --input-wdl-path [workflow.wdl]
```

