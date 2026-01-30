import re
import json
import argparse
from pathlib import Path
from itertools import groupby
from collections import defaultdict

regex_file_separator = re.compile(r'(?=^--- )', re.MULTILINE)
regex_file_header = re.compile(r"^--- ([^\t\n]+)$")
regex_diff_header_start = re.compile(r"(?=^@@ )", re.MULTILINE)
regex_diff_header = re.compile(r"^@@ \-(\d+)(?:,(\d+))? \+\d+(?:,\d+)? @@")

def extract_edits_from_diff(patch_path: Path):
    with open(patch_path) as f:
        diff_text = f.read()

    edit_by_file_sets = defaultdict(set)

    file_diffs = regex_file_separator.split(diff_text)

    for file_diff in file_diffs:
        if not file_diff.strip():
            continue

        file_name = regex_file_header.match(file_diff.splitlines()[0]).group(1)

        diff_blocks = regex_diff_header_start.split(file_diff)

        for diff in diff_blocks:
            # skip file header
            if not diff.startswith("@@"):
                continue

            header, *content = diff.splitlines(keepends=True)
            header_match = regex_diff_header.match(header)

            if not header_match:
                continue

            current_line = int(header_match.group(1))

            for flg, grp in groupby(content, key=lambda x: x.startswith(('+', '-'))):
                grp_lines = list(grp)

                if not flg:
                    # skip unchanged lines
                    current_line += len(grp_lines)
                    continue

                is_deleted_or_modified = any(line.startswith('-') for line in grp_lines)

                if is_deleted_or_modified:
                    for line in grp_lines:
                        if line.startswith('-'):
                            edit_by_file_sets[file_name].add(current_line)
                            current_line += 1
                else:
                    # added, record line number where the code is inserted once
                    edit_by_file_sets[file_name].add(current_line)
                    continue

    return edit_by_file_sets

def calc_prec(gold_edits, model_edits):
    # expand the dict to make a set of "{file_name}_{line_number}" strings for comparison
    model_edits = {f"{file_name}_{line_number}" for file_name, lines in model_edits.items() for line_number in lines}
    gold_edits = {f"{file_name}_{line_number}" for file_name, lines in gold_edits.items() for line_number in lines}

    total_model_edits = len(model_edits)

    tp = len(model_edits.intersection(gold_edits))

    if total_model_edits == 0:
        # the model cannot make tests pass without edits
        prec = 0
    else:
        prec = tp / total_model_edits

    return prec


def main(args):
    repo_name = args.repo_name
    gold_patch_path = args.gold_patch_path
    model_patch_path = args.model_patch_path

    gold_edits = extract_edits_from_diff(gold_patch_path)
    model_edits = extract_edits_from_diff(model_patch_path)

    prec = calc_prec(gold_edits, model_edits)

    results = {"repo_name": repo_name, "prec": prec}

    print(json.dumps(results, ensure_ascii=False))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="extract diff lines and calculate precision")
    parser.add_argument("--repo_name", type=str, required=True, help="the name of the repository")
    parser.add_argument("--gold_patch_path", type=Path, required=True, help="path to the gold patch file")
    parser.add_argument("--model_patch_path", type=Path, required=True, help="path to the model-generated patch file")
    args = parser.parse_args()
    main(args)
