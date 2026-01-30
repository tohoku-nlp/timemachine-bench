function usage() {
    cat << EOM
usage: $(basename "$0") [OPTION]...
  -b BASE_DIR    path to the directory containing repositories and other assets (SAVE_DIR in run_init.sh)
  -e EXPERIMENT_DIR    path to the experiment directory (a copy of BASE_DIR will be created)
EOM
  exit 1
}

BASE_DIR=""
EXPERIMENT_DIR=""

while getopts ":b:e:h" optKey; do
  case "$optKey" in
    b )
      BASE_DIR=${OPTARG}
      ;;
    e )
      EXPERIMENT_DIR=${OPTARG}
      ;;
    '-h'|'--help'|* )
      usage
      ;;
  esac
done

if [ -z "${BASE_DIR}" ]; then
  echo -e "-b option is required"
  exit 1
fi

if [ -z "${EXPERIMENT_DIR}" ]; then
  echo -e "-e option is required"
  exit 1
fi

mkdir -p "${EXPERIMENT_DIR}"

# if the directory is not empty, exit
if [ -n "$(ls -A ${EXPERIMENT_DIR})" ]; then
  echo "Directory ${EXPERIMENT_DIR} is not empty. Exit."
  exit 1
fi

cp -a "${BASE_DIR}/." "${EXPERIMENT_DIR}"
