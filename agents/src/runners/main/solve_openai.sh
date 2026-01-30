SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
PROJECT_ROOT=$(dirname "$(dirname "${SCRIPT_DIR}")")
SRC_DIR="${PROJECT_ROOT}/main"

function usage() {
    cat << EOM
usage: $(basename "$0") [OPTION]...
  -n REPO_NAME    the name of the repository
  -e EXPERIMENT_DIR    path to the experiment directory
  -x OPENAI_MODEL_NAME    name of the OpenAI model to use
EOM
  exit 1
}

REPO_NAME=""
EXPERIMENT_DIR=""
OPENAI_MODEL_NAME=""

while getopts ":n:e:x:h" optKey; do
  case "$optKey" in
    n )
      REPO_NAME=${OPTARG}
      ;;
    e )
      EXPERIMENT_DIR=${OPTARG}
      ;;
    x )
      OPENAI_MODEL_NAME=${OPTARG}
      ;;
    '-h'|'--help'|* )
      usage
      ;;
  esac
done

if [ -z "${REPO_NAME}" ]; then
  echo -e "-n option is required"
  exit 1
fi

if [ -z "${EXPERIMENT_DIR}" ]; then
  echo -e "-e option is required"
  exit 1
fi

if [ -z "${OPENAI_MODEL_NAME}" ]; then
  echo -e "-x option is required"
  exit 1
fi

ESCAPED_REPO_NAME=$(echo "${REPO_NAME}" | sed 's/\//__/g')

REPO_DIR="${EXPERIMENT_DIR}/repo/${ESCAPED_REPO_NAME}"

LOG_PATH="${EXPERIMENT_DIR}/log/log_${ESCAPED_REPO_NAME}.txt"
FLAG_PATH="${EXPERIMENT_DIR}/flag/success_${ESCAPED_REPO_NAME}.txt"

# input to agents
TEST_FILES_TXT_PATH="${EXPERIMENT_DIR}/asset/test_files_txt/${ESCAPED_REPO_NAME}_test_files.txt"
DEP_VERSIONS_TXT_PATH="${EXPERIMENT_DIR}/asset/dep_versions_txt/${ESCAPED_REPO_NAME}_dep_versions.txt"

OPENAI_MODEL_NAME=${OPENAI_MODEL_NAME} uv run python -u "${SRC_DIR}/solve_openai.py" \
  --repo_name "${REPO_NAME}" \
  --host_repo_dir "${REPO_DIR}" \
  --test_files_txt_path "${TEST_FILES_TXT_PATH}" \
  --dep_versions_txt_path "${DEP_VERSIONS_TXT_PATH}" \
  2>&1 | tee -i "${LOG_PATH}"

if grep -q "##### Test Success #####" "${LOG_PATH}"; then
  touch "${FLAG_PATH}"
fi
