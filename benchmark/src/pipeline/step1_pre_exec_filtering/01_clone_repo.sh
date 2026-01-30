function usage() {
    cat << EOM
usage: $(basename "$0") [OPTION]...
  -i INPUT_PATH    path to the jsonl file with candidate repositories
  -o OUTPUT_DIR    path to the output directory
EOM
  exit 1
}

INPUT_PATH=""
SAVE_DIR_ROOT=""

while getopts ":i:o:h" optKey; do
  case "$optKey" in
    i )
      INPUT_PATH=${OPTARG}
      ;;
    o )
      SAVE_DIR_ROOT=${OPTARG}
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

if [ -z "${SAVE_DIR_ROOT}" ]; then
  echo -e "-o option is required"
  exit 1
fi

# constants
REPO_NAME_KEY="repo_name"
REPO_URL_KEY="repo_url"
COMMIT_HASH_KEY="revision_id"

mkdir -p "${SAVE_DIR_ROOT}"

# for each line in the input file, extract the repository name, URL, and commit hash using jq
jq -r --arg repo_name_key "${REPO_NAME_KEY}" --arg repo_url_key "${REPO_URL_KEY}" --arg commit_hash_key "${COMMIT_HASH_KEY}" \
  '[.[$repo_name_key], .[$repo_url_key], .[$commit_hash_key]] | @tsv' "${INPUT_PATH}" | while IFS=$'\t' read -r REPO_NAME REPO_URL COMMIT_HASH; do
    echo "Now cloning repository: ${REPO_NAME} (${REPO_URL}) at commit ${COMMIT_HASH}"
    SAVE_DIR_NAME=$(echo "${REPO_NAME}" | sed 's/\//__/g')
    TARGET_DIR="${SAVE_DIR_ROOT}/${SAVE_DIR_NAME}"
    (GIT_TERMINAL_PROMPT=0 git clone ${REPO_URL} ${TARGET_DIR} && git -C "${TARGET_DIR}" checkout -b target_version ${COMMIT_HASH} && echo "clone completed" && rm -rf "${TARGET_DIR}/.git") || (echo "clone failed" && rm -rf ${TARGET_DIR})
done
