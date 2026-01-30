function usage() {
    cat << EOM
usage: $(basename "$0") [OPTION]...
  -n REPO_NAME    the name of the repository to check
  -r REPO_DIR    path to the directory with processed repositories
  -d DOCKERFILE_DIR    path to the directory with Dockerfiles
  -w WORK_DIR   path to the working directory
  -s SAVE_DIR   path to the directory to save dependency version lists
EOM
  exit 1
}

REPO_NAME=""
REPO_DIR=""
DOCKERFILE_DIR=""
WORK_DIR=""
SAVE_DIR=""

while getopts ":n:r:d:w:s:h" optKey; do
  case "$optKey" in
    n )
      REPO_NAME=${OPTARG}
      ;;
    r )
      REPO_DIR=${OPTARG}
      ;;
    d )
      DOCKERFILE_DIR=${OPTARG}
      ;;
    w )
      WORK_DIR=${OPTARG}
      ;;
    s )
      SAVE_DIR=${OPTARG}
      ;;
    '-h'|'--help'|* )
      usage
      ;;
  esac
done

if [ -z "${REPO_NAME}" ]; then
  echo -e "-n option is required"
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

if [ -z "${WORK_DIR}" ]; then
  echo -e "-w option is required"
  exit 1
fi

if [ -z "${SAVE_DIR}" ]; then
  echo -e "-s option is required"
  exit 1
fi

read -p "Are you sure you have a time-machine accessible from containers? (y/n): " answer

if [[ $answer == "y" ]]; then
  echo "Start processing..."
else
  echo "Please start a time-machine before running this script."
  exit 1
fi

# remove the existing work directory and create a new one
rm -rf "${WORK_DIR}"
mkdir -p "${WORK_DIR}"

# constants
MEM_SIZE="16g"

# set the target date for migration to the end of July, 2025
UPDATE_TARGET_VERSION=3.12.11
UPDATE_TARGET_DATE="2025-07-31"

NEW_REPO_DIR="${REPO_DIR}/new"
NEW_DOCKERFILE_DIR=${DOCKERFILE_DIR}/new

#escape slashes in the repository name
SAVE_DIR_NAME=$(echo "${REPO_NAME}" | sed 's/\//__/g')

TARGET_REPO_SRC_DIR="${NEW_REPO_DIR}/${SAVE_DIR_NAME}"

# lowercase the repository name (docker does not accept uppercase characters in image names)
SAVE_DIR_NAME_LOWER=${SAVE_DIR_NAME,,}

new_dockerfile="${NEW_DOCKERFILE_DIR}/${SAVE_DIR_NAME}.Dockerfile"

docker build --network=host --memory=${MEM_SIZE} -t "${SAVE_DIR_NAME_LOWER}_new" -f "${new_dockerfile}" ${NEW_REPO_DIR}

ENTRYPOINT_FILE_SRC="${TARGET_REPO_SRC_DIR}/test_${SAVE_DIR_NAME}.sh"
ENTRYPOINT_FILE_COPY="${WORK_DIR}/check_dep_version_${SAVE_DIR_NAME}.sh"

cp "${ENTRYPOINT_FILE_SRC}" "${ENTRYPOINT_FILE_COPY}"

EXEC_LINE=$(grep -E 'pytest|unittest' "${ENTRYPOINT_FILE_COPY}" | tail -n 1)

if [ -z "${EXEC_LINE}" ]; then
  echo "Could not find a line containing 'pytest' or 'unittest' for ${REPO_NAME}. please check it manually."
  exit 1
fi

FREEZE_COMMAND=""

if [[ "${EXEC_LINE}" == *"python -m"* ]]; then
  # ... python -m
  FREEZE_COMMAND=$(echo "$EXEC_LINE" | sed -E 's/(.*python -m).*/\1 pip freeze/')
elif [[ "$EXEC_LINE" == *"pytest"* ]]; then
  # pytest ...
  FREEZE_COMMAND=$(echo "$EXEC_LINE" | sed -E 's/(.*)pytest.*/\1 pip freeze/')
elif [[ "${EXEC_LINE}" == *"python "* ]]; then
  # python ...
  FREEZE_COMMAND=$(echo "$EXEC_LINE" | sed -E 's/(.*)python .*/\1 pip freeze/')
fi

if [ -z "${FREEZE_COMMAND}" ]; then
  echo "Could not generate a freeze command for ${REPO_NAME}. please check it manually."
  exit 1
else
  sed -i "s|${EXEC_LINE}|${FREEZE_COMMAND}|" "${ENTRYPOINT_FILE_COPY}"
fi

# run the container and start a bash shell inside it (mount copied repository)
docker run --rm -v ${ENTRYPOINT_FILE_COPY}:/work/check_dep_version_${SAVE_DIR_NAME}.sh --memory=${MEM_SIZE} --name "test" --entrypoint="bash" "${SAVE_DIR_NAME_LOWER}_new" -c "bash /work/check_dep_version_${SAVE_DIR_NAME}.sh" > "${SAVE_DIR}/dep_versions_${SAVE_DIR_NAME}.txt"

# clean up
docker rmi "${SAVE_DIR_NAME_LOWER}_new"
docker builder prune --force
