SRC_DIR=$(cd "$(dirname "$0")" && pwd)

function usage() {
    cat << EOM
usage: $(basename "$0") [OPTION]...
  -i INPUT_PATH    path to the jsonl file with candidate repositories
  -r REPO_DIR_ROOT    path to the root directory of raw (cloned) repositories
  -o OUTPUT_PATH    path to the output file
EOM
  exit 1
}

INPUT_PATH=""
REPO_DIR_ROOT=""
OUTPUT_PATH=""

while getopts ":i:r:o:h" optKey; do
  case "$optKey" in
    i )
      INPUT_PATH=${OPTARG}
      ;;
    r )
      REPO_DIR_ROOT=${OPTARG}
      ;;
    o )
      OUTPUT_PATH=${OPTARG}
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

if [ -z "${OUTPUT_PATH}" ]; then
  echo -e "-o option is required"
  exit 1
fi

uv run python ${SRC_DIR}/02_check_encoding.py \
  --input_path ${INPUT_PATH} \
  --repo_dir_root ${REPO_DIR_ROOT} \
  --save_path ${OUTPUT_PATH}
