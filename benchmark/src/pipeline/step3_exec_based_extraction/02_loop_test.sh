function usage() {
    cat << EOM
usage: $(basename "$0") [OPTION]...
  -i INPUT_PATH    path to the jsonl file with candidate repositories (step2 output)
  -r REPO_DIR    path to the directory with processed repositories
  -d DOCKERFILE_DIR    path to the directory with Dockerfiles
  -l LOG_DIR    path to the output directory for test logs
  -o OUTPUT_PATH    path to save target repository information (jsonl)
EOM
  exit 1
}

INPUT_PATH=""
REPO_DIR=""
DOCKERFILE_DIR=""
LOG_DIR=""
OUTPUT_PATH=""

while getopts ":i:r:d:l:o:h" optKey; do
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
    l )
      LOG_DIR=${OPTARG}
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

if [ -z "${REPO_DIR}" ]; then
  echo -e "-r option is required"
  exit 1
fi

if [ -z "${DOCKERFILE_DIR}" ]; then
  echo -e "-d option is required"
  exit 1
fi

if [ -z "${LOG_DIR}" ]; then
  echo -e "-l option is required"
  exit 1
fi

if [ -z "${OUTPUT_PATH}" ]; then
  echo -e "-o option is required"
  exit 1
fi

# constants
TIMEOUT="10m"
MEM_SIZE="16g"

mkdir -p ${LOG_DIR}

REPO_NAME_KEY="repo_name"

OLD_REPO_DIR="${REPO_DIR}/old"
NEW_REPO_DIR="${REPO_DIR}/new"

OLD_DOCKERFILE_DIR=${DOCKERFILE_DIR}/old
NEW_DOCKERFILE_DIR=${DOCKERFILE_DIR}/new

CANDIDATE_COUNT=0

touch ${OUTPUT_PATH}

# for each line in the input file, extract the repository name, target version, and target date for reproduction
while read -r LINE; do
  REPO_NAME=$(echo "${LINE}" | jq -r --arg repo_name_key "${REPO_NAME_KEY}" '.[$repo_name_key]')

  SAVE_DIR_NAME=$(echo "${REPO_NAME}" | sed 's/\//__/g')
  echo "[$(date +'%Y-%m-%d %H:%M:%S')] Processing repository: ${SAVE_DIR_NAME}"

  old_dockerfile="${OLD_DOCKERFILE_DIR}/${SAVE_DIR_NAME}.Dockerfile"
  new_dockerfile="${NEW_DOCKERFILE_DIR}/${SAVE_DIR_NAME}.Dockerfile"

  # no Dockerfile exists for the repository if the previous script exited with an error
  if [ ! -f "${old_dockerfile}" ] || [ ! -f "${new_dockerfile}" ]; then
    echo "Skipping repository ${SAVE_DIR_NAME}."
    continue
  fi

  echo "[$(date +'%Y-%m-%d %H:%M:%S')] Building Docker images for ${SAVE_DIR_NAME}."

  # lowercase the repository name (docker does not accept uppercase characters in image names)
  SAVE_DIR_NAME_LOWER="${SAVE_DIR_NAME,,}"

  # build Docker images for the old and new versions
  # connect to the host network to access the pypi-timemachine service
  if ! (timeout --foreground -s KILL ${TIMEOUT} docker build --network=host --memory=${MEM_SIZE} -t "${SAVE_DIR_NAME_LOWER}_old" -f "${old_dockerfile}" ${OLD_REPO_DIR}); then
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] Failed to build old Docker images for ${SAVE_DIR_NAME}."
    docker rmi --force "${SAVE_DIR_NAME_LOWER}_old" "${SAVE_DIR_NAME_LOWER}_new"
    docker builder prune --force
    continue
  fi

  echo "[$(date +'%Y-%m-%d %H:%M:%S')] Successfully built old Docker images for ${SAVE_DIR_NAME}."

  if ! (timeout --foreground -s KILL ${TIMEOUT} docker build --network=host --memory=${MEM_SIZE} -t "${SAVE_DIR_NAME_LOWER}_new" -f "${new_dockerfile}" ${NEW_REPO_DIR}); then
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] Failed to build new Docker images for ${SAVE_DIR_NAME}."
    docker rmi --force "${SAVE_DIR_NAME_LOWER}_old" "${SAVE_DIR_NAME_LOWER}_new"
    docker builder prune --force
    continue
  fi

  echo "[$(date +'%Y-%m-%d %H:%M:%S')] Successfully built new Docker images for ${SAVE_DIR_NAME}."

  echo "[$(date +'%Y-%m-%d %H:%M:%S')] Running tests for ${SAVE_DIR_NAME}."

  # run tests in the old and new Docker images
  timeout --foreground -s KILL ${TIMEOUT} docker run --network none --memory=${MEM_SIZE} --name "${SAVE_DIR_NAME_LOWER}_old" "${SAVE_DIR_NAME_LOWER}_old" > "${LOG_DIR}/${SAVE_DIR_NAME}_old.log" 2>&1
  exit_code=$?

  docker rm --force "${SAVE_DIR_NAME_LOWER}_old"

  # check if the test timed out (timeout command returns 124 if the command times out)
  if [ ${exit_code} -eq 124 ]; then
    echo -e "\n\nERROR: Test timed out after ${TIMEOUT}." >> "${LOG_DIR}/${SAVE_DIR_NAME}_old.log"
  fi

  if [ ${exit_code} -ne 0 ]; then
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] Failed to run tests for old version of ${SAVE_DIR_NAME}."
    docker rmi --force "${SAVE_DIR_NAME_LOWER}_old" "${SAVE_DIR_NAME_LOWER}_new"
    docker builder prune --force
    continue
  fi

  echo "[$(date +'%Y-%m-%d %H:%M:%S')] Successfully ran tests for old version of ${SAVE_DIR_NAME}."

  timeout --foreground -s KILL ${TIMEOUT} docker run --network none --memory=${MEM_SIZE} --name "${SAVE_DIR_NAME_LOWER}_new" "${SAVE_DIR_NAME_LOWER}_new" > "${LOG_DIR}/${SAVE_DIR_NAME}_new.log" 2>&1
  exit_code=$?

  docker rm --force "${SAVE_DIR_NAME_LOWER}_new"

  # check if the test timed out (timeout command returns 124 if the command times out)
  if [ ${exit_code} -eq 124 ]; then
    echo -e "\n\nERROR: Test timed out after ${TIMEOUT}." >> "${LOG_DIR}/${SAVE_DIR_NAME}_new.log"
  fi

  if [ ${exit_code} -ne 0 ]; then
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] Failed to run tests for new version of ${SAVE_DIR_NAME}."

    # the repository is a candidate for the benchmark because the old version passed the tests, but the new version did not
    CANDIDATE_COUNT=$((CANDIDATE_COUNT + 1))
    echo "The repository ${SAVE_DIR_NAME} is a candidate for the benchmark. Num candidates so far: ${CANDIDATE_COUNT}."

    # save repository information as jsonl
    echo "${LINE}" >> "${OUTPUT_PATH}"

    docker rmi --force "${SAVE_DIR_NAME_LOWER}_old" "${SAVE_DIR_NAME_LOWER}_new"
    docker builder prune --force
    continue
  fi

  echo "[$(date +'%Y-%m-%d %H:%M:%S')] Successfully ran tests for new version of ${SAVE_DIR_NAME}."

  # clean up Docker images
  docker rmi --force "${SAVE_DIR_NAME_LOWER}_old" "${SAVE_DIR_NAME_LOWER}_new"
  docker builder prune --force
  echo "[$(date +'%Y-%m-%d %H:%M:%S')] Finished processing repository: ${SAVE_DIR_NAME}."
done < "${INPUT_PATH}"
