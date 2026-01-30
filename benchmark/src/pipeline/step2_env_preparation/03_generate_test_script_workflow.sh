SRC_DIR=$(cd "$(dirname "$0")" && pwd)

function usage() {
    cat << EOM
usage: $(basename "$0") [OPTION]...
  -i INPUT_PATH    path to the jsonl file with candidate repositories
  -r REPO_DIR_ROOT    path to the root directory of raw (cloned) repositories
  -o SAVE_PATH    path to the output file
EOM
  exit 1
}

INPUT_PATH=""
REPO_DIR_ROOT=""
SAVE_PATH=""

while getopts ":i:r:o:h" optKey; do
  case "$optKey" in
    i )
      INPUT_PATH=${OPTARG}
      ;;
    r )
      REPO_DIR_ROOT=${OPTARG}
      ;;
    o )
      SAVE_PATH=${OPTARG}
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

if [ -z "${REPO_DIR_ROOT}" ]; then
  echo -e "-r option is required"
  exit 1
fi

if [ -z "${SAVE_PATH}" ]; then
  echo -e "-o option is required"
  exit 1
fi

uv run python ${SRC_DIR}/03_generate_test_script_workflow.py \
    --input_path ${INPUT_PATH} \
    --repo_dir_root ${REPO_DIR_ROOT} \
    --save_path ${SAVE_PATH} \
    --model_id "us.anthropic.claude-sonnet-4-20250514-v1:0"
