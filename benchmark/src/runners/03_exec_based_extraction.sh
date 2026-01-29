#!/bin/bash
set -euo pipefail

# Step 3: Execution-Based Candidate Extraction

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
PROJECT_ROOT=$(dirname "${SCRIPT_DIR}")
SRC_DIR="${PROJECT_ROOT}/pipeline/step3_exec_based_extraction"

function usage() {
    cat << EOM
usage: $(basename "$0") [OPTION]...
  -i INPUT_PATH    path to the step2 output jsonl file
  -r REPO_DIR   path to the directory where repositories are saved
  -l LOG_DIR    path to the directory to save log files
  -s SAVE_DIR    path to the directory to save output files (used in subsequent steps)
EOM
  exit 1
}

INPUT_PATH=""
REPO_DIR=""
SAVE_DIR=""

while getopts ":i:r:l:s:h" optKey; do
  case "$optKey" in
    i )
      INPUT_PATH=${OPTARG}
      ;;
    r )
      REPO_DIR=${OPTARG}
      ;;
    l )
      LOG_DIR=${OPTARG}
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

if [ -z "${REPO_DIR}" ]; then
  echo -e "-r option is required"
  exit 1
fi

if [ -z "${LOG_DIR}" ]; then
  echo -e "-l option is required"
  exit 1
fi

if [ -z "${SAVE_DIR}" ]; then
  echo -e "-s option is required"
  exit 1
fi

read -p "Are you sure you have a time-machine accessible from containers? (y/n): " answer

if [[ $answer == "y" ]]; then
  echo "Start processing..."
else
  echo "Please start a time-machine before running this script."
  exit 1
fi

DOCKERFILE_DIR="${REPO_DIR}/dockerfiles"
mkdir -p "${DOCKERFILE_DIR}"

TEST_LOG_DIR="${SAVE_DIR}/test_logs"
mkdir -p "${TEST_LOG_DIR}"

fname_raw=`basename "${INPUT_PATH}" .jsonl`
# remove stepX_ prefix
fname_base=`echo "${fname_raw}" | sed -E 's/^step[0-9]+_//'`

mkdir -p "${SAVE_DIR}"

# Step 3-01: generate Dockerfiles
mkdir -p "${LOG_DIR}/step3-01"
uv run bash "${SRC_DIR}/01_generate_dockerfiles.sh" \
  -i "${INPUT_PATH}" \
  -d "${REPO_DIR}" \
  -o "${DOCKERFILE_DIR}" 2>&1 | tee -i "${LOG_DIR}/step3-01/${fname_base}.log"

# Step 3-02: execute tests
mkdir -p "${LOG_DIR}/step3-02"
uv run bash "${SRC_DIR}/02_loop_test.sh" \
  -i "${INPUT_PATH}" \
  -r "${REPO_DIR}" \
  -d "${DOCKERFILE_DIR}" \
  -l "${TEST_LOG_DIR}" \
  -o "${SAVE_DIR}/step3_${fname_base}.jsonl" 2>&1 | tee -i "${LOG_DIR}/step3-02/${fname_base}.log"

echo "Step 3: Execution-Based Candidate Extraction completed. Output saved to ${SAVE_DIR}/step3_${fname_base}.jsonl"
