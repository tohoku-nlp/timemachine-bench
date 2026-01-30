SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
PROJECT_ROOT=$(dirname "$(dirname "${SCRIPT_DIR}")")
SRC_DIR="${PROJECT_ROOT}/main"

function usage() {
    cat << EOM
usage: $(basename "$0") [OPTION]...
  -n REPO_NAME    the name of the repository
  -e EXPERIMENT_DIR    path to the experiment directory
  -x BEDROCK_MODEL_NAME    name of the Bedrock model to use
  -r BEDROCK_REGION    the region where the Bedrock model is hosted
EOM
  exit 1
}

REPO_NAME=""
EXPERIMENT_DIR=""
BEDROCK_MODEL_NAME=""
# default
BEDROCK_REGION="us-east-1"

while getopts ":n:e:x:r:h" optKey; do
  case "$optKey" in
    n )
      REPO_NAME=${OPTARG}
      ;;
    e )
      EXPERIMENT_DIR=${OPTARG}
      ;;
    x )
      BEDROCK_MODEL_NAME=${OPTARG}
      ;;
    r )
      BEDROCK_REGION=${OPTARG}
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

if [ -z "${BEDROCK_MODEL_NAME}" ]; then
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

MODEL_NAME_LOWER="${BEDROCK_MODEL_NAME,,}"
SCRIPT_PATH="${SRC_DIR}/solve_bedrock.py"

if [[ "${MODEL_NAME_LOWER}" == *"deepseek"* ]]; then
  SCRIPT_PATH="${SRC_DIR}/model_specific/solve_bedrock_deepseek.py"
elif [[ "${MODEL_NAME_LOWER}" == *"llama"* ]]; then
  SCRIPT_PATH="${SRC_DIR}/model_specific/solve_bedrock_llama.py"
fi

BEDROCK_MODEL_NAME=${BEDROCK_MODEL_NAME} BEDROCK_REGION=${BEDROCK_REGION} uv run python -u "${SCRIPT_PATH}" \
  --repo_name "${REPO_NAME}" \
  --host_repo_dir "${REPO_DIR}" \
  --test_files_txt_path "${TEST_FILES_TXT_PATH}" \
  --dep_versions_txt_path "${DEP_VERSIONS_TXT_PATH}" \
  2>&1 | tee -i "${LOG_PATH}"

if grep -q "##### Test Success #####" "${LOG_PATH}"; then
  touch "${FLAG_PATH}"
fi
