from itertools import groupby
from typing import List

from utils.custom_types import FailureReport, SectionReport, TestReport
from utils.const import (
    REGEX_PYTEST_SECTION_HEADER,
    REGEX_PYTEST_TEST_DELIMITER,
    REGEX_PYTEST_TRACE_LINE,
    REGEX_PYTEST_SUMMARY_LINE,
    REGEX_TRACEBACK_LINE,
    REGEX_PYTEST_STATS_LINE,
    REGEX_PYTEST_COUNT_PATTERN,
    REGEX_COLLECTED_ITEMS,
    REGEX_PY_EXT
)

from utils.unittest_parser import parse_single_failure as parse_single_failure_tracebacks

def parse_single_failure(failure_lines: List[str]) -> FailureReport:
    """
    extract files and summary from a single failure report
    "files" is a list of file paths related to the failure, and "summary" is the summary of the failure (usually starting with "E" or ">")
    """
    # extract related files in the order of their appearance
    files = []

    for line in failure_lines:
        match = REGEX_PYTEST_TRACE_LINE.match(line)
        if match:
            path = match.group("path").strip()
            lineno = match.group("lineno")
            files.append((path, lineno))

    summary_lines = []

    # the summary could be multiple lines
    for is_summary, group in groupby(
        failure_lines, key=lambda line: REGEX_PYTEST_SUMMARY_LINE.match(line) is not None
    ):
        if not is_summary:
            continue

        # overwrite the summary lines (to avoid false positives and keep the last block starting with "E" or ">")
        summary_lines = [REGEX_PYTEST_SUMMARY_LINE.match(line).group("body") for line in group]

    summary = "\n".join(summary_lines).strip() if summary_lines else "\n".join(failure_lines)

    return {"files": files, "summary": summary}

def parse_failure_section(section_lines: List[str]) -> SectionReport:
    """
    analyze the content of FAILURES or ERRORS section
    returns {test_name: {files: [...], summary: "..."}}
    """
    results: SectionReport = {}

    current_name = None
    line_buf = []

    for line in section_lines:
        match = REGEX_PYTEST_TEST_DELIMITER.match(line)
        if match:
            # if the line indicates a new test case
            if current_name is not None:
                results[current_name] = parse_single_failure(line_buf)
            # start of a new test case
            current_name = match.group("filename")
            line_buf = []
        else:
            if current_name is not None:
                line_buf.append(line)

    # process the last test case
    if current_name is not None:
        results[current_name] = parse_single_failure(line_buf)

    return results


def parse_pytest_log(log_file_path: str) -> TestReport:
    """
    parse pytest-style log file and return results by section (FAILURES/ERRORS)
    returns {"FAILURES": {test_name: {files, summary}}, "ERRORS": {...}}
    """
    with open(log_file_path, "r") as f:
        lines = [line.rstrip("\n") for line in f]

    report: TestReport = {}

    has_section_header = any(REGEX_PYTEST_SECTION_HEADER.match(line) for line in lines)

    if has_section_header:
        current_section = None

        line_buf = []

        for line in lines:
            match = REGEX_PYTEST_SECTION_HEADER.match(line)
            if match:
                # if the line indicates a new section
                if current_section is not None:
                    report[current_section] = parse_failure_section(line_buf)
                # start of a new section
                line_buf = []
                current_section = match.group("header") if match.group("header") in {"FAILURES", "ERRORS"} else None
            else:
                if current_section is not None:
                    line_buf.append(line)

        # process the last section
        if current_section is not None:
            report[current_section] = parse_failure_section(line_buf)
    else:
        # split by traceback markers (treat whole file as single error if no markers found)
        has_trackback_lines = any(REGEX_TRACEBACK_LINE.match(line) for line in lines)

        line_buf = []
        flg_traceback_started = False

        ct = 0

        if has_trackback_lines:
            for line in lines:
                match = REGEX_TRACEBACK_LINE.match(line)
                if not flg_traceback_started:
                    flg_traceback_started = True
                if match:
                    if line_buf:
                        if "ERRORS" not in report:
                            report["ERRORS"] = {}
                        # use unittest-style parser
                        report["ERRORS"][f"error_{ct}"] = parse_single_failure_tracebacks(line_buf)
                        ct += 1
                        line_buf = []
                elif flg_traceback_started:
                    line_buf.append(line)

            if line_buf:
                if "ERRORS" not in report:
                    report["ERRORS"] = {}
                report["ERRORS"][f"error_{ct}"] = parse_single_failure_tracebacks(line_buf)
        else:
            report["ERRORS"] = {}
            report["ERRORS"]["error_0"] = parse_single_failure(lines)

    return report

def get_pytest_executed_count(log_file_path):
    """
    extract the number of executed tests from a pytest log file
    """
    last_match = None

    with open(log_file_path) as f:
        for line in f:
            match = REGEX_PYTEST_STATS_LINE.match(line)
            if match:
                last_match = match

    if not last_match:
        return 0

    stats = last_match.group("stats").strip()

    count_matches = REGEX_PYTEST_COUNT_PATTERN.findall(stats)
    total_executed = sum(int(num) for num, _ in count_matches)

    return total_executed

def get_pytest_test_executed_files(log_file_path):
    """
    extract the names of files in which tests were executed
    """
    is_target_section = False

    line_buf = []

    with open(log_file_path) as f:
        for line in f:
            match = REGEX_PYTEST_SECTION_HEADER.match(line)
            if match:
                if match.group("header") == "test session starts":
                    line_buf = []
                    is_target_section = True
                else:
                    is_target_section = False
            else:
                if is_target_section:
                    line_buf.append(line)

    test_files = []

    if line_buf:
        line_buf_iter = iter(line_buf)

        for line in line_buf_iter:
            if REGEX_COLLECTED_ITEMS.match(line.strip()):
                break

        for line in line_buf_iter:
            match = REGEX_PY_EXT.match(line.strip())
            if match:
                test_files.append(match.group(0))

    test_files = list(set(test_files))

    return test_files
