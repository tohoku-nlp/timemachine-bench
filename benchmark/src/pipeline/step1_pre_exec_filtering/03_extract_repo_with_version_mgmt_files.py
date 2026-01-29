import sys
import json
import argparse
from tqdm import tqdm
from pathlib import Path

from utils.const import REGEX_PYPROJECT_TOML, REGEX_REQUIREMENTS_TXT, REGEX_SETUP_PY

def has_version_mgmt_files(rel_paths):
    for path in rel_paths:

        # Check if the file path matches any of the version management files
        # `pyproject.toml` and `setup.py` must be under the repository root
        if REGEX_PYPROJECT_TOML.match(path):
            return True
        if REGEX_REQUIREMENTS_TXT.search(path):
            return True
        if REGEX_SETUP_PY.match(path):
            return True

    return False

def main(args):
    input_path = args.input_path
    repo_dir_root = args.repo_dir_root
    save_path = args.save_path

    with open(input_path) as f_in, open(save_path, "w") as f_out:
        for line in tqdm(f_in):
            line = line.strip()
            line_dic = json.loads(line)

            repo_name = line_dic["repo_name"]
            save_dir_name = repo_name.replace("/", "__")

            repo_dir = repo_dir_root / save_dir_name

            try:
                if not repo_dir.exists():
                    print(f"Repository {repo_name} does not exist, skipped.", file=sys.stderr)
                    continue

                rel_paths = [str(path.relative_to(repo_dir)) for path in repo_dir.rglob("*") if path.is_file()]
            except Exception:
                print(f"An error occurred while processing repository {repo_name}", file=sys.stderr)
                continue

            if has_version_mgmt_files(rel_paths):
                print(json.dumps(line_dic, ensure_ascii=False), file=f_out, flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='extract repositories with version management files')
    parser.add_argument('--input_path', type=Path, required=True, help="the path to the input file with candidate repositories")
    parser.add_argument('--repo_dir_root', type=Path, required=True, help="the path to raw (cloned) repositories")
    parser.add_argument('--save_path', type=Path, required=True, help="the path to save output")

    args = parser.parse_args()
    main(args)
