#!/bin/bash
set -euo pipefail

# Step 2: Runtime Environment Preparation

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
PROJECT_ROOT=$(dirname "${SCRIPT_DIR}")
SRC_DIR="${PROJECT_ROOT}/pipeline/step2_env_preparation"

function usage() {
    cat << EOM
usage: $(basename "$0") [OPTION]...
  -i INPUT_PATH    path to the step1 output jsonl file
  -v PY_VER_LIST_PATH    path to the csv file with Python versions
  -w WORK_DIR    path to the directory to save intermediate files
  -l LOG_DIR    path to the directory to save log files
  -r REPO_DIR   path to the directory to save repository files
  -s SAVE_DIR    path to the directory to save output files (used in subsequent steps)
EOM
  exit 1
}

INPUT_PATH=""
PY_VER_LIST_PATH=""
WORK_DIR=""
LOG_DIR=""
REPO_DIR=""
SAVE_DIR=""

while getopts ":i:v:w:l:r:s:h" optKey; do
  case "$optKey" in
    i )
      INPUT_PATH=${OPTARG}
      ;;
    v )
      PY_VER_LIST_PATH=${OPTARG}
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

if [ -z "${PY_VER_LIST_PATH}" ]; then
  echo -e "-v option is required"
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

fname_raw=`basename "${INPUT_PATH}" .jsonl`
# remove stepX_ prefix
fname_base=`echo "${fname_raw}" | sed -E 's/^step[0-9]+_//'`

mkdir -p "${SAVE_DIR}"

# Step 2-01: copy repositories twice and unpin requirements for experiments in new environments
mkdir -p "${LOG_DIR}/step2-01"
uv run bash "${SRC_DIR}/01_copy_and_unpin_repo.sh" \
  -i "${INPUT_PATH}" \
  -d "${REPO_DIR}" 2>&1 | tee -i "${LOG_DIR}/step2-01/${fname_base}.log"

# Step 2-02: select appropriate Python versions
mkdir -p "${LOG_DIR}/step2-02"
uv run bash "${SRC_DIR}/02_select_python_version_workflow.sh" \
  -i "${INPUT_PATH}" \
  -r "${RAW_REPO_DIR}" \
  -o "${WORK_DIR}/step2-02_${fname_base}.jsonl" \
  -v ${PY_VER_LIST_PATH} 2>&1 | tee -i "${LOG_DIR}/step2-02/${fname_base}.log"

# Step 2-03: generate test script
mkdir -p "${LOG_DIR}/step2-03"
uv run bash "${SRC_DIR}/03_generate_test_script_workflow.sh" \
  -i "${WORK_DIR}/step2-02_${fname_base}.jsonl" \
  -r "${RAW_REPO_DIR}" \
  -o "${SAVE_DIR}/step2_${fname_base}.jsonl" 2>&1 | tee -i "${LOG_DIR}/step2-03/${fname_base}.log"

# Step 2-04: copy generated setup / test scripts
mkdir -p "${LOG_DIR}/step2-04"
uv run bash "${SRC_DIR}/04_copy_setup_scripts.sh" \
  -i "${SAVE_DIR}/step2_${fname_base}.jsonl" \
  -d "${REPO_DIR}" 2>&1 | tee -i "${LOG_DIR}/step2-04/${fname_base}.log"

echo "Step 2: Runtime Environment Preparation completed. Output saved to ${SAVE_DIR}/step2_${fname_base}.jsonl"
