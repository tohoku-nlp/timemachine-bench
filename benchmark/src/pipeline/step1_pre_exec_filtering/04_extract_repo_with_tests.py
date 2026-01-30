import sys
import json
import argparse
from tqdm import tqdm
from pathlib import Path

def check_test_import(py_files, root):
    test_info = []

    for rel_path in py_files:
        path = root / rel_path

        with open(path) as f:
            content = f.read()

            if "import pytest" in content:
                test_info.append({
                    "path": rel_path,
                    "test_type": "pytest"
                })
            elif "unittest" in content and "TestCase" in content:
                test_info.append({
                    "path": rel_path,
                    "test_type": "unittest"
                })

    return test_info

def main(args):
    input_path = args.input_path
    save_path = args.save_path

    with open(input_path) as f_in, open(save_path, "w") as f_out:
        for line in tqdm(f_in):
            line = line.strip()
            line_dic = json.loads(line)

            repo_name = line_dic["repo_name"]
            save_dir_name = repo_name.replace("/", "__")

            repo_dir = args.repo_dir_root / save_dir_name

            try:
                if not repo_dir.exists():
                    print(f"Repository {repo_name} does not exist, skipped.", file=sys.stderr)
                    continue

                # filter by extension
                py_files = [str(path.relative_to(repo_dir)) for path in repo_dir.rglob("*.py") if path.is_file()]
                # exclude if the path is under "site-packages"
                py_files = [path for path in py_files if "site-packages" not in path]

                test_info = check_test_import(py_files, root=repo_dir)
            except Exception:
                print(f"An error occurred while processing repository {repo_name}", file=sys.stderr)
                continue

            if not test_info:
                print(f"No test imports found in {repo_name}, skipped.", file=sys.stderr)
                continue

            line_dic["available_tests"] = test_info

            print(json.dumps(line_dic, ensure_ascii=False), file=f_out, flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='extract repositories with test imports')
    parser.add_argument('--input_path', type=Path, required=True, help="the path to the input file with candidate repositories")
    parser.add_argument('--repo_dir_root', type=Path, required=True, help="the path to raw (cloned) repositories")
    parser.add_argument('--save_path', type=Path, required=True, help="the path to save output")

    args = parser.parse_args()
    main(args)
