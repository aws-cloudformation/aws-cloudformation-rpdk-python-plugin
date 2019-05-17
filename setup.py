#!/usr/bin/env python
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
    name="aws-cloudformation-rpdk-python-plugin",
    version=find_version("python", "rpdk", "python", "__init__.py"),
    description=__doc__,
    long_description=read("README.md"),
    author="Amazon Web Services",
    url="https://aws.amazon.com/cloudformation/",
    # https://packaging.python.org/guides/packaging-namespace-packages/
    packages=["rpdk.python"],
    package_dir={"": "python"},
    # package_data -> use MANIFEST.in instead
    include_package_data=True,
    zip_safe=True,
    install_requires=["aws-cloudformation-rpdk>=0.1,<0.2", "docker>=3.7,<3.8"],
    entry_points={"rpdk.v1.languages": [
        "python37 = rpdk.python.codegen:Python37LanguagePlugin",
        "python36 = rpdk.python.codegen:Python36LanguagePlugin"
    ]},
    license="Apache License 2.0",
    classifiers=(
        "Development Status :: 2 - Pre-Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: Apache Software License",
        "Natural Language :: English",
        "Topic :: Software Development :: Build Tools",
        "Topic :: Software Development :: Code Generators",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
    ),
    keywords="Amazon Web Services AWS CloudFormation",
)
