# python version detection prompt
SETUP_PY_VER_DETECTION_PROMPT = """
You are an experienced software engineer.
Your task is to configure a dev environment for the given repository in a container.

You will be provided with the `setup.py` file of the repository.
Please read the document and determine the appropriate Python version range to run the software.

### Rules

- Do not make any assumptions about the repository.

If the document does not provide any cues about supported Python versions, just output "N/A".

You may use information from:

1. `python_requires` argument in the `setup()` function
2. `classifiers` argument in the `setup()` function
(prioritize the former over the latter)

- The output must conform to the given version specifier format.

A version specifier consists of a series of version clauses, separated by commas.

The valid operators to compose version clauses are:
    - `~=` (Compatible release)
    - `==` (Version maching)
    - `!=` (Version exclusion)
    - `<=`, `>=` (Inclusive ordered comparison)
    - `<`, `>` (Exclusive ordered comparison)
    - `===` (Arbitrary equality)

For `classifiers` argument, please extract minor versions with explicit support.
If there exists consecutive minor versions listed in the argument, put them together.

For example,

- `Programming Language :: Python :: 3.8` means `>=3.8,<3.9`
- `Programming Language :: Python :: 3.8, Programming Language :: Python :: 3.9` means `>=3.8,<3.10`

### Output format

To sum up, the output must look like any of the following examples:

- `N/A`
- `>=3.8,<3.10`

No explanation is needed.

### Document

<setup_py_document>
{setup_py_content}
</setup_py_document>
""".strip()

# test script generation prompt
SETUP_TEST_SCRIPT_GENERATION_PROMPT = """
You are an experienced software engineer.
Your task is to configure a dev environment for the given repository in a container.

You will be provided with the `setup.py` file of the repository.
Please generate a bash script to install the software and run provided unit tests.

### Preconditions

- Assume your current working directory is the repository root

### Rules

- Install all dependencies including extras

As a developer, it is preferable to install the package with full functionality.
Please find the names of extras in the `setup.py` file to achieve this.
The resulting installtion command should always look like: `pip install .[extra1,extra2,...(if any)]`.

- Any packages specified in the `tests_require` argument should be installed manually

The packages specified in the `tests_require` argument are not installed automatically.
Please add them manually via `pip install {{package_name1 package_name2...}}` command to ensure the installation of the test-time dependencies.
If they are specified by a requirements file, please use `pip install -r {{requirements_file}}` command.

- Use the following command to run unit tests: `{fallback_test_command}`

- Write the setup and test commands in different sections, each starting with `# Setup` and `# Testing` respectively

### Output Format

No explanation is needed.
Please provide the resulting bash script in the format below.

<output_format>
```bash
#!/bin/bash
set -euo pipefail

# ----- Setup -----
{{ setup_command }}

# ----- Test -----
{{ test_command }}
```
</output_format>

### Document

<setup_py_document>
{setup_py_content}
</setup_py_document>
""".strip()
