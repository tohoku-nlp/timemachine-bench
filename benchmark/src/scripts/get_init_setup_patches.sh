function usage() {
    cat << EOM
usage: $(basename "$0") [OPTION]...
  -i INPUT_PATH    jsonl file with candidate repositories (step4 output)
  -r REPO_DIR    path to the directory with processed repositories
  -o OUTPUT_DIR    path to the output directory
EOM
  exit 1
}

INPUT_PATH=""
REPO_DIR=""
OUTPUT_DIR=""

while getopts ":i:r:o:h" optKey; do
  case "$optKey" in
    i )
      INPUT_PATH=${OPTARG}
      ;;
    r )
      REPO_DIR=${OPTARG}
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

if [ -z "${OUTPUT_DIR}" ]; then
  echo -e "-o option is required"
  exit 1
fi

# constants
REPO_NAME_KEY="repo_name"

# get diff of two directories
jq -r --arg repo_name_key "${REPO_NAME_KEY}" '.[$repo_name_key]' "${INPUT_PATH}" | while read -r REPO_NAME; do
    SAVE_DIR_NAME=$(echo "${REPO_NAME}" | sed 's/\//__/g')

    RAW_REPO_DIR="${REPO_DIR}/raw/${SAVE_DIR_NAME}"
    NEW_REPO_DIR="${REPO_DIR}/new/${SAVE_DIR_NAME}"

    TMP_RAW_DIR=$(mktemp -d)
    TMP_NEW_DIR=$(mktemp -d)

    # compare files with the following extensions
    (
        cd "${RAW_REPO_DIR}" && find . \( -name "*.txt" -o -name "*.pip" -o -name "*.toml" -o -name "*.py" -o -name "*.sh" -o -name "*.lock" \) -type f -not -type l -print0 | \
        while IFS= read -r -d '' file; do
            mime_type=$(file -b --mime-type "${file}")
            if [[ "${mime_type}" == "application/octet-stream" || "${mime_type}" == "data" ]]; then
                continue
            fi
            cp --parents "${file}" "${TMP_RAW_DIR}/"
        done
    )

    (
        cd "${NEW_REPO_DIR}" && find . \( -name "*.txt" -o -name "*.pip" -o -name "*.toml" -o -name "*.py" -o -name "*.sh" -o -name "*.lock" \) -type f -not -type l -print0 | \
        while IFS= read -r -d '' file; do
            mime_type=$(file -b --mime-type "${file}")
            if [[ "${mime_type}" == "application/octet-stream" || "${mime_type}" == "data" ]]; then
                continue
            fi
            cp --parents "${file}" "${TMP_NEW_DIR}/"
        done
    )

    diff -Naur "${TMP_RAW_DIR}" "${TMP_NEW_DIR}" | \
    sed -e "s,^--- ${TMP_RAW_DIR}/\([^ \t]\+\).*$,--- \1," \
        -e "s,^+++ ${TMP_NEW_DIR}/\([^ \t]\+\).*$,+++ \1," | \
    grep -v -E '^(diff -|Only in |Binary files)' > "${OUTPUT_DIR}/${SAVE_DIR_NAME}.patch"

    rm -rf "${TMP_RAW_DIR}" "${TMP_NEW_DIR}"
done
