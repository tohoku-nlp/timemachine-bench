import re

# regex
# pyproject.toml
REGEX_PYPROJECT_TOML = re.compile(r"(^|/)pyproject\.toml$")

# requirements.txt
REGEX_REQUIREMENTS_TXT = re.compile(r"(^|/)[\w-]*requirements([-_.]\w+)?\.(txt|pip)$")

# setup.py
REGEX_SETUP_PY = re.compile(r"(^|/)setup\.py$")

# lockfile
REGEX_LOCKFILE = re.compile(r"(^|/).*\.lock$")

# codeblocks
REGEX_CODEBLOCK = re.compile(r"^```(?:[^\n\r]*)(?:\r?\n)(?P<content>[\s\S]*?)```$")

# unittest
REGEX_UNITTEST = re.compile(r"python -m unittest .*$", re.MULTILINE)

# markers
SETUP_MARKER = "# ----- Setup -----"
TEST_MARKER = "# ----- Test -----"
SCRIPT_PREFIX = "#!/bin/bash\nset -euo pipefail"

# unpinning keywords
AST_SETUP_PY_VERSION_KEYWORDS = {"install_requires", "setup_requires", "tests_require", "extras_require"}

# pip options (from pip 25.0.1)
PIP_OPTIONS_WITH_ARGS = {
    "-r", "--requirement",
    "-c", "--constraint",
    "-e", "--editable",
    "-t", "--target",
    "--platform",
    "--python-version",
    "--implementation",
    "--abi",
    "--root",
    "--prefix",
    "--src",
    "--upgrade-strategy",
    "-C", "--config-settings",
    "--global-option",
    "--no-binary",
    "--only-binary",
    "--progress-bar",
    "--root-user-action",
    "--report",
    "-i", "--index-url",
    "--extra-index-url",
    "-f", "--find-links",
    "--python",
    "--log",
    "--keyring-provider",
    "--proxy",
    "--retries",
    "--timeout",
    "--exists-action",
    "--trusted-host",
    "--cert",
    "--client-cert",
    "--cache-dir",
    "--use-feature",
    "--use-deprecated"
}

# test parser
TEST_TIMEOUT_KEYWORD = "Test timed out"

# ===== FAILURES ===== / ===== ERRORS =====
REGEX_PYTEST_SECTION_HEADER = re.compile(r"^={5,}\s+(?P<header>.+?)\s+={5,}$")
# _____ test_xxx _____
REGEX_PYTEST_TEST_DELIMITER = re.compile(r"^_{5,}\s+(?P<filename>.+?)\s+_{5,}$")
# path/to/file.py:123
REGEX_PYTEST_TRACE_LINE = re.compile(r"^\s*(?P<path>[\w./-]+):(?P<lineno>\d+)")
# example: "E       AssertionError: ..." / ">       assert x == y"
REGEX_PYTEST_SUMMARY_LINE = re.compile(r"^[E>]\s+(?P<body>.*)$")
# ===== 2 passed, 1 failed in 0.001s =====
REGEX_PYTEST_STATS_LINE = re.compile(r"^=+\s+(?P<stats>.*?)\s+in\s+[\d\.]+(?:s|\s+seconds?).*\s+=+$")
# count by status
REGEX_PYTEST_COUNT_PATTERN = re.compile(r"(\d+)\s+(passed|failed|error|xfailed|xpassed)")
# collected 2 items
REGEX_COLLECTED_ITEMS = re.compile(r"^collected\s+(?P<count>\d+)\s+items?$")
# python file names
REGEX_PY_EXT = re.compile(r"^(?P<path>[\w./ -]+\.py)")

# FAIL: test_login (test_auth.AuthTests)
REGEX_UNITTEST_TEST_HEADER = re.compile(r"^(?P<type>FAIL|ERROR): (?P<test_name>\S+) \(.+\)$")
# File "/path/to/file.py", line 123
REGEX_UNITTEST_TRACE_LINE = re.compile(r'^\s*File "(?P<path>[\w./ -]+\.py)", line (?P<lineno>\d+)')
# =====
REGEX_UNITTEST_SEPARATOR_LINE = re.compile(r"^={5,}$")
# -----
REGEX_UNITTEST_SUB_SEPARATOR_LINE = re.compile(r"^-{5,}$")
# Ran X tests
REGEX_UNITTEST_SUMMARY_LINE = re.compile(r"^Ran (?P<count>\d+) tests?")

REGEX_TRACEBACK_LINE = re.compile(r"^Traceback \(most recent call last\):$")

# to standardize the name of errors type to pytest-style
ERROR_TYPE_MAP = {
    "ERROR": "ERRORS",
    "FAIL": "FAILURES"
}

REGEX_MODULE_NOT_FOUND = re.compile(r"ModuleNotFoundError: No module named '(?P<module>[\w-]+)'")
REGEX_REQUIRE_MODULE_INSTALL = re.compile(r"requires (?P<module>[\w-]+) to be installed")
