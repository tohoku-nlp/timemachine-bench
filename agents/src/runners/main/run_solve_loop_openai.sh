# to stop loop on Ctrl+C
trap 'exit 1' INT

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)

function usage() {
    cat << EOM
usage: $(basename "$0") [OPTION]...
  -i INPUT_PATH    path to the evaluation dataset (in jsonl)
  -e EXPERIMENT_DIR    path to the experiment directory
  -x OPENAI_MODEL_NAME    name of the OpenAI model to use
EOM
  exit 1
}

INPUT_PATH=""
EXPERIMENT_DIR=""
OPENAI_MODEL_NAME=""

while getopts ":i:e:x:h" optKey; do
  case "$optKey" in
    i )
      INPUT_PATH=${OPTARG}
      ;;
    e )
      EXPERIMENT_DIR=${OPTARG}
      ;;
    x )
      OPENAI_MODEL_NAME=${OPTARG}
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

if [ -z "${OPENAI_MODEL_NAME}" ]; then
  echo -e "-x option is required"
  exit 1
fi

read -p "Are you sure you have a time-machine accessible from containers? (y/n): " answer

if [[ $answer == "y" ]]; then
  echo "Start processing..."
else
  echo "Please start a time-machine before running this script."
  exit 1
fi

LOG_DIR="${EXPERIMENT_DIR}/log"
FLAG_DIR="${EXPERIMENT_DIR}/flag"
mkdir -p "${LOG_DIR}" "${FLAG_DIR}"

# if the directory is not empty, exit
if [ -n "$(ls -A ${LOG_DIR})" ]; then
  echo "Previous logs exist in ${LOG_DIR}. Please move or delete them before running this script."
  exit 1
fi

REPO_DIR_ROOT="${EXPERIMENT_DIR}/repo"
DOCKERFILE_DIR="${EXPERIMENT_DIR}/asset/dockerfile"

# constants
REPO_NAME_KEY="repo_name"
MEM_SIZE="16g"

# loop through each repository
jq -r --arg repo_name_key "${REPO_NAME_KEY}" '.[$repo_name_key]' "${INPUT_PATH}" | while read -r REPO_NAME; do
  ESCAPED_REPO_NAME=$(echo "${REPO_NAME}" | sed 's/\//__/g')

  echo "Now working on ...: ${REPO_NAME}"

  dockerfile_path="${DOCKERFILE_DIR}/${ESCAPED_REPO_NAME}.Dockerfile"
  repo_name_lower="${ESCAPED_REPO_NAME,,}"

  # build container image
  docker build --network=host --memory=${MEM_SIZE} -t "${repo_name_lower}_new" -f "${dockerfile_path}" ${REPO_DIR_ROOT} \
  && uv run bash "${SCRIPT_DIR}/solve_openai.sh" \
    -n "${REPO_NAME}" \
    -e "${EXPERIMENT_DIR}" \
    -x "${OPENAI_MODEL_NAME}"

  # clean up
  docker rmi "${repo_name_lower}_new"
  docker builder prune --force
done
