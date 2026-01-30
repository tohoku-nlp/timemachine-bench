import csv
import sys
import json
import time
import atexit
import argparse
import datetime

from tqdm import tqdm
from pathlib import Path
from itertools import islice
from dicttoxml import dicttoxml
from xml.dom.minidom import parseString

from packaging.version import parse as parse_version
from packaging.specifiers import SpecifierSet

from typing import Dict, Any, List, Tuple
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END

from utils.const import REGEX_PYPROJECT_TOML, REGEX_SETUP_PY

from llm.bedrock_generate import get_llm_response
from llm.prompts.prompts_pyproject import PYPROJECT_PY_VER_DETECTION_PROMPT
from llm.prompts.prompts_setup import SETUP_PY_VER_DETECTION_PROMPT
from llm.prompts.prompts_readme import README_PY_VER_DETECTION_PROMPT

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

    # model to use
    bedrock_model_id: str
    available_version_lst: List[Tuple[str, datetime.date]]

    # the type of current file to use for generating test scripts
    gen_source: str

    # intermediate flags
    has_pyproject_toml: bool
    has_setup_py: bool
    has_readme_txt: bool

    has_valid_specifier: bool

    # output
    specifier: str
    target_version: str

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
        except:
            break
    else:
        is_readable = True

    return {"has_pyproject_toml": len(pyproject_toml_files) > 0 and is_readable}

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
        except:
            break
    else:
        is_readable = True

    return {"has_setup_py": len(setup_py_files) > 0 and is_readable}

def check_exist_readme_txt(state: State):
    files = state["rel_paths"]

    readme_txt_files = list(filter(lambda path: path in {"/README.md", "/README.rst"}, files))

    # check if readable
    is_readable = False
    for rel_path in readme_txt_files:
        path = Path(state["repo_root"]) / rel_path
        try:
            with open(path) as f:
                content = f.read()
        except:
            break
    else:
        is_readable = True

    return {"has_readme_txt": len(readme_txt_files) > 0 and is_readable}

def _check_has_valid_specifier(state: State):
    try:
        SpecifierSet(state["specifier"])
        return {"has_valid_specifier": True}
    except:
        return {"has_valid_specifier": False}

def check_has_valid_specifier_pyproject_toml(state: State):
    # just a wrapper for _check_has_valid_specifier, but defined separately to make the graph more readable
    return _check_has_valid_specifier(state)

def check_has_valid_specifier_setup_py(state: State):
    # just a wrapper for _check_has_valid_specifier, but defined separately to make the graph more readable
    return _check_has_valid_specifier(state)

def check_has_valid_specifier_readme_txt(state: State):
    # just a wrapper for _check_has_valid_specifier, but defined separately to make the graph more readable
    return _check_has_valid_specifier(state)

def has_pyproject_toml(state: State):
    return state["has_pyproject_toml"]

def has_setup_py(state: State):
    return state["has_setup_py"]

def has_readme_txt(state: State):
    return state["has_readme_txt"]

def has_valid_specifier(state: State):
    return state["has_valid_specifier"]

def read_from_pyproject_toml(state: State):
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

    prompt_pyproject_python_detection = PYPROJECT_PY_VER_DETECTION_PROMPT.format(
        pyproject_toml_content=pyproject_toml_content
    )

    model_response = get_llm_response(
        user_input=prompt_pyproject_python_detection,
        model_id=state["bedrock_model_id"],
        inference_config={"maxTokens": 512, "temperature": 0}
    )

    # add token counts
    global TOTAL_INPUT_TOKENS, TOTAL_OUTPUT_TOKENS
    TOTAL_INPUT_TOKENS += model_response["usage"]["inputTokens"]
    TOTAL_OUTPUT_TOKENS += model_response["usage"]["outputTokens"]

    specifier = model_response["output"]["message"]["content"][0]["text"]

    return {"specifier": specifier, "gen_source": "pyproject.toml"}

def read_from_setup_py(state: State):
    files = state["rel_paths"]

    # assume there is only one setup.py file (usually in the repository root)
    setup_py_rel_path = list(filter(lambda path: REGEX_SETUP_PY.search(path), files))[0]

    path = Path(state["repo_root"]) / setup_py_rel_path
    with open(path) as f:
        setup_py_text = f.read()

    prompt_setup_python_detection = SETUP_PY_VER_DETECTION_PROMPT.format(
        setup_py_content=setup_py_text
    )

    model_response = get_llm_response(
        user_input=prompt_setup_python_detection,
        model_id=state["bedrock_model_id"],
        inference_config={"maxTokens": 512, "temperature": 0}
    )

    # add token counts
    global TOTAL_INPUT_TOKENS, TOTAL_OUTPUT_TOKENS
    TOTAL_INPUT_TOKENS += model_response["usage"]["inputTokens"]
    TOTAL_OUTPUT_TOKENS += model_response["usage"]["outputTokens"]

    specifier = model_response["output"]["message"]["content"][0]["text"]

    return {"specifier": specifier, "gen_source": "setup.py"}

def read_from_readme_txt(state: State):
    files = state["rel_paths"]

    # use the first README.md or README.rst file (it is usually the top-level README file)
    readme_rel_path = list(filter(lambda path: path in {"/README.md", "/README.rst"}, files))[0]

    path = Path(state["repo_root"]) / readme_rel_path
    with open(path) as f:
        readme_txt = f.read()

    prompt_readme_python_detection = README_PY_VER_DETECTION_PROMPT.format(
        readme_content=readme_txt
    )

    model_response = get_llm_response(
        user_input=prompt_readme_python_detection,
        model_id=state["bedrock_model_id"],
        inference_config={"maxTokens": 512, "temperature": 0}
    )

    # add token counts
    global TOTAL_INPUT_TOKENS, TOTAL_OUTPUT_TOKENS
    TOTAL_INPUT_TOKENS += model_response["usage"]["inputTokens"]
    TOTAL_OUTPUT_TOKENS += model_response["usage"]["outputTokens"]

    specifier = model_response["output"]["message"]["content"][0]["text"]

    return {"specifier": specifier, "gen_source": "readme"}

def _get_target_python_version(available_version_lst, target_date, version_specifier=None):
    """
    if version_specifier is provided, return the latest version that matches the specifier and released before the target date.
    otherwise, check latest minor version released 1 year before the target date, and return the lastest patch version having the same major and minor versions.
    note: assuming that 1 year is sufficient to support a new minor version
    """
    version_spec_parsed = None

    if version_specifier:
        try:
            version_spec_parsed = SpecifierSet(version_specifier)
        except:
            print(f"Invalid version specifier: {version_specifier} found, fallback to date-based logic", file=sys.stderr)

    if version_spec_parsed:
        # filter versions by specifier and release date
        filtered_versions = [v for v in available_version_lst if (v[1] <= target_date) and (parse_version(v[0]) in version_spec_parsed)]

        if not filtered_versions:
            print("No matching version found, exit", file=sys.stderr)
            return

        # sort by version
        filtered_versions_sorted = sorted(filtered_versions, key=lambda x: parse_version(x[0]), reverse=True)
        # return the latest version
        target_version = filtered_versions_sorted[0][0]

    else:
        target_date_1y_before = target_date - datetime.timedelta(days=365)
        available_versions_1y_before = [x[0] for x in filter(lambda x: x[1] <= target_date_1y_before, available_version_lst)]

        if not available_versions_1y_before:
            print("No matching version found, exit", file=sys.stderr)
            return

        available_versions_1y_before_sorted = list(sorted(available_versions_1y_before, key=lambda x: parse_version(x), reverse=True))

        target_major, target_minor = parse_version(available_versions_1y_before_sorted[0]).major, parse_version(available_versions_1y_before_sorted[0]).minor

        filtered_versions = [v for v in available_version_lst if (v[1] <= target_date) and (parse_version(v[0]).major == target_major and parse_version(v[0]).minor == target_minor)]

        if not filtered_versions:
            print("No matching version found, exit", file=sys.stderr)
            return

        # sort by version
        filtered_versions_sorted = sorted(filtered_versions, key=lambda x: parse_version(x[0]), reverse=True)
        # return the latest version
        target_version = filtered_versions_sorted[0][0]

    # check if the candidate is equal to, or greater than version 3.6
    target_version_parsed = parse_version(target_version)

    if target_version_parsed < parse_version("3.6"):
        print(f"No matching version found, exit", file=sys.stderr)
        return

    return target_version

def get_target_python_version_with_specifier(state: State):
    repo_dic = state["repo_dic"]
    available_version_lst = state["available_version_lst"]

    commit_date_str = repo_dic["committer_date"]

    commit_date = datetime.datetime.strptime(commit_date_str, "%Y-%m-%d %H:%M:%S").date()

    version_specifier = state["specifier"]

    target_version = _get_target_python_version(available_version_lst, commit_date, version_specifier)

    return {"target_version": target_version}

def get_target_python_version_no_specifier(state: State):
    repo_dic = state["repo_dic"]
    available_version_lst = state["available_version_lst"]

    commit_date_str = repo_dic["committer_date"]

    commit_date = datetime.datetime.strptime(commit_date_str, "%Y-%m-%d %H:%M:%S").date()

    target_version = _get_target_python_version(available_version_lst, commit_date)

    return {"target_version": target_version, "specifier": "N/A", "gen_source": "default"}

def build_graph():
    graph_builder = StateGraph(State)

    ### nodes
    # set flags to decide from which file to select appropriate python version
    graph_builder.add_node("check_exist_pyproject_toml", check_exist_pyproject_toml)
    graph_builder.add_node("check_exist_setup_py", check_exist_setup_py)
    graph_builder.add_node("check_exist_readme_txt", check_exist_readme_txt)

    # get information about python version from each file type
    graph_builder.add_node("read_from_pyproject_toml", read_from_pyproject_toml)
    graph_builder.add_node("read_from_setup_py", read_from_setup_py)
    graph_builder.add_node("read_from_readme_txt", read_from_readme_txt)

    # check if extracted specifier is valid
    graph_builder.add_node("check_has_valid_specifier_pyproject_toml", check_has_valid_specifier_pyproject_toml)
    graph_builder.add_node("check_has_valid_specifier_setup_py", check_has_valid_specifier_setup_py)
    graph_builder.add_node("check_has_valid_specifier_readme_txt", check_has_valid_specifier_readme_txt)

    # select exact version
    graph_builder.add_node("get_target_python_version_with_specifier", get_target_python_version_with_specifier)
    graph_builder.add_node("get_target_python_version_no_specifier", get_target_python_version_no_specifier)

    ### edges

    graph_builder.add_edge(START, "check_exist_pyproject_toml")

    graph_builder.add_conditional_edges(
        source="check_exist_pyproject_toml",
        path=has_pyproject_toml,
        path_map={True: "read_from_pyproject_toml", False: "check_exist_setup_py"}
    )

    graph_builder.add_conditional_edges(
        source="check_exist_setup_py",
        path=has_setup_py,
        path_map={True: "read_from_setup_py", False: "check_exist_readme_txt"}
    )

    graph_builder.add_conditional_edges(
        source="check_exist_readme_txt",
        path=has_readme_txt,
        path_map={True: "read_from_readme_txt", False: "get_target_python_version_no_specifier"}
    )

    graph_builder.add_edge("read_from_pyproject_toml", "check_has_valid_specifier_pyproject_toml")

    graph_builder.add_conditional_edges(
        source="check_has_valid_specifier_pyproject_toml",
        path=has_valid_specifier,
        path_map={True: "get_target_python_version_with_specifier", False: "check_exist_setup_py"}
    )

    graph_builder.add_edge("read_from_setup_py", "check_has_valid_specifier_setup_py")

    graph_builder.add_conditional_edges(
        source="check_has_valid_specifier_setup_py",
        path=has_valid_specifier,
        path_map={True: "get_target_python_version_with_specifier", False: "check_exist_readme_txt"}
    )

    graph_builder.add_edge("read_from_readme_txt", "check_has_valid_specifier_readme_txt")

    graph_builder.add_conditional_edges(
        source="check_has_valid_specifier_readme_txt",
        path=has_valid_specifier,
        path_map={True: "get_target_python_version_with_specifier", False: "get_target_python_version_no_specifier"}
    )

    graph_builder.add_edge("get_target_python_version_with_specifier", END)
    graph_builder.add_edge("get_target_python_version_no_specifier", END)

    # compile
    graph = graph_builder.compile()

    return graph

def main(args):
    input_path = args.input_path
    save_path = args.save_path

    py_ver_list_path = args.py_ver_list_path

    available_version_lst = []

    with open(py_ver_list_path) as f:
        reader = csv.reader(f)
        for version_str, release_date in reader:
            release_date = datetime.datetime.strptime(release_date, "%Y-%m-%d").date()
            available_version_lst.append((version_str, release_date))

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

            try:
                result = graph.invoke(
                    {
                        "repo_dic": repo_dic,
                        "repo_root": str(repo_dir),
                        "rel_paths": repo_files,
                        "bedrock_model_id": bedrock_model_id,
                        "available_version_lst": available_version_lst,
                    }
                )
            except:
                print(f"An error occurred while processing repository: {repo_name}, skipped", file=sys.stderr)
                continue

            version_source = result["gen_source"]
            version_specifier = result["specifier"]
            target_version = result["target_version"]

            if target_version is None:
                print(f"No matching version found for repository: {repo_name}, skipped", file=sys.stderr)
                continue

            repo_dic["version_source"] = version_source
            repo_dic["version_specifier"] = version_specifier
            repo_dic["target_version"] = target_version

            print(json.dumps(repo_dic, ensure_ascii=False), file=f_out, flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="select appropriate Python version to use in the repository")
    parser.add_argument('--input_path', type=Path, required=True, help="the path to the input file with candidate repositories")
    parser.add_argument('--repo_dir_root', type=Path, required=True, help="the path to raw (cloned) repositories")
    parser.add_argument('--save_path', type=Path, required=True, help="the path to save output")
    parser.add_argument('--py_ver_list_path', type=Path, required=True, help="the path to the CSV file with available Python versions")
    parser.add_argument('--model_id', type=str, default="us.anthropic.claude-sonnet-4-20250514-v1:0", help="the model id to use for inference")
    parser.add_argument('--limit', type=int, help="the maximum number of repositories to process (optional)")

    args = parser.parse_args()
    main(args)
