# AWS CloudFormation Resource Provider Python Plugin

The CloudFormation CLI (cfn) allows you to author your own resource providers that can be used by CloudFormation.

This plugin library helps to provide Python runtime bindings for the execution of your providers by CloudFormation.

## AWS CloudFormation Resource Provider Python Plugin

The CloudFormation Resource Provider Development Kit (RPDK) allows you to author your own resource providers that can be used by CloudFormation.

This plugin library helps to provide runtime bindings for the execution of your providers by CloudFormation.

[![Build Status](https://travis-ci.com/aws-cloudformation/cloudformation-cli-python-plugin.svg?branch=main)](https://travis-ci.com/aws-cloudformation/cloudformation-cli-python-plugin)

## Community

Join us on Discord! Connect & interact with CloudFormation developers &
experts, find channels to discuss and get help for our CLIs, cfn-lint, CloudFormation registry, StackSets,
Guard and more:

[![Join our Discord](https://discordapp.com/api/guilds/981586120448020580/widget.png?style=banner3)](https://discord.gg/9zpd7TTRwq)

Installation
------------

```bash
pip install cloudformation-cli-python-plugin
```

Howto
-----

```
$ cfn init
Initializing new project
What's the name of your resource type?
(Organization::Service::Resource)
>> Foo::Bar::Baz
Select a language for code generation:
[1] java
[2] csharp
[3] python38
[4] python39
[5] python310
[6] python311
[7] python312
(enter an integer):
>> 4
Use docker for platform-independent packaging (Y/n)?
This is highly recommended unless you are experienced
with cross-platform Python packaging.
>> y
Initialized a new project in <>
$ cfn submit --dry-run
$ cat <<EOT > test.json
{
  "credentials": {
    "accessKeyId": "",
    "secretAccessKey": "",
    "sessionToken": ""
  },
  "action": "CREATE",
  "request": {
    "clientRequestToken": "ecba020e-b2e6-4742-a7d0-8a06ae7c4b2b",
    "desiredResourceState": {
      "Title": "This_Is_The_Title_For_My_Example",
      "TestCode": "NOT_STARTED"
    },
    "previousResourceState": null,
    "logicalResourceIdentifier": null
  },
  "callbackContext": null
}
EOT
$ sam local invoke TestEntrypoint --event test.json
```

Development
-----------

For changes to the plugin, a Python virtual environment is recommended. The development requirements can be sourced from the core repository:

```
python3 -m venv env
source env/bin/activate
pip install -e . -e src/ \
  -r https://raw.githubusercontent.com/aws-cloudformation/cloudformation-cli/master/requirements.txt
pre-commit install
```

Linting and running unit tests is done via [pre-commit](https://pre-commit.com/), and so is performed automatically on commit. The continuous integration also runs these checks. Manual options are available so you don't have to commit):

```
# run all hooks on all files, mirrors what the CI runs
pre-commit run --all-files
# run unit tests only. can also be used for other hooks, e.g. black, flake8, pylint-local
pre-commit run pytest-local
```

License
-------

This library is licensed under the Apache 2.0 License.
