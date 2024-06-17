#!/usr/bin/env python
"""Python 3.6 and 3.7 language support for the CloudFormation CLI"""
import os.path
import re
from setuptools import setup

HERE = os.path.abspath(os.path.dirname(__file__))


def read(*parts):
    with open(os.path.join(HERE, *parts), "r", encoding="utf-8") as fp:
        return fp.read()


# https://packaging.python.org/guides/single-sourcing-package-version/
def find_version(*file_paths):
    version_file = read(*file_paths)
    version_match = re.search(r"^__version__ = ['\"]([^'\"]*)['\"]", version_file, re.M)
    if version_match:
        return version_match.group(1)
    raise RuntimeError("Unable to find version string.")


setup(
    name="cloudformation-cli-python-plugin",
    version=find_version("python", "rpdk", "python", "__init__.py"),
    description=__doc__,
    long_description=read("README.md"),
    long_description_content_type="text/markdown",
    author="Amazon Web Services",
    author_email="aws-cloudformation-developers@amazon.com",
    url="https://github.com/aws-cloudformation/aws-cloudformation-rpdk-python-plugin/",
    # https://packaging.python.org/guides/packaging-namespace-packages/
    packages=["rpdk.python"],
    package_dir={"": "python"},
    # package_data -> use MANIFEST.in instead
    include_package_data=True,
    zip_safe=True,
    python_requires=">=3.8",
    install_requires=[
        "cloudformation-cli>=0.2.26",
        "types-dataclasses>=0.1.5",
        "setuptools",
    ],
    entry_points={
        "rpdk.v1.languages": [
            "python312 = rpdk.python.codegen:Python312LanguagePlugin",
            "python311 = rpdk.python.codegen:Python311LanguagePlugin",
            "python310 = rpdk.python.codegen:Python310LanguagePlugin",
            "python39 = rpdk.python.codegen:Python39LanguagePlugin",
            "python38 = rpdk.python.codegen:Python38LanguagePlugin",
        ],
        "rpdk.v1.parsers": [
            "python312 = rpdk.python.parser:setup_subparser_python312",
            "python311 = rpdk.python.parser:setup_subparser_python311",
            "python310 = rpdk.python.parser:setup_subparser_python310",
            "python39 = rpdk.python.parser:setup_subparser_python39",
            "python38 = rpdk.python.parser:setup_subparser_python38",
        ],
    },
    license="Apache License 2.0",
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: Apache Software License",
        "Natural Language :: English",
        "Topic :: Software Development :: Build Tools",
        "Topic :: Software Development :: Code Generators",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    keywords="Amazon Web Services AWS CloudFormation",
)
