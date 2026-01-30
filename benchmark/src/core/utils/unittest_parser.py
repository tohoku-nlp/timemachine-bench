import re
from itertools import groupby
from typing import List

from utils.custom_types import FailureReport, TestReport

from utils.const import ERROR_TYPE_MAP
from utils.const import (
    REGEX_UNITTEST_TEST_HEADER,
    REGEX_UNITTEST_TRACE_LINE,
    REGEX_UNITTEST_SEPARATOR_LINE,
    REGEX_UNITTEST_SUB_SEPARATOR_LINE,
    REGEX_UNITTEST_SUMMARY_LINE,
    REGEX_TRACEBACK_LINE
)

def parse_single_failure(failure_lines: List[str]) -> FailureReport:
    """
    extract files and summary from a single failure report
    "files" is a list of file paths related to the failure, and "summary" is the summary of the failure ()
    """
    # extract related files in the order of their appearance
    files = []

    for line in failure_lines:
        match = REGEX_UNITTEST_TRACE_LINE.match(line)
        if match:
            path = match.group("path").strip()
            lineno = match.group("lineno")
            files.append((path, lineno))

    summary_lines = []

    last_traceback_idx = -1

    for i, line in enumerate(failure_lines):
        if REGEX_TRACEBACK_LINE.match(line):
            last_traceback_idx = i
            break

    if last_traceback_idx+1 < len(failure_lines):
        for line in failure_lines[last_traceback_idx+1:]:
            # if the line matches the traceback pattern or is indented, assume they are part of the traceback
            is_traceback = REGEX_UNITTEST_TRACE_LINE.match(line) is not None or line.startswith("  ")

            if is_traceback:
                continue
            else:
                summary_lines.append(line.strip())

    summary = "\n".join(summary_lines).strip()

    return {"files": files, "summary": summary}


def parse_unittest_log(log_file_path: str) -> TestReport:
    """
    parse unittest-style log file and return results by section (FAILURES/ERRORS)
    returns {"FAILURES": {test_name: {files, summary}}, "ERRORS": {...}}
    """
    with open(log_file_path, "r") as f:
        lines = [line.rstrip("\n") for line in f]

    # look for separator lines ("-----") and truncate if the next line is a test summary
    for i in range(len(lines)-1, 0, -1):
        if re.fullmatch(REGEX_UNITTEST_SUB_SEPARATOR_LINE, lines[i]):
            if i+1 < len(lines) and REGEX_UNITTEST_SUMMARY_LINE.match(lines[i+1]):
                lines = lines[:i]
                break

    report: TestReport = {}

    has_separator_line = any(re.fullmatch(REGEX_UNITTEST_SEPARATOR_LINE, line) for line in lines)

    if has_separator_line:
        for is_separator, group_iter in groupby(lines, key=lambda line: re.fullmatch(REGEX_UNITTEST_SEPARATOR_LINE, line) is not None):
            # skip separator lines
            if is_separator:
                continue

            # parse error messages
            content_lines = "\n".join(group_iter).rstrip().split("\n")

            # check if the first line starts with either FAIL or ERROR
            match = REGEX_UNITTEST_TEST_HEADER.match(content_lines[0])
            if not match:
                continue

            error_type = match.group("type")
            error_type = ERROR_TYPE_MAP[error_type]

            test_name = match.group("test_name")

            result = parse_single_failure(content_lines)

            if error_type not in report:
                report[error_type] = {}

            report[error_type][test_name] = result
    else:
        # split by traceback markers (treat whole file as single error if no markers found)
        has_trackback_lines = any(REGEX_TRACEBACK_LINE.match(line) for line in lines)

        line_buf = []
        flg_traceback_started = False

        ct = 0

        if has_trackback_lines:
            for line in lines:
                match = REGEX_TRACEBACK_LINE.match(line)
                if match:
                    if not flg_traceback_started:
                        flg_traceback_started = True
                    if line_buf:
                        if "ERRORS" not in report:
                            report["ERRORS"] = {}
                        # use unittest-style parser
                        report["ERRORS"][f"error_{ct}"] = parse_single_failure(line_buf)
                        ct += 1
                        line_buf = []
                elif flg_traceback_started:
                    line_buf.append(line)

            if line_buf:
                if "ERRORS" not in report:
                    report["ERRORS"] = {}
                report["ERRORS"][f"error_{ct}"] = parse_single_failure(line_buf)
        else:
            report["ERRORS"] = {}
            report["ERRORS"]["error_0"] = parse_single_failure(lines)

    return report

def get_unittest_executed_count(log_file_path):
    """
    extract the number of executed tests from a pytest log file
    """
    last_match = None

    with open(log_file_path) as f:
        for line in f:
            match = REGEX_UNITTEST_SUMMARY_LINE.match(line)
            if match:
                last_match = match

    if not last_match:
        return 0

    total_executed = int(last_match.group("count"))

    return total_executed
