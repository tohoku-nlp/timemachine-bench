#!/bin/bash
set -euo pipefail

# Step 4: Post-Execution Filtering

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
PROJECT_ROOT=$(dirname "${SCRIPT_DIR}")
SRC_DIR="${PROJECT_ROOT}/pipeline/step4_post_exec_filtering"

function usage() {
    cat << EOM
usage: $(basename "$0") [OPTION]...
  -i INPUT_PATH    path to the step3 output jsonl file
  -r REPO_DIR   path to the directory where repositories are saved
  -t TEST_LOG_DIR    path to the directory with test logs
  -e EXEC_LOG_DIR    path to the directory to save log files
  -s SAVE_DIR    path to the directory to save output files
EOM
  exit 1
}

INPUT_PATH=""
TEST_LOG_DIR=""
EXEC_LOG_DIR=""
SAVE_DIR=""
REPO_DIR=""

while getopts ":i:r:t:e:s:h" optKey; do
  case "$optKey" in
    i )
      INPUT_PATH=${OPTARG}
      ;;
    r )
      REPO_DIR=${OPTARG}
      ;;
    t )
      TEST_LOG_DIR=${OPTARG}
      ;;
    e )
      EXEC_LOG_DIR=${OPTARG}
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

if [ -z "${TEST_LOG_DIR}" ]; then
  echo -e "-t option is required"
  exit 1
fi

if [ -z "${EXEC_LOG_DIR}" ]; then
  echo -e "-e option is required"
  exit 1
fi

if [ -z "${SAVE_DIR}" ]; then
  echo -e "-s option is required"
  exit 1
fi

fname_raw=`basename "${INPUT_PATH}" .jsonl`
# remove stepX_ prefix
fname_base=`echo "${fname_raw}" | sed -E 's/^step[0-9]+_//'`

mkdir -p "${SAVE_DIR}"

DOCKERFILE_DIR="${REPO_DIR}/dockerfiles"
EXTRACTED_REPO_DIR="${SAVE_DIR}/full_data"
mkdir -p "${EXTRACTED_REPO_DIR}"

# Step 4-01: apply test log filter
mkdir -p "${EXEC_LOG_DIR}/step4-01"
uv run python "${SRC_DIR}/01_apply_test_log_filter.py" \
    --log_dir "${TEST_LOG_DIR}" \
    --input_path "${INPUT_PATH}" \
    --save_path "${SAVE_DIR}/step4_${fname_base}.jsonl" 2>&1 | tee "${EXEC_LOG_DIR}/step4-01/${fname_base}.log"

# Step 4-02: copy repository files and Dockerfiles
uv run bash "${SRC_DIR}/02_save_target_repositories.sh" \
  -i "${SAVE_DIR}/step4_${fname_base}.jsonl" \
  -r "${REPO_DIR}" \
  -d "${DOCKERFILE_DIR}" \
  -o "${EXTRACTED_REPO_DIR}"

echo "Step 4: Post-Execution Filtering completed. Output saved to ${SAVE_DIR}/step4_${fname_base}.jsonl"
