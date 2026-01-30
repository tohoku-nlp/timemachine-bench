## TimeMachine-bench Construction Pipeline

This directory contains the scripts to construct the TimeMachine-bench evaluation dataset.
Our construction pipeline enables automatic extraction of repositories with migration issues by comparing test results before and after dependency updates.

### Prerequisites

- [uv](https://docs.astral.sh/uv/): For managing dependencies for the pipeline scripts.
- [docker](https://www.docker.com/): To provide isolated environments for secure execution of test suites.
- [jq](https://jqlang.org/): For parsing and processing JSON data within shell scripts.

Please set your AWS credentials as environment variables to invoke LLMs via AWS Bedrock.
If you prefer to use other LLM services, please modify the relevant parts of the scripts accordingly.

Additionally, you need to download The Stack v2 dataset by following the [official instructions](https://huggingface.co/datasets/bigcode/the-stack-v2-train-smol-ids#downloading-the-file-contents).
We do not redistribute the raw dataset contents, as users are required to accept the dataset agreement before downloading it.

### Usage

First, start the pypi-timemachine server with the following command (ensure you are in the repository root):

```bash
docker compose up -d
```

Then, move to the `benchmark` directory and run the following command to install the required dependencies for the pipeline scripts:

```bash
uv sync
```

Each step of the pipeline is implemented as a separate shell script in the `src/runners` directory.
Move to the `src` directory and run the commands in the following order:

```bash
# Step1: Pre-Execution Filtering
uv run runners/01_pre_exec_filtering.sh \
    -i <input_stack_jsonl> \
    -w <tmp_work_dir> \
    -l <log_dir> \
    -r <repo_dir> \
    -s <output_dir>

# Note: Repositories listed in the input JSONL file will be cloned into `<repo_dir>` during this step. Consider splitting the file into smaller chunks and make sure you have sufficient disk space.

# Step2: Runtime Environment Preparation
uv run runners/02_env_preparation.sh \
    -i <step1_output_jsonl> \
    -w <tmp_work_dir> \
    -l <log_dir> \
    -r <repo_dir> \
    -s <output_dir>

# Step3: Execution-Based Candidate Extraction
uv run runners/03_exec_based_extraction.sh \
    -i <step2_output_jsonl> \
    -r <repo_dir> \
    -l <log_dir> \
    -s <output_dir>

# Step4: Post-Execution Filtering
uv run runners/04_post_exec_filtering.sh \
    -i <step3_output_jsonl> \
    -r <repo_dir> \
    -t <test_log_dir> \
    -e <exec_log_dir> \
    -s <output_dir>

# Note: `<test_log_dir>` is the directory to which test execution logs inside Docker containers are stored. `<exec_log_dir>` is the directory to which the logs of the pipeline scripts are stored.
```
