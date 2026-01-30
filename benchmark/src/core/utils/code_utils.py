import re
from pathlib import Path

from utils.const import REGEX_CODEBLOCK, REGEX_UNITTEST
from utils.const import SCRIPT_PREFIX, SETUP_MARKER, TEST_MARKER

def build_local_module_set(root_dir):
    """
    Build a set of local module names from repository structure.
    """
    local_modules = []

    if isinstance(root_dir, str):
        root_dir = Path(root_dir)

    if not root_dir.is_dir():
        raise ValueError(f"{root_dir} is not a valid directory.")

    for path in root_dir.rglob("*.py"):
        if path.is_file():
            rel_path = path.relative_to(root_dir)

            if rel_path.name == "__init__.py":
                module_path = str(rel_path.parent).replace("/", ".")
            else:
                module_path = str(rel_path).removesuffix(".py").replace("/", ".")

            local_modules.append(module_path)

            parts = module_path.split(".")
            for i in range(1, len(parts)):
                local_modules.append(".".join(parts[:i]))

    local_modules = set(local_modules)

    return local_modules

def extract_codeblock(txt):
    """
    Extract a code block surrounded by triple backquotes from the given text
    """
    txt = txt.strip()

    match = REGEX_CODEBLOCK.match(txt)

    if not match:
        # return empty string if no code block is found
        return ""

    codeblock = match.group("content").strip()

    return codeblock

def split_script_by_section(txt):
    """
    Split the script into setup and test sections based on the presence of'# Setup' and '# Testing' keywords.
    """

    # simple string match based on markers
    try:
        setup_start_index = txt.index(SETUP_MARKER)
        test_start_index = txt.index(TEST_MARKER, setup_start_index)

        setup_section = txt[setup_start_index+len(SETUP_MARKER):test_start_index].strip()
        test_section = txt[test_start_index+len(TEST_MARKER):].strip()

        setup_script = f"{SCRIPT_PREFIX}\n\n{setup_section}"
        test_script = f"{SCRIPT_PREFIX}\n\n{test_section}"

        return {
            "setup_script": setup_script,
            "test_script": test_script
        }

    except Exception:
        return {
            "setup_script": "",
            "test_script": ""
        }

def overwrite_unittest_script_with_paths(original_script, test_paths):
    # overwrite the given test script so that the test runner can find the test files
    # `python -m unittest {any}` to `python -m unittest {test_path1} {test_path2} ...`
    test_command = re.search(REGEX_UNITTEST, original_script)

    if not test_command:
        # fallback to the original script if no unittest command is found
        return original_script

    # remove ".py" extension and replace "/" with "."
    test_paths = [path.removesuffix(".py").replace("/", ".") for path in test_paths]
    test_path_str = " ".join(test_paths)

    new_command = f"python -m unittest {test_path_str}"
    new_script = original_script.replace(test_command.group(0), new_command)

    return new_script
