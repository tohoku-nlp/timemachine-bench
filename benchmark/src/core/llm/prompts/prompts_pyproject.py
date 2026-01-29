# python version detection prompt
PYPROJECT_PY_VER_DETECTION_PROMPT = """
You are an experienced software engineer.
Your task is to configure a dev environment for the given repository in a container.

You will be provided with the `pyproject.toml` file of the repository.
Please read the document and determine the appropriate Python version range to run the software.

### Rules

- Do not make any assumptions about the repository

If the document does not provide any cues about supported Python versions, just output "N/A".

You may use information from:

1. `requires-python` field in the `[project]` section
2. `python` attribute associated with arbitrary package managers
3. `classifiers` field in the `[project]` section
(prioritize the former over the latter)

- The output must conform to the given version specifier format

A version specifier consists of a series of version clauses, separated by commas.

The valid operators to compose version clauses are:
    - `~=` (Compatible release)
    - `==` (Version maching)
    - `!=` (Version exclusion)
    - `<=`, `>=` (Inclusive ordered comparison)
    - `<`, `>` (Exclusive ordered comparison)
    - `===` (Arbitrary equality)

The caret operator (`^`) is not allowed here as it is not supported in PEP 440.
Please rewrite them using a combination of `>=` and `<` operators.
The caret operator is used to fix the leftmost non-zero digit in the major, minor, patch grouping.

For `classifiers` argument, please extract minor versions with explicit support.
If there exists consecutive minor versions listed in the argument, put them together.

For example,

- `Programming Language :: Python :: 3.8` means `>=3.8,<3.9`
- `Programming Language :: Python :: 3.8, Programming Language :: Python :: 3.9` means `>=3.8,<3.10`

### Output format

To sum up, the output must look like any of the following examples:

(Good)
- `N/A`
- `>=3.8,<3.10`

(Bad)
- `^3.8` (use `>=3.8,<4.0` instead)
- `The python version is not specified.` (use `N/A` instead)

No explanation is needed.

### Document

<pyproject_toml_files>
{pyproject_toml_content}
</pyproject_toml_files>
""".strip()

# test script generation prompt
PYPROJECT_TEST_SCRIPT_GENERATION_PROMPT = """
You are an experienced software engineer.
Your task is to configure a dev environment for the given repository in a container.

You will be provided with the `pyproject.toml` file of the repository.
Please generate a bash script to install the software and run provided unit tests.

### Preconditions

- Assume your current working directory is the repository root

### Rules

- Select appropriate package manager to install the software

Please check `[build-system]` section of the `pyproject.toml` file to infer which package manager is used in the repository.
Install the package manager with `pip install {{package_manager}}` command at the very beginning of the script to ensure the package manager is available in the container.
If there is no `[build-system]` section, assume the package manager is `pip` (you can skip the installation of the `pip` itself).

- All the dependencies must be under the management of the selected package manager

If the respository adopts any package manager other than `pip`, please ensure that all packages are installed under the management of the selected package manager.
For example, if the repository adopts `poetry`, you must not use `pip install` command once after `poetry` is installed.

- Install all dependencies including optional dependencies or extras

As a developer, it is preferable to install the package with full functionality.
Please find the names of optional dependency groups or extras in the `pyproject.toml` file to achieve this.
{test_installation_guide}
- Run unit tests under the management of the selected package manager

Please run the tests under the environment managed by the selected package manager.
Use the following command to run unit tests: `{fallback_test_command}`

- Write the setup and test commands in different sections, each starting with `# Setup` and `# Testing` respectively.

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

<pyproject_toml_files>
{pyproject_toml_content}
</pyproject_toml_files>
""".strip()
