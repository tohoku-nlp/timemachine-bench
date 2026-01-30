import sys
import json
import argparse

from tqdm import tqdm
from pathlib import Path

from utils.const import TEST_TIMEOUT_KEYWORD
from utils.const import REGEX_MODULE_NOT_FOUND, REGEX_REQUIRE_MODULE_INSTALL
from utils.pytest_parser import parse_pytest_log, get_pytest_executed_count, get_pytest_test_executed_files
from utils.unittest_parser import parse_unittest_log, get_unittest_executed_count

def check_no_timeout(log_path):
    line = ""
    with open(log_path) as f:
        for line in f:
            pass

    # check if the last line contains message indicating timeout
    line = line.strip()

    if TEST_TIMEOUT_KEYWORD in line:
        return False

    return True

def get_error_cause(log_report):
    """
    Check if the error occurs inside the main code of the repository, not in dependent modules.
    The errors in the code within the "site-packages" (but not "__init__.py") are considered as errors in dependent modules.
    """
    cause_dic_lst = []

    is_all_error_within_repo = True

    for section in log_report.keys():
        section_log = log_report[section]
        for _, details in section_log.items():
            is_error_within_repo = True

            files = details["files"]
            files_rev = iter(files[::-1])

            file = None
            for file, lineno in files_rev:
                if "/usr/local/lib/python" in file or "site-packages" in file:
                    if "__init__.py" not in file:
                        is_error_within_repo = False
                        break
                    continue
                else:
                    break

            try:
                while True:
                    if "/usr/local/lib/python" in file or "site-packages" in file:
                        if "__init__.py" in file:
                            file, lineno = next(files_rev)
                        else:
                            break
                    else:
                        break
            except Exception:
                pass

            if file:
                cause_dic = {
                    "path": file,
                    "lineno": int(lineno),
                    "summary": details["summary"]
                }
                cause_dic_lst.append(cause_dic)

                if "unittest" in cause_dic["path"] or "pytest" in cause_dic["path"]:
                    is_error_within_repo = False
            else:
                is_error_within_repo = False

            is_all_error_within_repo = is_all_error_within_repo and is_error_within_repo

    # deduplicate the cause_dic_lst
    deduped_cause_dic_lst = []
    seen_set = set()

    for cause_dic in cause_dic_lst:
        key = f"{cause_dic['path']}:{cause_dic['lineno']}, {cause_dic['summary']}"
        if key not in seen_set:
            seen_set.add(key)
            deduped_cause_dic_lst.append(cause_dic)

    return is_all_error_within_repo, deduped_cause_dic_lst

def check_error_no_contain_module_not_found(log_report):
    """
    Check if there is no ModuleNotFoundError in the log report.
    Only top-level imports (ex. "numpy", not "numpy.lib.polynomial") are considered.
    """
    for section in log_report.keys():
        section_log = log_report[section]
        for _, details in section_log.items():
            summary = details["summary"]
            if REGEX_MODULE_NOT_FOUND.search(summary):
                match = REGEX_MODULE_NOT_FOUND.search(summary)
                if "." not in match.group("module"):
                    return False
            # special cases
            # "requires * to be installed"
            if REGEX_REQUIRE_MODULE_INSTALL.search(summary):
                return False
            # "not natively supported"
            if "not natively supported" in summary:
                return False
    return True

def check_any_error_from_main_code(log_report, test_files):
    """
    Check if there exists one or more errors associated with the main code of the repository (not tests).
    """
    is_any_error_main = False

    for section in log_report.keys():
        section_log = log_report[section]
        for _, details in section_log.items():
            is_error_main = True

            files = details["files"]
            files_rev = iter(files[::-1])

            for file, lineno in files_rev:
                if "/usr/local/lib/python" in file or "site-packages" in file:
                    if "__init__.py" in file:
                        continue
                    is_error_main = False
                if file in test_files:
                    is_error_main = False
                if "conftest.py" in file:
                    # pytest configuration file
                    is_error_main = False
                break

            is_any_error_main = is_any_error_main or is_error_main

    return is_any_error_main

def main(args):
    input_path = args.input_path
    save_path = args.save_path
    log_dir = args.log_dir

    with open(input_path) as f_in, open(save_path, "w") as f_out:
        for line in tqdm(f_in):
            line = line.strip()
            repo_dic = json.loads(line)

            repo_name = repo_dic["repo_name"]

            save_dir_name = repo_name.replace("/", "__")

            old_log_path = log_dir / f"{save_dir_name}_old.log"
            new_log_path = log_dir / f"{save_dir_name}_new.log"

            try:
                if not old_log_path.exists() or not new_log_path.exists():
                    print(f"Test log not found for {repo_name}, skip.", file=sys.stderr)
                    continue
            except Exception:
                print(f"An error occurred while processing the logs for {repo_name}, skip.", file=sys.stderr)
                continue

            available_tests = repo_dic["available_tests"]
            # prioritize pytest over unittest
            testing_framework = "pytest" if any(x["test_type"] == "pytest" for x in available_tests) else "unittest"

            # check if there exists one or more tests ran in the old log
            get_executed_count = get_pytest_executed_count if testing_framework == 'pytest' else get_unittest_executed_count
            old_test_count = get_executed_count(old_log_path)

            if old_test_count == 0:
                print(f"No tests ran in the old version of the repository: {repo_name}, skip.", file=sys.stderr)
                continue

            # check if the test succeeded without timeout in the new log
            if not check_no_timeout(new_log_path):
                print(f"Tests timed out in the new version of the repository: {repo_name}, skip.", file=sys.stderr)
                continue

            # parse new test log with the corresponding parser
            test_parser = parse_pytest_log if testing_framework == 'pytest' else parse_unittest_log
            report = test_parser(new_log_path)

            # check if there are any errors in the log
            if not any(report[section] for section in report.keys()):
                print(f"No errors detected in the new version of the repository: {repo_name}, skip.", file=sys.stderr)
                continue

            # check if all the errors occurred inside the main code of the repository
            is_all_error_within_repo, cause_dic_lst = get_error_cause(report)

            if not is_all_error_within_repo:
                print(f"One or more errors occurred in dependent modules in the repository: {repo_name}, skip.", file=sys.stderr)
                continue

            # check if there is no ModuleNotFoundError
            if not check_error_no_contain_module_not_found(report):
                print(f"One or more ModuleNotFoundError found in the repository: {repo_name}, skip.", file=sys.stderr)
                continue

            # files extracted by simple string match (lightweight alternative to execution-based approach)
            tmp_test_files = [x["path"] for x in available_tests]

            if testing_framework == "pytest":
                test_files = get_pytest_test_executed_files(old_log_path) or tmp_test_files
            else:
                test_files = tmp_test_files

            test_files = list(set(test_files))

            # expand the list with their full paths
            extended_test_files = test_files + ["/work/" + path.lstrip("/") for path in test_files]

            is_any_error_main = check_any_error_from_main_code(report, extended_test_files)

            repo_dic["testing_framework"] = testing_framework
            repo_dic["test_files"] = test_files
            repo_dic["test_count"] = old_test_count
            repo_dic["is_any_error_main"] = is_any_error_main
            repo_dic["error_cause"] = cause_dic_lst

            # drop unnecessary (tentative) columns
            repo_dic.pop("available_tests")

            print(json.dumps(repo_dic, ensure_ascii=False), file=f_out)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='filter repositories based on the logs of the tests (where the tests are seemed to be impossible to fix within the repository)')
    parser.add_argument('--log_dir', type=Path, required=True, help="the path to the directory with logs")
    parser.add_argument('--input_path', type=Path, required=True, help="the path to the input file with candidate repositories")
    parser.add_argument('--save_path', type=Path, required=True, help="the path to save output")

    args = parser.parse_args()
    main(args)
