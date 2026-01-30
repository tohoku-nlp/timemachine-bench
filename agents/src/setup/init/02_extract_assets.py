import json
import argparse
from pathlib import Path

def main(args):
    input_path = args.input_path
    save_dir = args.save_dir

    # dockerfile
    dockerfile_dir = save_dir / "dockerfile"

    # dependency versions
    dep_versions_txt_dir = save_dir / "dep_versions_txt"

    # test files list
    test_files_txt_dir = save_dir / "test_files_txt"

    # patches
    init_patch_dir = save_dir / "init_patch"
    test_patch_dir = save_dir / "test_patch"
    gold_patch_dir = save_dir / "gold_patch"

    dockerfile_dir.mkdir(parents=True, exist_ok=True)
    dep_versions_txt_dir.mkdir(parents=True, exist_ok=True)
    test_files_txt_dir.mkdir(parents=True, exist_ok=True)
    init_patch_dir.mkdir(parents=True, exist_ok=True)
    test_patch_dir.mkdir(parents=True, exist_ok=True)
    gold_patch_dir.mkdir(parents=True, exist_ok=True)

    with open(input_path, newline="") as f_in:
        for line in f_in:
            line = line.strip()
            line_dic = json.loads(line)

            repo_name = line_dic["repo_name"]
            save_name = repo_name.replace("/", "__")

            dockerfile = line_dic["dockerfile"]
            dep_versions_txt = line_dic["dependency_versions"]

            test_files_txt = line_dic["test_files"]
            test_files_txt = "\n".join([p.strip() for p in test_files_txt.split(",") if p.strip()])
            test_files_txt += "\n"

            init_patch = line_dic["patch"]
            test_patch = line_dic["test_patch"]
            gold_patch = line_dic["gold_patch"]

            with open(dockerfile_dir / f"{save_name}.Dockerfile", "w", newline="") as f_out:
                f_out.write(dockerfile)

            with open(dep_versions_txt_dir / f"{save_name}_dep_versions.txt", "w", newline="") as f_out:
                f_out.write(dep_versions_txt)

            with open(test_files_txt_dir / f"{save_name}_test_files.txt", "w", newline="") as f_out:
                f_out.write(test_files_txt)

            with open(init_patch_dir / f"{save_name}.patch", "w", newline="") as f_out:
                f_out.write(init_patch)

            with open(test_patch_dir / f"{save_name}.patch", "w", newline="") as f_out:
                f_out.write(test_patch)

            with open(gold_patch_dir / f"{save_name}.patch", "w", newline="") as f_out:
                f_out.write(gold_patch)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='extract patches from jsonl and save to files')
    parser.add_argument('-i', '--input_path', type=Path, required=True, help="the path to the evaluation dataset (in jsonl)")
    parser.add_argument('-s', '--save_dir', type=Path, required=True, help="the path to save patches")

    args = parser.parse_args()
    main(args)