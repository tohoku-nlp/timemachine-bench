import sys
import json
import argparse

from tqdm import tqdm
from pathlib import Path

from utils.ast_utils import ast_find_related_module
from utils.code_utils import build_local_module_set

def get_error_related_modules(target_repo_dir, error_lst):
    related_modules = []
    local_modules = build_local_module_set(target_repo_dir)

    for error_info in error_lst:
        container_path = error_info["path"]
        line_no = error_info["lineno"]

        # the "target_repo_dir" is mounted to the container as "/work"
        # so remove the "/work" prefix if exists
        rel_path = container_path.removeprefix("/work/")
        path = target_repo_dir / rel_path

        try:
            if not path.exists():
                print(f"The file {rel_path} does not exist, skip.", file=sys.stderr)
                continue
        except Exception:
            print(f"An error occurred while processing the file {rel_path}, skip.", file=sys.stderr)
            continue

        related_module = ast_find_related_module(path, line_no, local_modules)

        if related_module:
            related_modules.append(related_module)
        else:
            print(f"No related module found for {rel_path} at line {line_no}.", file=sys.stderr)

    related_modules = list(set(related_modules))

    return related_modules

def get_total_loc(target_repo_dir):
    py_file_count = 0
    total_loc = 0

    for path in target_repo_dir.rglob("*.py"):
        if path.is_file():
            py_file_count += 1
            with open(path) as f:
                total_loc += sum(1 for _ in f)

    return py_file_count, total_loc

def main(args):
    input_path = args.input_path
    save_path = args.save_path

    repo_dir_root = args.repo_dir_root

    new_repo_dir_root = repo_dir_root / "new"

    with open(input_path) as f_in, open(save_path, "w") as f_out:
        for line in tqdm(f_in):
            line = line.strip()
            repo_dic = json.loads(line)

            repo_name = repo_dic["repo_name"]

            save_dir_name = repo_name.replace("/", "__")
            target_repo_dir = new_repo_dir_root / save_dir_name

            # error-related modules
            # this contains some noise but may be useful to filter out trivial errors
            # we annotated manually for Verified subset instead
            error_cause = repo_dic["error_cause"]
            related_modules = get_error_related_modules(target_repo_dir, error_cause)

            py_file_count, total_loc = get_total_loc(target_repo_dir)

            repo_dic["related_modules"] = related_modules
            repo_dic["py_file_count"] = py_file_count
            repo_dic["total_loc"] = total_loc

            print(json.dumps(repo_dic, ensure_ascii=False), file=f_out)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='filter repositories based on the logs of the tests (where the tests are seemed to be impossible to fix within the repository)')
    parser.add_argument('--repo_dir_root', type=Path, required=True, help="the path to the directory where processed repositories are stored (with 'old' and 'new' subdirectories)")
    parser.add_argument('--input_path', type=Path, required=True, help="the path to the input file with candidate repositories")
    parser.add_argument('--save_path', type=Path, required=True, help="the path to save output")

    args = parser.parse_args()
    main(args)
