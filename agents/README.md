## TimeMachine-bench Baseline Agents

This directory contains implementations of our baseline agents for running experiments on the TimeMachine-bench dataset.

### Prerequisites

- [uv](https://docs.astral.sh/uv/): For managing dependencies for the pipeline scripts.
- [docker](https://www.docker.com/): To provide isolated environments for secure execution of test suites.
- [jq](https://jqlang.org/): For parsing and processing JSON data within shell scripts.

The agents interact with LLMs via the OpenAI API for GPT models, and AWS Bedrock for all other models we reported in the paper.
Please set your OpenAI API key (and/or) AWS credentials as environment variables before starting the experiments.
If you prefer to use other LLM services, please modify the relevant parts of the scripts accordingly.

### Usage

First, start the pypi-timemachine server with the following command (ensure you are in the repository root):

```bash
docker compose up -d
```

Then, move to the `agents` directory and run the following command to install the required dependencies for the experiments:

```bash
uv sync
```

(Only once) Run the following command to set up the initial state of the repositories (ensure you are in the `agents/src` directory).
This step clones the repositories, rolls back to the target commits, and applies patches to the test files.

Note: The output of this step will be copied each time in the subsequent steps. This allows you to run multiple experiments without re-initializing the repositories.

```bash
uv run bash runners/setup/run_init.sh \
    -i ../../benchmark/data/v1/timemachine-bench-verified.jsonl \
    -s <base_dir>
```

To run the experiments, execute the following commands in the `agents/src` directory:

```bash
# Copy initialized repositories
uv run bash runners/setup/prepare_experiment.sh \
    -b <base_dir> \
    -e <experiment_dir>

# (for GPT models) Run the agent with OpenAI API
uv run bash runners/main/run_solve_loop_openai.sh \
    -i ../../benchmark/data/v1/timemachine-bench-verified.jsonl \
    -e <experiment_dir> \
    -x <openai_model_name>

# (for other models) Run the agent with AWS Bedrock
uv run bash runners/main/run_solve_loop_bedrock.sh \
    -i ../../benchmark/data/v1/timemachine-bench-verified.jsonl \
    -e <experiment_dir> \
    -x <bedrock_model_name> \
    -r <bedrock_region>
```

Once the agents have finished running, execute the following commands to calculate the pass@1 and prec@1 values (inside the `agents/src` directory).
The final evaluation results will be stored under the `<experiment_dir>` directory.

```bash
uv run bash evaluation/loop_get_patch.sh \
    -i ../../benchmark/data/v1/timemachine-bench-verified.jsonl \
    -e <experiment_dir> \
    -b <base_dir>

uv run python evaluation/calc_metrics.py \
    -i ../../benchmark/data/v1/timemachine-bench-verified.jsonl \
    -e <experiment_dir>
```
