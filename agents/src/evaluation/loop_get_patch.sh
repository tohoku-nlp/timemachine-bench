SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)

function usage() {
    cat << EOM
usage: $(basename "$0") [OPTION]...
  -i INPUT_PATH    path to the evaluation dataset (in jsonl)
  -e EXPERIMENT_DIR   path to the experiment directory
  -b BASE_DIR    path to the directory containing repositories and other assets (SAVE_DIR in run_init.sh)
EOM
  exit 1
}

INPUT_PATH=""
EXPERIMENT_DIR=""
BASE_DIR=""

while getopts ":i:e:b:s:h" optKey; do
  case "$optKey" in
    i )
      INPUT_PATH=${OPTARG}
      ;;
    e )
      EXPERIMENT_DIR=${OPTARG}
      ;;
    b )
      BASE_DIR=${OPTARG}
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

if [ -z "${EXPERIMENT_DIR}" ]; then
  echo -e "-e option is required"
  exit 1
fi

if [ -z "${BASE_DIR}" ]; then
  echo -e "-b option is required"
  exit 1
fi

SAVE_DIR="${EXPERIMENT_DIR}/diff_patch"
mkdir -p "${SAVE_DIR}"

BASE_REPO_DIR_ROOT="${BASE_DIR}/repo"
AFTER_REPO_DIR_ROOT="${EXPERIMENT_DIR}/repo"
TEST_FILES_LST_DIR="${BASE_DIR}/asset/test_files_txt"

# constants
REPO_NAME_KEY="repo_name"

# loop through each repository
jq -r --arg repo_name_key "${REPO_NAME_KEY}" '.[$repo_name_key]' "${INPUT_PATH}" | while read -r REPO_NAME; do
  ESCAPED_REPO_NAME=$(echo "${REPO_NAME}" | sed 's/\//__/g')

  BASE_REPO_DIR="${BASE_REPO_DIR_ROOT}/${ESCAPED_REPO_NAME}"
  AFTER_REPO_DIR="${AFTER_REPO_DIR_ROOT}/${ESCAPED_REPO_NAME}"
  TEST_FILES_LST="${TEST_FILES_LST_DIR}/${ESCAPED_REPO_NAME}_test_files.txt"

  uv run bash "${SCRIPT_DIR}/get_patch.sh" \
    -n ${REPO_NAME} \
    -b ${BASE_REPO_DIR} \
    -a ${AFTER_REPO_DIR} \
    -t ${TEST_FILES_LST} \
    -s ${SAVE_DIR}
done
