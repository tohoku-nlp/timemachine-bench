SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
PROJECT_ROOT=$(dirname "$(dirname "${SCRIPT_DIR}")")
SRC_DIR="${PROJECT_ROOT}/setup/init"

function usage() {
    cat << EOM
usage: $(basename "$0") [OPTION]...
  -i INPUT_PATH    path to the evaluation dataset (in jsonl)
  -s SAVE_DIR    path to the directory to save repositories and other assets
EOM
  exit 1
}

INPUT_PATH=""
SAVE_DIR=""

while getopts ":i:s:h" optKey; do
  case "$optKey" in
    i )
      INPUT_PATH=${OPTARG}
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

if [ -z "${SAVE_DIR}" ]; then
  echo -e "-s option is required"
  exit 1
fi

mkdir -p "${SAVE_DIR}"

# if the directory is not empty, exit
if [ -n "$(ls -A ${SAVE_DIR})" ]; then
  echo "Directory ${SAVE_DIR} is not empty. Exit."
  exit 1
fi

REPO_DIR="${SAVE_DIR}/repo"
ASSET_DIR="${SAVE_DIR}/asset"

# Step 1: clone repositories
uv run bash "${SRC_DIR}/01_clone_repo.sh" \
    -i "${INPUT_PATH}" \
    -o "${REPO_DIR}"

# Step 2: extract assets
uv run python "${SRC_DIR}/02_extract_assets.py" \
    -i "${INPUT_PATH}" \
    -s "${ASSET_DIR}"

# Step 3: apply patches
uv run bash "${SRC_DIR}/03_apply_patches.sh" \
    -i "${INPUT_PATH}" \
    -r "${REPO_DIR}" \
    -a "${ASSET_DIR}"