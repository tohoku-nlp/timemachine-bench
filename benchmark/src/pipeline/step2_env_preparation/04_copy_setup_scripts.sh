function usage() {
    cat << EOM
usage: $(basename "$0") [OPTION]...
  -i INPUT_PATH    path to the jsonl file with candidate repositories (the output from the previous step)
  -d WORK_DIR    path to the working directory with processed repositories
EOM
  exit 1
}

INPUT_PATH=""
WORK_DIR=""

while getopts ":i:d:h" optKey; do
  case "$optKey" in
    i )
      INPUT_PATH=${OPTARG}
      ;;
    d )
      WORK_DIR=${OPTARG}
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

if [ -z "${WORK_DIR}" ]; then
  echo -e "-d option is required"
  exit 1
fi

# constants
REPO_NAME_KEY="repo_name"
SETUP_SCRIPT_KEY="setup_script"
UNPINNED_SETUP_SCRIPT_KEY="unpinned_setup_script"
TEST_SCRIPT_KEY="test_script"

OLD_WORK_DIR_ROOT=${WORK_DIR}/old
NEW_WORK_DIR_ROOT=${WORK_DIR}/new

# for each line in the input file, extract the repository name, setup script, unpinned setup script, and test script using jq
jq -r --arg repo_name_key "${REPO_NAME_KEY}" --arg setup_script_key "${SETUP_SCRIPT_KEY}" --arg unpinned_setup_script_key "${UNPINNED_SETUP_SCRIPT_KEY}" --arg test_script_key "${TEST_SCRIPT_KEY}" \
  '[.[$repo_name_key], .[$setup_script_key], .[$unpinned_setup_script_key], .[$test_script_key]] | @tsv' "${INPUT_PATH}" | while IFS=$'\t' read -r REPO_NAME SETUP_SCRIPT UNPINNED_SETUP_SCRIPT TEST_SCRIPT; do
  SAVE_DIR_NAME=$(echo "${REPO_NAME}" | sed 's/\//__/g')
  echo "[$(date +'%Y-%m-%d %H:%M:%S')] Processing repository: ${SAVE_DIR_NAME}"

  # no directory exists for the repository if the previous script exited with an error
  if [ ! -d "${OLD_WORK_DIR_ROOT}/${SAVE_DIR_NAME}" ] || [ ! -d "${NEW_WORK_DIR_ROOT}/${SAVE_DIR_NAME}" ]; then
    echo "Skipping repository ${SAVE_DIR_NAME}."
    continue
  fi

  # setup script
  echo -e "${SETUP_SCRIPT}" > "${OLD_WORK_DIR_ROOT}/${SAVE_DIR_NAME}/setup_${SAVE_DIR_NAME}.sh"
  # setup script (unpinned)
  echo -e "${UNPINNED_SETUP_SCRIPT}" > "${NEW_WORK_DIR_ROOT}/${SAVE_DIR_NAME}/setup_${SAVE_DIR_NAME}.sh"

  # test scripts
  echo -e "${TEST_SCRIPT}" > "${OLD_WORK_DIR_ROOT}/${SAVE_DIR_NAME}/test_${SAVE_DIR_NAME}.sh"
  echo -e "${TEST_SCRIPT}" > "${NEW_WORK_DIR_ROOT}/${SAVE_DIR_NAME}/test_${SAVE_DIR_NAME}.sh"
done
