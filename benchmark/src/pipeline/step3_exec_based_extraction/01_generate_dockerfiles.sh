SRC_DIR=$(cd "$(dirname "$0")" && pwd)

function usage() {
    cat << EOM
usage: $(basename "$0") [OPTION]...
  -i INPUT_PATH    path to the jsonl file with candidate repositories (step2 output)
  -d WORK_DIR    path to the working directory with processed repositories
  -o OUTPUT_DIR    path to the output directory
EOM
  exit 1
}

INPUT_PATH=""
WORK_DIR=""
OUTPUT_DIR=""

while getopts ":i:d:o:h" optKey; do
  case "$optKey" in
    i )
      INPUT_PATH=${OPTARG}
      ;;
    d )
      WORK_DIR=${OPTARG}
      ;;
    o )
      OUTPUT_DIR=${OPTARG}
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

if [ -z "${OUTPUT_DIR}" ]; then
  echo -e "-o option is required"
  exit 1
fi

# constants
REPO_NAME_KEY="repo_name"
REPRODUCE_TARGET_VERSION_KEY="target_version"
REPRODUCE_TARGET_DATE_KEY="committer_date"

# set the target date for migration to the end of July, 2025
UPDATE_TARGET_VERSION=3.12.11
UPDATE_TARGET_DATE="2025-07-31"

OLD_WORK_DIR_ROOT=${WORK_DIR}/old
NEW_WORK_DIR_ROOT=${WORK_DIR}/new

# save directories for old (reproduction) and new (updated) Dockerfiles

OLD_SAVE_DIR_ROOT=${OUTPUT_DIR}/old
NEW_SAVE_DIR_ROOT=${OUTPUT_DIR}/new

mkdir -p ${OLD_SAVE_DIR_ROOT}
mkdir -p ${NEW_SAVE_DIR_ROOT}

# for each line in the input file, extract the repository name, target version, and target date for reproduction
jq -r --arg repo_name_key "${REPO_NAME_KEY}" --arg target_version_key "${REPRODUCE_TARGET_VERSION_KEY}" --arg target_date_key "${REPRODUCE_TARGET_DATE_KEY}" \
  '[.[$repo_name_key], .[$target_version_key], .[$target_date_key]] | @tsv' "${INPUT_PATH}" | while IFS=$'\t' read -r REPO_NAME REPRODUCE_TARGET_VERSION REPRODUCE_TARGET_DATE; do
  SAVE_DIR_NAME=$(echo "${REPO_NAME}" | sed 's/\//__/g')
  echo "[$(date +'%Y-%m-%d %H:%M:%S')] Processing repository: ${SAVE_DIR_NAME}"

  # no directory exists for the repository if the previous script exited with an error
  if [ ! -d "${OLD_WORK_DIR_ROOT}/${SAVE_DIR_NAME}" ] || [ ! -d "${NEW_WORK_DIR_ROOT}/${SAVE_DIR_NAME}" ]; then
    echo "Skipping repository ${SAVE_DIR_NAME}."
    continue
  fi

  # convert `REPRODUCE_TARGET_DATE` to "%Y-%m-%d" format
  REPRODUCE_TARGET_DATE=$(date -d "${REPRODUCE_TARGET_DATE}" +%Y-%m-%d)

  # old
  uv run python ${SRC_DIR}/01_generate_dockerfiles.py \
    --repo_name_id ${SAVE_DIR_NAME} \
    --save_dir_root ${OLD_SAVE_DIR_ROOT} \
    --target_version ${REPRODUCE_TARGET_VERSION} \
    --target_date ${REPRODUCE_TARGET_DATE}

  # new
  uv run python ${SRC_DIR}/01_generate_dockerfiles.py \
    --repo_name_id ${SAVE_DIR_NAME} \
    --save_dir_root ${NEW_SAVE_DIR_ROOT} \
    --target_version ${UPDATE_TARGET_VERSION} \
    --target_date ${UPDATE_TARGET_DATE}
done
