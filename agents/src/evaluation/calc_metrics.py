import re
import json
import argparse
from pathlib import Path
from itertools import groupby
from collections import defaultdict

# regex for log analysis
regex_ai_message = re.compile(r"^====={5,} Ai Message ====={5,}$")
regex_num_llm_calls = re.compile(r"^Current num_llm_calls: (\d+)$", re.MULTILINE)
regex_num_executed_tests = re.compile(r"^Current num_executed_tests: (\d+)$", re.MULTILINE)
regex_input_tokens = re.compile(r"^Total input tokens: (\d+)$", re.MULTILINE)
regex_output_tokens = re.compile(r"^Total output tokens: (\d+)$", re.MULTILINE)

# regex for diff parsing
regex_file_separator = re.compile(r'(?=^--- )', re.MULTILINE)
regex_file_header = re.compile(r"^--- ([^\t\n]+)$")
regex_diff_header_start = re.compile(r"(?=^@@ )", re.MULTILINE)
regex_diff_header = re.compile(r"^@@ \-(\d+)(?:,(\d+))? \+\d+(?:,\d+)? @@")


def _extract_last_ai_message(log_file: Path):
    block_content = []
    with open(log_file) as f:
        for line in f:
            if regex_ai_message.match(line):
                block_content = []
            block_content.append(line)

    last_ai_message = "\n".join(block_content)
    return last_ai_message

def extract_stats_from_log(log_file: Path):
    last_ai_message = _extract_last_ai_message(log_file)

    num_llm_calls = regex_num_llm_calls.search(last_ai_message)
    num_executed_tests = regex_num_executed_tests.search(last_ai_message)

    total_input_tokens = regex_input_tokens.search(last_ai_message)
    total_output_tokens = regex_output_tokens.search(last_ai_message)

    return {
        "num_llm_calls": int(num_llm_calls.group(1)) if num_llm_calls else 0,
        "num_executed_tests": int(num_executed_tests.group(1)) if num_executed_tests else 0,
        "total_input_tokens": int(total_input_tokens.group(1)) if total_input_tokens else 0,
        "total_output_tokens": int(total_output_tokens.group(1)) if total_output_tokens else 0,
    }

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
    input_path = args.input_path
    experiment_dir = args.experiment_dir

    log_dir = experiment_dir / "log"
    flag_dir = experiment_dir / "flag"

    gold_patch_dir = experiment_dir / "asset" / "gold_patch"
    model_patch_dir = experiment_dir / "diff_patch" / "main"

    save_path = experiment_dir / "evaluation_summary.json"

    success_count = 0
    prec_values = []

    with open(input_path) as f:
        for i, line in enumerate(f, start=1):
            line = line.strip()
            line_dic = json.loads(line)

            repo_name = line_dic["repo_name"]
            escaped_repo_name = repo_name.replace("/", "__")

            log_path = log_dir / f"log_{escaped_repo_name}.txt"
            flag_path = flag_dir / f"success_{escaped_repo_name}.txt"

            gold_patch_path = gold_patch_dir / f"{escaped_repo_name}.patch"
            model_patch_path = model_patch_dir / f"{escaped_repo_name}.patch"

            gold_edits = extract_edits_from_diff(gold_patch_path)
            model_edits = extract_edits_from_diff(model_patch_path)

            # for pass@1
            is_test_success = flag_path.exists()
            success_count += int(is_test_success)
            # for prec@1
            data_prec = calc_prec(gold_edits, model_edits)
            prec_values.append(data_prec)

            result = {"repo_name": repo_name, "is_test_success": is_test_success, "prec": data_prec}

            stats = extract_stats_from_log(log_path)
            result.update(stats)

            # flush to stdout
            print(json.dumps(result, ensure_ascii=False), flush=True)

    # summary
    total_repos = i
    pass1 = success_count / total_repos * 100
    prec1 = sum(prec_values) / total_repos * 100

    with open(save_path, "w") as f:
        summary = {"pass@1": pass1, "prec@1": prec1}
        print(json.dumps(summary, ensure_ascii=False), file=f)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="calculate metrics from experiment results")
    parser.add_argument("-i", "--input_path", type=Path, required=True, help="the path to the evaluation dataset (in jsonl)")
    parser.add_argument("-e", "--experiment_dir", type=Path, required=True, help="the path to the experiment directory")

    args = parser.parse_args()

    main(args)
