# python version detection prompt
README_PY_VER_DETECTION_PROMPT = """
You are an experienced software engineer.
Your task is to configure a dev environment for the given repository in a container.

You will be provided with the README document of the repository.
Please read the document and determine the appropriate Python version range to run the software.

### Rules

- Do not make any assumptions about the repository.

If the document does not provide any cues about supported Python versions, just output "N/A".

- The output must conform to the given version specifier format.

A version specifier consists of a series of version clauses, separated by commas.

The valid operators to compose version clauses are:
    - `~=` (Compatible release)
    - `==` (Version maching)
    - `!=` (Version exclusion)
    - `<=`, `>=` (Inclusive ordered comparison)
    - `<`, `>` (Exclusive ordered comparison)
    - `===` (Arbitrary equality)

### Output format

To sum up, the output must look like any of the following examples:

- `N/A`
- `>=3.8,<3.10`

No explanation is needed.

### Document

<readme_document>
{readme_content}
</readme_document>
""".strip()
