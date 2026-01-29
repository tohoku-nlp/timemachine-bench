SRC_DIR=$(cd "$(dirname "$0")" && pwd)

function usage() {
    cat << EOM
usage: $(basename "$0") [OPTION]...
  -i INPUT_PATH    path to the jsonl file with candidate repositories (step1 output)
  -d WORK_DIR    path to the working directory, where (raw) cloned repositories are supposed to be stored under the 'raw' subdirectory
EOM
  exit 1
}

INPUT_PATH=""
WORK_DIR=""

while getopts ":i:d:h" optKey; do
  case "$optKey" in
    i )
      INPUT_PATH=${OPTARG}
      ;;
    d )
      WORK_DIR=${OPTARG}
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
  echo -e "-d option is required"
  exit 1
fi

# constants
REPO_NAME_KEY="repo_name"

RAW_REPO_DIR_ROOT=${WORK_DIR}/raw

OLD_WORK_DIR_ROOT=${WORK_DIR}/old
NEW_WORK_DIR_ROOT=${WORK_DIR}/new

# if the directories already exist, remove them
if [ -d "${OLD_WORK_DIR_ROOT}" ]; then
  rm -rf ${OLD_WORK_DIR_ROOT}
fi

if [ -d "${NEW_WORK_DIR_ROOT}" ]; then
  rm -rf ${NEW_WORK_DIR_ROOT}
fi

# for each line in the input file, extract the repository name, setup script, unpinned setup script, and test script using jq
jq -r --arg repo_name_key "${REPO_NAME_KEY}" '.[$repo_name_key]' "${INPUT_PATH}" | while read -r REPO_NAME; do
  SAVE_DIR_NAME=$(echo "${REPO_NAME}" | sed 's/\//__/g')
  echo "[$(date +'%Y-%m-%d %H:%M:%S')] Processing repository: ${SAVE_DIR_NAME}"

  RAW_REPO_DIR=${RAW_REPO_DIR_ROOT}/${SAVE_DIR_NAME}

  # in case the directories do not exist, skip the repository (this should not happen)
  if [ ! -d "${RAW_REPO_DIR}" ]; then
    echo "Skipping repository ${SAVE_DIR_NAME}."
    continue
  fi

  (uv run python ${SRC_DIR}/01_copy_and_unpin_repo.py \
    --raw_repo_dir ${RAW_REPO_DIR} \
    --save_dir ${OLD_WORK_DIR_ROOT}/${SAVE_DIR_NAME} \
  && \
  uv run python ${SRC_DIR}/01_copy_and_unpin_repo.py \
    --raw_repo_dir ${RAW_REPO_DIR} \
    --save_dir ${NEW_WORK_DIR_ROOT}/${SAVE_DIR_NAME} \
    --unpin_requirements
  ) || rm -rf ${OLD_WORK_DIR_ROOT}/${SAVE_DIR_NAME} ${NEW_WORK_DIR_ROOT}/${SAVE_DIR_NAME}
done
