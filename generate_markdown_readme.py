#!/usr/bin/env python3

import argparse

from workflow_info import *

parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument("--input-wdl-path", required=True)
args = parser.parse_args()

info = WorkflowInfo(args.input_wdl_path)

# header
print(f"# {info.name}\n")
print(f"{info.description}\n")

# overview
print("## Overview\n")
# generate docs/summary.png
# print("![Summary dot plot](./docs/summary.png)\n")

# dependencies
print("## Dependencies\n")
for dep in info.dependencies:
    print(f"* [{' '.join(dep['name'].split('/'))}]({dep['url']})")
print('\n')

# usage
print("## Usage\n")
print("### Cromwell")
print("```")
print(f"java -jar cromwell.jar run {info.filename} --inputs inputs.json")
print("```\n")

print("### Inputs\n")

# required
print("#### Required workflow parameters:")
print("Parameter|Value|Description")
print("---|---|---")
for param in info.required_inputs:
    print(f"`{param.name}`|{param.wdl_type}|{param.description}")
for param in info.task_inputs:
    if param.optional == False and param.default == "None":
        print(f"`{param.name}`|{param.wdl_type}|{param.description}")
print('\n')

# optional
print("#### Optional workflow parameters:")
print("Parameter|Value|Default|Description")
print("---|---|---|---")
for param in info.optional_inputs:
    print(f"`{param.name}`|{param.wdl_type}|{param.default}|{param.description}")
print('\n')

# task optional
print("#### Optional task parameters:")
print("Parameter|Value|Default|Description")
print("---|---|---|---")
for param in info.task_inputs:
    if param.optional == True or param.default != 'None':
        print(f"`{param.name}`|{param.wdl_type}|{param.default}|{param.description}")
print('\n')

# outputs
print("### Outputs\n")
print("Output | Type | Description")
print("---|---|---")
for output in info.outputs:
    print(f"`{output.name}`|{output.wdl_type}|{output.description}")
print('\n')

print("""## Niassa + Cromwell

This WDL workflow is wrapped in a Niassa workflow (https://github.com/oicr-gsi/pipedev/tree/master/pipedev-niassa-cromwell-workflow) so that it can used with the Niassa metadata tracking system (https://github.com/oicr-gsi/niassa).

* Building
```
mvn clean install
```

* Testing
```
mvn clean verify \\
-Djava_opts="-Xmx1g -XX:+UseG1GC -XX:+UseStringDeduplication" \\
-DrunTestThreads=2 \\
-DskipITs=false \\
-DskipRunITs=false \\
-DworkingDirectory=/path/to/tmp/ \\
-DschedulingHost=niassa_oozie_host \\
-DwebserviceUrl=http://niassa-url:8080 \\
-DwebserviceUser=niassa_user \\
-DwebservicePassword=niassa_user_password \\
-Dcromwell-host=http://cromwell-url:8000
```

## Support

For support, please file an issue on the [Github project](https://github.com/oicr-gsi) or send an email to gsi@oicr.on.ca .
""")

print(f"_Generated with generate-markdown-readme (https://github.com/oicr-gsi/gsi-wdl-tools/)_")
