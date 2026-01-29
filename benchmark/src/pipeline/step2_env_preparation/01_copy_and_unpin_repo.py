import re
import ast
import sys
import shutil
import tomlkit
import argparse
from pathlib import Path

from utils.ast_utils import ast_extract_func_kwargs, ast_find_variable_assignments
from utils.toml_utils import toml_find_all_tables, toml_is_primitive

from utils.requirement_utils import (
    unpin_single_package,
    unpin_pep_or_semver_requirements,
    ast_find_setup_call,
    ast_unpin_call_args,
    ast_unpin_dict_args
)

from utils.const import REGEX_PYPROJECT_TOML, REGEX_REQUIREMENTS_TXT, REGEX_SETUP_PY, REGEX_LOCKFILE

def unpin_requirements_txt(content):
    # remove line continuation markers
    content = re.sub(r'\\\n\s*', ' ', content)

    lines = []

    for line in content.splitlines():
        line = line.strip()

        opt = None

        if not line or line.startswith("#"):
            lines.append(line)
            continue

        if line.startswith(("--index-url", "-i")):
            raise Exception("Index urls found in the requirements.txt.")

        if line.startswith("--extra-index-url"):
            raise Exception("Extra index urls found in the requirements.txt.")

        if line.startswith(("--constraint", "-c")):
            # remove constraints
            continue

        if line.startswith(("--requirement", "-r")):
            lines.append(line)
            continue

        if line.startswith(("--editable", "-e")):
            # flag to indicate editable install
            opt, line = line.split(maxsplit=1)

        # remove inline comment
        line = line.split('#', 1)[0].strip()

        # remove hash
        if line.find("--hash") >= 0:
            line = line[:line.find("--hash")].strip()

        package_name = unpin_single_package(line)

        # keep editable install flag
        if opt:
            package_name = f"{opt} {package_name}"

        lines.append(package_name)

    return "\n".join(lines)

def unpin_pyproject_toml(content):
    try:
        data = tomlkit.loads(content)
    except Exception:
        raise

    for table_data in toml_find_all_tables(data):

        path, table = table_data
        path = list(map(str, path))

        for k, v in table.items():
            if any((x in k) for x in {"requires", "dependencies", "extras"}):
                # if the value itself is primitive (string, integer...) or the value is a list of primitives
                if toml_is_primitive(v):
                    if k == "requires-python":
                        # deleting constraint on Python can cause issues on dependency resolution
                        table[k] = unpin_pep_or_semver_requirements(v)
                    # if the key includes one of `requires`, `dependencies`, `extras`
                    elif isinstance(v, str):
                        table[k] = "*"
                    elif isinstance(v, (tomlkit.items.Array, list)):
                        package_lst = [unpin_single_package(el) for el in v if el != "python"]
                        table[k] = package_lst

        if any((x in p) for p in path for x in {"requires", "dependencies", "extras"}):
            # if the name of the table includes one of `requires`, `dependencies`, `extras`
            if isinstance(table, tomlkit.items.InlineTable):
                # dict-like (ex. packagename = {version=1.0, source=...})
                if "source" in table.keys():
                    raise Exception("Extra index urls found in requirements.txt.")

                if "url" in table.keys() or "git" in table.keys():
                    raise Exception("Package outside standard package manager found in requirements.txt.")

                for k, v in table.items():
                    if toml_is_primitive(v):
                        if k == "python":
                            table[k] = unpin_pep_or_semver_requirements(v)
                        if k in {"version", "markers"}:
                            table[k] = "*"
            else:
                # list-like
                for k, v in table.items():
                    if toml_is_primitive(v):
                        if k == "python":
                            table[k] = unpin_pep_or_semver_requirements(v)
                        elif isinstance(v, str):
                            table[k] = "*"
                        elif isinstance(v, (tomlkit.items.Array, list)):
                            package_lst = [unpin_single_package(el) for el in v if el != "python"]
                            table[k] = package_lst

    return tomlkit.dumps(data)

def unpin_setup_py(content):
    try:
        tree = ast.parse(content)
    except Exception:
        raise

    setup_call = ast_find_setup_call(tree)

    if setup_call is None:
        raise Exception("No call of the setup function found in setup.py.")

    # handle direct arguments
    ast_unpin_call_args(tree, setup_call)

    # handle keyword arguments (setup(**kwargs))
    kwargs = ast_extract_func_kwargs(setup_call)

    if kwargs and hasattr(kwargs.value, 'id'):
        kwargs_var_name = kwargs.value.id
        for assign_node in ast_find_variable_assignments(tree, kwargs_var_name):
            if isinstance(assign_node.value, ast.Call) and assign_node.value.func.id == "dict":
                # dict(key=value) format
                ast_unpin_call_args(tree, assign_node.value)

            if isinstance(assign_node.value, ast.Dict):
                dict_node = assign_node.value
                keys_node, values_node = dict_node.keys, dict_node.values
                ast_unpin_dict_args(tree, keys_node, values_node)

    return ast.unparse(tree)

def main(args):
    raw_repo_dir = args.raw_repo_dir
    save_dir = args.save_dir

    # whether to unpin requirements
    flg_unpin_requirements = args.unpin_requirements

    # check if the directory exists
    try:
        if not raw_repo_dir:
            print(f"The specified path {raw_repo_dir} is not a directory, exit.")
            sys.exit(1)

        files = list(raw_repo_dir.rglob("*"))
    except Exception:
        print(f"An error occurred while processing the directory {raw_repo_dir}, exit.", file=sys.stderr)
        sys.exit(1)

    # if save_dir does not exist, create it
    try:
        save_dir.mkdir(parents=True)
    except Exception:
        print(f"Failed to create the directory {save_dir}, exit.")
        sys.exit(1)

    try:
        for file in files:

            if not file.is_file():
                continue

            relative_path = file.relative_to(raw_repo_dir)
            save_path = save_dir / relative_path

            # create parent directories if they do not exist
            save_path.parent.mkdir(parents=True, exist_ok=True)

            if flg_unpin_requirements:

                # remove lockfiles
                if REGEX_LOCKFILE.match(str(file)):
                    continue

                # check if the file is one of unpinning targets
                if REGEX_PYPROJECT_TOML.match(str("/" / relative_path)):
                    content = file.read_text(encoding="utf-8")
                    content = unpin_pyproject_toml(content)

                elif REGEX_REQUIREMENTS_TXT.search(str("/" / relative_path)):
                    content = file.read_text(encoding="utf-8")
                    content = unpin_requirements_txt(content)

                elif REGEX_SETUP_PY.match(str("/" / relative_path)):
                    content = file.read_text(encoding="utf-8")
                    content = unpin_setup_py(content)

                else:
                    # make a copy
                    shutil.copy(file, save_path)
                    # go to the next file
                    continue

                # save unpinned content
                save_path.write_text(content, encoding="utf-8")

            else:
                # make a copy
                # this is the same as just `cp -r` the directory
                shutil.copy(file, save_path)
    except Exception as e:
        # print original exception and exit with error code
        print(f"An error occurred while processing the repository: {e}, skipped", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='loop through repository and save unpinned requirements')
    parser.add_argument('--raw_repo_dir', type=Path, required=True, help="the path to the cloned (raw) repository")
    parser.add_argument('--save_dir', type=Path, required=True, help="the path to save processed repository")
    parser.add_argument('--unpin_requirements', action='store_true', help="whether to unpin requirements")

    args = parser.parse_args()
    main(args)
