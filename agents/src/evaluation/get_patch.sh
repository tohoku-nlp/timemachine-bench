function usage() {
    cat << EOM
usage: $(basename "$0") [OPTION]...
  -n REPO_NAME    the name of the repository
  -b BEFORE_REPO_DIR    path to the directory with base repository
  -a AFTER_REPO_DIR    path to the directory with fixed repository
  -t TEST_FILE_LST   path to the text file with test file names
  -s SAVE_DIR    path to the directory to save diff patches
EOM
  exit 1
}

REPO_NAME=""
BEFORE_REPO_DIR=""
AFTER_REPO_DIR=""
TEST_FILE_LST=""
SAVE_DIR=""

while getopts ":n:b:a:t:s:h" optKey; do
  case "$optKey" in
    n )
      REPO_NAME=${OPTARG}
      ;;
    b )
      BEFORE_REPO_DIR=${OPTARG}
      ;;
    a )
      AFTER_REPO_DIR=${OPTARG}
      ;;
    t )
      TEST_FILE_LST=${OPTARG}
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

if [ -z "${BEFORE_REPO_DIR}" ]; then
  echo -e "-b option is required"
  exit 1
fi

if [ -z "${AFTER_REPO_DIR}" ]; then
  echo -e "-a option is required"
  exit 1
fi

if [ -z "${TEST_FILE_LST}" ]; then
  echo -e "-t option is required"
  exit 1
fi

if [ -z "${SAVE_DIR}" ]; then
  echo -e "-s option is required"
  exit 1
fi

mkdir -p ${SAVE_DIR}/main
mkdir -p ${SAVE_DIR}/test

ESCAPED_REPO_NAME=$(echo "${REPO_NAME}" | sed 's/\//__/g')

if [ ! -d ${AFTER_REPO_DIR} ]; then
  echo "Fixed repository for ${REPO_NAME} not found. Have you have completed the fixing step?"
  exit 1
fi

# get union of files from before/after repositories
(find ${BEFORE_REPO_DIR} -type f -name "*.py" -printf '%P\n'; find ${AFTER_REPO_DIR} -type f -name "*.py" -printf '%P\n') | sort | uniq > ${SAVE_DIR}/tmp_${ESCAPED_REPO_NAME}_all_files.txt
sort ${TEST_FILE_LST} > ${SAVE_DIR}/tmp_${ESCAPED_REPO_NAME}_test_files.txt
# get files other than test files
comm -23 ${SAVE_DIR}/tmp_${ESCAPED_REPO_NAME}_all_files.txt ${SAVE_DIR}/tmp_${ESCAPED_REPO_NAME}_test_files.txt > ${SAVE_DIR}/tmp_${ESCAPED_REPO_NAME}_main_files.txt

# create patch for main (non-test) files
rm -f ${SAVE_DIR}/main/${ESCAPED_REPO_NAME}.patch
while IFS= read -r file_path; do
    diff -Naur "${BEFORE_REPO_DIR}/${file_path}" "${AFTER_REPO_DIR}/${file_path}" | \
    sed -e "s,^--- ${BEFORE_REPO_DIR}/\([^ \t]\+\).*$,--- \1," \
        -e "s,^+++ ${AFTER_REPO_DIR}/\([^ \t]\+\).*$,+++ \1," >> ${SAVE_DIR}/main/${ESCAPED_REPO_NAME}.patch
done < ${SAVE_DIR}/tmp_${ESCAPED_REPO_NAME}_main_files.txt

# create patch for test files
rm -f ${SAVE_DIR}/test/${ESCAPED_REPO_NAME}.patch
while IFS= read -r file_path; do
    diff -Naur "${BEFORE_REPO_DIR}/${file_path}" "${AFTER_REPO_DIR}/${file_path}" | \
    sed -e "s,^--- ${BEFORE_REPO_DIR}/\([^ \t]\+\).*$,--- \1," \
        -e "s,^+++ ${AFTER_REPO_DIR}/\([^ \t]\+\).*$,+++ \1," >> ${SAVE_DIR}/test/${ESCAPED_REPO_NAME}.patch
done < ${SAVE_DIR}/tmp_${ESCAPED_REPO_NAME}_test_files.txt

# remove temporary files
rm -f ${SAVE_DIR}/tmp_${ESCAPED_REPO_NAME}_*.txt
