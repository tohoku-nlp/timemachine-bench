import ast
import sys
import json
import time
import atexit
import tomlkit
import argparse
from tqdm import tqdm
from pathlib import Path
from itertools import islice
from dicttoxml import dicttoxml
from xml.dom.minidom import parseString

from typing import Dict, Any, List
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END

from utils.requirement_utils import ast_find_setup_call, unpin_pip_install_line
from utils.code_utils import extract_codeblock, split_script_by_section, overwrite_unittest_script_with_paths

from utils.const import REGEX_PYPROJECT_TOML, REGEX_REQUIREMENTS_TXT, REGEX_SETUP_PY

from llm.bedrock_generate import get_llm_response
# prompts
from llm.prompts.prompts_pyproject import PYPROJECT_TEST_SCRIPT_GENERATION_PROMPT
from llm.prompts.prompts_setup import SETUP_TEST_SCRIPT_GENERATION_PROMPT

TOTAL_INPUT_TOKENS = 0
TOTAL_OUTPUT_TOKENS = 0

def _get_total_tokens_at_exit():
    print(f"Total input tokens: {TOTAL_INPUT_TOKENS}", file=sys.stderr)
    print(f"Total output tokens: {TOTAL_OUTPUT_TOKENS}", file=sys.stderr)

atexit.register(_get_total_tokens_at_exit)

class State(TypedDict):
    repo_dic: Dict[str, Any]
    repo_root: str
    rel_paths: List[str]
    testing_framework: str

    # model to use
    bedrock_model_id: str

    # the type of current file to use for generating test scripts
    gen_source: str

    has_pyproject_toml: bool
    has_requirements_txt: bool
    has_setup_py: bool

    # output
    raw_script: str
    setup_script: str
    test_script: str

def check_exist_pyproject_toml(state: State):
    files = state["rel_paths"]

    pyproject_toml_files = list(filter(lambda path: REGEX_PYPROJECT_TOML.match(path), files))

    # check if readable
    is_readable = False

    for rel_path in pyproject_toml_files:
        path = Path(state["repo_root"]) / rel_path

        try:
            with open(path) as f:
                content = f.read()

                # check if the file is a valid pyproject.toml (with `build-system` sections)
                data = tomlkit.loads(content)
                # check top-level keys
                is_readable = "build-system" in data
        except Exception:
            break

    return {"has_pyproject_toml": len(pyproject_toml_files) > 0 and is_readable}

def check_exist_requirements_txt(state: State):
    files = state["rel_paths"]
    # requirements.txt files can be located in any level of the repository
    requirements_txt_files = list(filter(lambda path: REGEX_REQUIREMENTS_TXT.search(path), files))

    # check if readable
    is_readable = False
    for rel_path in requirements_txt_files:
        path = Path(state["repo_root"]) / rel_path
        try:
            with open(path) as f:
                content = f.read()
        except Exception:
            break
    else:
        is_readable = True

    return {"has_requirements_txt": len(requirements_txt_files) > 0 and is_readable}

def check_exist_setup_py(state: State):
    files = state["rel_paths"]

    setup_py_files = list(filter(lambda path: REGEX_SETUP_PY.match(path), files))

    # check if readable
    is_readable = False

    for rel_path in setup_py_files:
        path = Path(state["repo_root"]) / rel_path
        try:
            with open(path) as f:
                content = f.read()

                # check if the file is a valid setup.py (with `setup` call)
                tree = ast.parse(content)
                if ast_find_setup_call(tree):
                    is_readable = True
        except Exception:
            break

    return {"has_setup_py": len(setup_py_files) > 0 and is_readable}

def has_pyproject_toml(state: State):
    return state["has_pyproject_toml"]

def has_requirements_txt(state: State):
    return state["has_requirements_txt"]

def has_setup_py(state: State):
    return state["has_setup_py"]

def generate_from_pyproject_toml(state: State):
    files = state["rel_paths"]

    pyproject_toml_files = list(filter(lambda path: REGEX_PYPROJECT_TOML.search(path), files))

    path_content_lst = []

    for rel_path in pyproject_toml_files:
        path = Path(state["repo_root"]) / rel_path

        with open(path) as f:
            content = f.read()
            path_content_lst.append({"path": rel_path, "content": content})

    pyproject_toml_content_raw = dicttoxml(
                                    path_content_lst,
                                    custom_root="pyproject_toml_files",
                                    item_func=lambda node: "pyproject_toml_file" if node == "pyproject_toml_files" else "item",
                                    attr_type=False
                                )

    pyproject_toml_content = parseString(pyproject_toml_content_raw).toprettyxml()
    # remove the first line (<?xml version="1.0" ?>)
    pyproject_toml_content = "\n".join(pyproject_toml_content.splitlines()[1:])

    testing_framework = state["testing_framework"]
    fallback_test_command = "python -m pytest ." if testing_framework == "pytest" else "python -m unittest discover"

    # ensure pytest to be installed even in case the author did not include it as a dependency
    test_installation_guide = \
"""In order not to miss `pytest` in the environment, please introduce an additional step to install `pytest` manually.
For example, `pip install pytest` for environments managed by `pip`, or `poetry add pytest` for those by `poetry`.
""" if testing_framework == "pytest" else ""

    prompt_pyproject_script_generation = PYPROJECT_TEST_SCRIPT_GENERATION_PROMPT.format(
        pyproject_toml_content=pyproject_toml_content,
        test_installation_guide=test_installation_guide,
        fallback_test_command=fallback_test_command
    )

    model_response = get_llm_response(
        user_input=prompt_pyproject_script_generation,
        model_id=state["bedrock_model_id"],
        inference_config={"maxTokens": 512, "temperature": 0}
    )

    # add token counts
    global TOTAL_INPUT_TOKENS, TOTAL_OUTPUT_TOKENS
    TOTAL_INPUT_TOKENS += model_response["usage"]["inputTokens"]
    TOTAL_OUTPUT_TOKENS += model_response["usage"]["outputTokens"]

    raw_script = model_response["output"]["message"]["content"][0]["text"]

    return {"raw_script": raw_script, "gen_source": "pyproject.toml"}

def generate_from_requirements_txt(state: State):
    files = state["rel_paths"]

    requirements_txt_paths = list(filter(lambda path: REGEX_REQUIREMENTS_TXT.search(path), files))

    installation_command_lst = ["pip install -r " + path for path in requirements_txt_paths]
    installation_command = "\n".join(installation_command_lst)

    testing_framework = state["testing_framework"]
    fallback_test_command = "python -m pytest ." if testing_framework == "pytest" else "python -m unittest discover"

    # rule-based
    raw_script = f"""```bash
#!/bin/bash
set -euo pipefail

# ----- Setup -----
{installation_command}

# ----- Test -----
{fallback_test_command}
```""".strip()

    return {"raw_script": raw_script, "gen_source": "requirements.txt"}

def generate_from_setup_py(state: State):
    files = state["rel_paths"]

    # assume there is only one setup.py file (usually in the repository root)
    setup_py_rel_path = list(filter(lambda path: REGEX_SETUP_PY.search(path), files))[0]

    path = Path(state["repo_root"]) / setup_py_rel_path
    with open(path) as f:
        setup_py_text = f.read()

    testing_framework = state["testing_framework"]
    fallback_test_command = "python -m pytest ." if testing_framework == "pytest" else "python -m unittest discover"

    prompt_setup_script_generation = SETUP_TEST_SCRIPT_GENERATION_PROMPT.format(
        setup_py_content=setup_py_text,
        fallback_test_command=fallback_test_command
    )

    model_response = get_llm_response(
        user_input=prompt_setup_script_generation,
        model_id=state["bedrock_model_id"],
        inference_config={"maxTokens": 512, "temperature": 0}
    )

    # add token counts
    global TOTAL_INPUT_TOKENS, TOTAL_OUTPUT_TOKENS
    TOTAL_INPUT_TOKENS += model_response["usage"]["inputTokens"]
    TOTAL_OUTPUT_TOKENS += model_response["usage"]["outputTokens"]

    raw_script = model_response["output"]["message"]["content"][0]["text"]

    return {"raw_script": raw_script, "gen_source": "setup.py"}

def extract_and_split_codeblock(state: State):
    raw_script = state["raw_script"]

    codeblock = extract_codeblock(raw_script)

    split_dic = split_script_by_section(codeblock)

    setup_script = split_dic["setup_script"]
    test_script = split_dic["test_script"]

    return {"setup_script": setup_script, "test_script": test_script}

def build_graph():
    graph_builder = StateGraph(State)

    ### nodes
    # set flags to decide from which file to generate test script
    graph_builder.add_node("check_exist_pyproject_toml", check_exist_pyproject_toml)
    graph_builder.add_node("check_exist_requirements_txt", check_exist_requirements_txt)
    graph_builder.add_node("check_exist_setup_py", check_exist_setup_py)

    # test script generation from each file type
    graph_builder.add_node("generate_from_pyproject_toml", generate_from_pyproject_toml)
    graph_builder.add_node("generate_from_requirements_txt", generate_from_requirements_txt)
    graph_builder.add_node("generate_from_setup_py", generate_from_setup_py)

    graph_builder.add_node("extract_and_split_codeblock", extract_and_split_codeblock)

    # ignore README, as it may contain some steps that cause unexpected change in the environment
    graph_builder.add_edge(START, "check_exist_pyproject_toml")

    graph_builder.add_conditional_edges(
        source="check_exist_pyproject_toml",
        path=has_pyproject_toml,
        path_map={True: "generate_from_pyproject_toml", False: "check_exist_requirements_txt"}
    )

    graph_builder.add_conditional_edges(
        source="check_exist_requirements_txt",
        path=has_requirements_txt,
        path_map={True: "generate_from_requirements_txt", False: "check_exist_setup_py"}
    )

    graph_builder.add_conditional_edges(
        source="check_exist_setup_py",
        path=has_setup_py,
        path_map={True: "generate_from_setup_py", False: END}
    )

    graph_builder.add_edge("generate_from_pyproject_toml", "extract_and_split_codeblock")
    graph_builder.add_edge("generate_from_requirements_txt", "extract_and_split_codeblock")
    graph_builder.add_edge("generate_from_setup_py", "extract_and_split_codeblock")

    graph_builder.add_edge("extract_and_split_codeblock", END)

    # compile
    graph = graph_builder.compile()

    return graph

def main(args):
    input_path = args.input_path
    save_path = args.save_path

    bedrock_model_id = args.model_id

    graph = build_graph()

    with open(input_path) as f_in, open(save_path, "w") as f_out:
        for line in tqdm(islice(f_in, args.limit)):
            # to avoid rate limit error
            time.sleep(30)

            line = line.strip()
            repo_dic = json.loads(line)

            repo_name = repo_dic["repo_name"]
            save_dir_name = repo_name.replace("/", "__")

            repo_dir = args.repo_dir_root / save_dir_name

            try:
                if not repo_dir.exists():
                    print(f"Repository {repo_name} does not exist, skipped.", file=sys.stderr)
                    continue

                repo_files = [str(path.relative_to(repo_dir)) for path in repo_dir.rglob("*") if path.is_file()]
            except Exception:
                print(f"An error occurred while processing repository {repo_name}", file=sys.stderr)
                continue

            available_tests = repo_dic["available_tests"]
            # prioritize pytest over unittest
            testing_framework = "pytest" if any(x["test_type"] == "pytest" for x in available_tests) else "unittest"

            try:
                result = graph.invoke(
                    {
                        "repo_dic": repo_dic,
                        "repo_root": str(repo_dir),
                        "rel_paths": repo_files,
                        "testing_framework": testing_framework,
                        "bedrock_model_id": bedrock_model_id
                    }
                )
            except Exception:
                print(f"An error occurred while processing repository: {repo_name}, skipped", file=sys.stderr)
                continue

            if "raw_script" not in result:
                # in case none of valid `pyproject.toml`, `requirements.txt`, `setup.py` files exist in the repository
                print(f"No test script generated for repository: {repo_name}, skipped", file=sys.stderr)
                continue

            script_source = result["gen_source"]

            setup_script = result["setup_script"]
            test_script = result["test_script"]

            # if any of the scripts is empty
            if not setup_script or not test_script:
                print(f"Script generation failed for repository: {repo_name}, skipped", file=sys.stderr)
                print(f"raw_script: {result['raw_script']}", file=sys.stderr)
                continue

            # if the test is implemented with unittest,
            # overwrite the test script to notice the location of the test files
            if testing_framework == "unittest":
                test_paths = [x["path"] for x in available_tests if x["test_type"] == "unittest"]
                test_script = overwrite_unittest_script_with_paths(test_script, test_paths)

            try:
                # unpin hardcoded version constraints in setup script
                unpinned_setup_script_lines = []

                for line in setup_script.splitlines():
                    if line.startswith("pip install"):
                        line = unpin_pip_install_line(line)
                    unpinned_setup_script_lines.append(line)

                unpinned_setup_script = "\n".join(unpinned_setup_script_lines)
            except Exception:
                unpinned_setup_script = ""
                print(f"Could not unpin hardcoded version constraints for repository: {repo_name}, skipped", file=sys.stderr)
                continue

            # The following line is left as-is to maintain consistency with the original experiments.
            # While this line might overwrite the unpinning logic for the model-generated setup scripts,
            # the configuration files themselves were already unpinned in the previous script (2-01).
            # Only affects cases where the model generates setup scripts with hardcoded version constraints.
            unpinned_setup_script = setup_script

            if script_source != "pyproject.toml" and testing_framework == "pytest":
                # for `pyproject.toml`, the installation command depends on the package manager used in the repository
                # therefore, we leave the model to output the command altogether
                # for other sources, we can assume that `pip` is used to manage the dependencies
                setup_script += "\npip install pytest"
                unpinned_setup_script += "\npip install pytest"

            repo_dic["script_source"] = script_source
            repo_dic["setup_script"] = setup_script
            repo_dic["unpinned_setup_script"] = unpinned_setup_script
            repo_dic["test_script"] = test_script

            print(json.dumps(repo_dic, ensure_ascii=False), file=f_out, flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="generate test scripts for repositories")
    parser.add_argument('--input_path', type=Path, required=True, help="the path to the input file with candidate repositories")
    parser.add_argument('--repo_dir_root', type=Path, required=True, help="the path to raw (cloned) repositories")
    parser.add_argument('--save_path', type=Path, required=True, help="the path to save output")
    parser.add_argument('--model_id', type=str, default="us.anthropic.claude-sonnet-4-20250514-v1:0", help="the model id to use for inference")
    parser.add_argument('--limit', type=int, help="the maximum number of repositories to process (optional)")

    args = parser.parse_args()
    main(args)
