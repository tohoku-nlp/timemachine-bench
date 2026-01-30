#!/bin/bash
set -euo pipefail

# Step 1: Pre-Execution Filtering

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
PROJECT_ROOT=$(dirname "${SCRIPT_DIR}")
SRC_DIR="${PROJECT_ROOT}/pipeline/step1_pre_exec_filtering"

function usage() {
    cat << EOM
usage: $(basename "$0") [OPTION]...
  -i INPUT_PATH    path to the jsonl file with candidate repositories (Python, stars >= 1, allowed licenses)
  -w WORK_DIR    path to the directory to save intermediate files
  -l LOG_DIR    path to the directory to save log files
  -r REPO_DIR   path to the directory to save repository files
  -s SAVE_DIR    path to the directory to save output files (used in subsequent steps)
EOM
  exit 1
}

INPUT_PATH=""
WORK_DIR=""
LOG_DIR=""
REPO_DIR=""
SAVE_DIR=""

while getopts ":i:w:l:r:s:h" optKey; do
  case "$optKey" in
    i )
      INPUT_PATH=${OPTARG}
      ;;
    w )
      WORK_DIR=${OPTARG}
      ;;
    l )
      LOG_DIR=${OPTARG}
      ;;
    r )
      REPO_DIR=${OPTARG}
      ;;
    s )
      SAVE_DIR=${OPTARG}
      ;;
    '-h'|'--help'|* )
      usage
      ;;
  esac
done

if [ -z "${INPUT_PATH}" ]; then
  echo -e "-i option is required"
  exit 1
fi

if [ -z "${WORK_DIR}" ]; then
  echo -e "-w option is required"
  exit 1
fi

if [ -z "${LOG_DIR}" ]; then
  echo -e "-l option is required"
  exit 1
fi

if [ -z "${REPO_DIR}" ]; then
  echo -e "-r option is required"
  exit 1
fi

if [ -z "${SAVE_DIR}" ]; then
  echo -e "-s option is required"
  exit 1
fi

# remove the existing work directory and create a new one
rm -rf "${WORK_DIR}"
mkdir -p "${WORK_DIR}"

RAW_REPO_DIR="${REPO_DIR}/raw"
mkdir -p "${RAW_REPO_DIR}"

fname_raw=`basename "${INPUT_PATH}" .jsonl`
# remove stepX_ prefix
fname_base=`echo "${fname_raw}" | sed -E 's/^step[0-9]+_//'`

mkdir -p "${SAVE_DIR}"

# Step 1-01. clone repositories
mkdir -p "${LOG_DIR}/step1-01"
bash "${SRC_DIR}/01_clone_repo.sh" \
  -i "${INPUT_PATH}" \
  -o "${RAW_REPO_DIR}" 2>&1 | tee -i "${LOG_DIR}/step1-01/${fname_base}.log"

# Step 1-02. check encoding
mkdir -p "${LOG_DIR}/step1-02"
uv run bash "${SRC_DIR}/02_check_encoding.sh" \
  -i "${INPUT_PATH}" \
  -r "${RAW_REPO_DIR}" \
  -o "${WORK_DIR}/step1-02_${fname_base}.jsonl" 2>&1 | tee -i "${LOG_DIR}/step1-02/${fname_base}.log"

# Step 1-03: extract repositories with version management files
mkdir -p "${LOG_DIR}/step1-03"
uv run bash "${SRC_DIR}/03_extract_repos_with_version_mgmt_files.sh" \
  -i "${WORK_DIR}/step1-02_${fname_base}.jsonl" \
  -r "${RAW_REPO_DIR}" \
  -o "${WORK_DIR}/step1-03_${fname_base}.jsonl" 2>&1 | tee -i "${LOG_DIR}/step1-03/${fname_base}.log"

# Step 1-04. extract repositories with test cases
mkdir -p "${LOG_DIR}/step1-04"
uv run bash "${SRC_DIR}/04_extract_repo_with_tests.sh" \
  -i "${WORK_DIR}/step1-03_${fname_base}.jsonl" \
  -r "${RAW_REPO_DIR}" \
  -o "${SAVE_DIR}/step1_${fname_base}.jsonl" 2>&1 | tee -i "${LOG_DIR}/step1-04/${fname_base}.log"

echo "Step 1: Pre-Execution Filtering completed. Output saved to ${SAVE_DIR}/step1_${fname_base}.jsonl"
