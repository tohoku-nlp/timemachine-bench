import sys
import json
import argparse
from tqdm import tqdm
from pathlib import Path

def check_encoding(py_files, root):
    for rel_path in py_files:
        path = root / rel_path

        try:
            with open(path) as f:
                content = f.read()
        except Exception:
            # skip the whole repository
            print(f"Error reading file {rel_path}, skipped.", file=sys.stderr)
            return False

    return True

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

            # filter by extension
            try:
                if not repo_dir.exists():
                    print(f"Repository {repo_name} does not exist, skipped.", file=sys.stderr)
                    continue

                py_files = [str(path.relative_to(repo_dir)) for path in repo_dir.rglob("*.py") if path.is_file()]
            except Exception:
                print(f"An error occurred while processing repository {repo_name}", file=sys.stderr)
                continue

            if not check_encoding(py_files, repo_dir):
                print(f"Repository {repo_name} has encoding issues, skipped.", file=sys.stderr)
                continue

            print(json.dumps(line_dic, ensure_ascii=False), file=f_out, flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='extract repositories with test imports')
    parser.add_argument('--input_path', type=Path, required=True, help="the path to the input file with candidate repositories")
    parser.add_argument('--repo_dir_root', type=Path, required=True, help="the path to raw (cloned) repositories")
    parser.add_argument('--save_path', type=Path, required=True, help="the path to save output")

    args = parser.parse_args()
    main(args)
