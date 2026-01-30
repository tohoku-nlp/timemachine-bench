SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)

function usage() {
    cat << EOM
usage: $(basename "$0") [OPTION]...
  -i INPUT_PATH    path to the evaluation dataset (in jsonl)
  -e EXPERIMENT_DIR   path to the experiment directory
EOM
  exit 1
}

INPUT_PATH=""
EXPERIMENT_DIR=""

while getopts ":i:e:h" optKey; do
  case "$optKey" in
    i )
      INPUT_PATH=${OPTARG}
      ;;
    e )
      EXPERIMENT_DIR=${OPTARG}
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

GOLD_PATCH_DIR="${EXPERIMENT_DIR}/asset/gold_patch"
MODEL_PATCH_DIR="${EXPERIMENT_DIR}/diff_patch/main"

# constants
REPO_NAME_KEY="repo_name"

# loop through each repository
jq -r --arg repo_name_key "${REPO_NAME_KEY}" '.[$repo_name_key]' "${INPUT_PATH}" | while read -r REPO_NAME; do
  ESCAPED_REPO_NAME=$(echo "${REPO_NAME}" | sed 's/\//__/g')

  GOLD_PATCH_PATH="${GOLD_PATCH_DIR}/${ESCAPED_REPO_NAME}.patch"
  MODEL_PATCH_PATH="${MODEL_PATCH_DIR}/${ESCAPED_REPO_NAME}.patch"

  uv run python "${SCRIPT_DIR}/calc_prec.py" \
    --repo_name "${REPO_NAME}" \
    --gold_patch_path "${GOLD_PATCH_PATH}" \
    --model_patch_path "${MODEL_PATCH_PATH}"
done
