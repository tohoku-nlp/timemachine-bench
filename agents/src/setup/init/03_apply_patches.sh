function usage() {
    cat << EOM
usage: $(basename "$0") [OPTION]...
  -i INPUT_PATH    path to the evaluation dataset (in jsonl)
  -r REPO_DIR    path to the directory with repositories
  -a ASSET_DIR    path to the directory with assets
EOM
  exit 1
}

INPUT_PATH=""
REPO_DIR=""
ASSET_DIR=""

while getopts ":i:r:a:h" optKey; do
  case "$optKey" in
    i )
      INPUT_PATH=${OPTARG}
      ;;
    r )
      REPO_DIR=${OPTARG}
      ;;
    a )
      ASSET_DIR=${OPTARG}
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

if [ -z "${ASSET_DIR}" ]; then
  echo -e "-a option is required"
  exit 1
fi

# constants
REPO_NAME_KEY="repo_name"

jq -r --arg repo_name_key "${REPO_NAME_KEY}" '.[$repo_name_key]' "${INPUT_PATH}" | while read -r REPO_NAME; do
    SAVE_DIR_NAME=$(echo "${REPO_NAME}" | sed 's/\//__/g')

    TARGET_REPO_DIR="${REPO_DIR}/${SAVE_DIR_NAME}"

    INIT_PATCH_PATH="${ASSET_DIR}/init_patch/${SAVE_DIR_NAME}.patch"
    TEST_PATCH_PATH="${ASSET_DIR}/test_patch/${SAVE_DIR_NAME}.patch"

    # apply patches
    (patch -p0 -t -E -d "${TARGET_REPO_DIR}" < "${INIT_PATCH_PATH}" && patch -p0 -t -E -d "${TARGET_REPO_DIR}" < "${TEST_PATCH_PATH}") || echo "Failed to apply patches for ${REPO_NAME}"
done
