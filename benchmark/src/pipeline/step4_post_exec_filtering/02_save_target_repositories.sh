function usage() {
    cat << EOM
usage: $(basename "$0") [OPTION]...
  -i INPUT_PATH    jsonl file with candidate repositories (output from the previous step)
  -r REPO_DIR    path to the directory with processed repositories
  -d DOCKERFILE_DIR    path to the directory with Dockerfiles
  -o OUTPUT_DIR    path to the output directory
EOM
  exit 1
}

INPUT_PATH=""
REPO_DIR=""
DOCKERFILE_DIR=""
OUTPUT_DIR=""

while getopts ":i:r:d:o:h" optKey; do
  case "$optKey" in
    i )
      INPUT_PATH=${OPTARG}
      ;;
    r )
      REPO_DIR=${OPTARG}
      ;;
    d )
      DOCKERFILE_DIR=${OPTARG}
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

if [ -z "${REPO_DIR}" ]; then
  echo -e "-r option is required"
  exit 1
fi

if [ -z "${DOCKERFILE_DIR}" ]; then
  echo -e "-d option is required"
  exit 1
fi

if [ -z "${OUTPUT_DIR}" ]; then
  echo -e "-o option is required"
  exit 1
fi

# constants
REPO_NAME_KEY="repo_name"

TARGET_REPO_DIR_ROOT="${OUTPUT_DIR}/repos"
TARGET_DOCKERFILE_ROOT="${OUTPUT_DIR}/dockerfiles"

mkdir -p "${TARGET_REPO_DIR_ROOT}/raw" "${TARGET_REPO_DIR_ROOT}/old" "${TARGET_REPO_DIR_ROOT}/new"
mkdir -p "${TARGET_DOCKERFILE_ROOT}/old" "${TARGET_DOCKERFILE_ROOT}/new"

jq -r --arg repo_name_key "${REPO_NAME_KEY}" '.[$repo_name_key]' "${INPUT_PATH}" | while read -r REPO_NAME; do
    SAVE_DIR_NAME=$(echo "${REPO_NAME}" | sed 's/\//__/g')

    cp -r "${REPO_DIR}/raw/${SAVE_DIR_NAME}" "${TARGET_REPO_DIR_ROOT}/raw"
    cp -r "${REPO_DIR}/old/${SAVE_DIR_NAME}" "${TARGET_REPO_DIR_ROOT}/old"
    cp -r "${REPO_DIR}/new/${SAVE_DIR_NAME}" "${TARGET_REPO_DIR_ROOT}/new"

    cp -r "${DOCKERFILE_DIR}/old/${SAVE_DIR_NAME}.Dockerfile" "${TARGET_DOCKERFILE_ROOT}/old"
    cp -r "${DOCKERFILE_DIR}/new/${SAVE_DIR_NAME}.Dockerfile" "${TARGET_DOCKERFILE_ROOT}/new"
done
