
import ast
import shlex

from packaging.version import Version
from packaging.requirements import Requirement, SpecifierSet

from utils.ast_utils import ast_find_variable_assignments

from utils.const import PIP_OPTIONS_WITH_ARGS
from utils.const import AST_SETUP_PY_VERSION_KEYWORDS
from packaging.specifiers import SpecifierSet

def unpin_single_package(req_text):
    """
    Remove version pinning from requirements string.
    Keep lower bounds (`>=` or `>`).
    """
    if req_text.startswith(".") or req_text.startswith("/"):
        # local package
        return req_text

    if any((x in req_text) for x in {"http://", "https://", "git://", "git+"}):
        raise Exception("Packages outside package manager are not allowed.")

    try:
        req = Requirement(req_text)
    except Exception:
        # re-raise original exc (ex. version specifiers are in non-standard format)
        raise

    package_name = req.name

    if req.extras:
        package_name += f"[{', '.join(req.extras)}]"

    return package_name

def unpin_pip_install_line(text):
    tokens = shlex.split(text)

    # skip `pip install`
    tokens = tokens[2:]
    it = iter(tokens)

    arguments = []

    for token in it:
        if token.startswith('-'):
            arguments.append(token)
            if token in PIP_OPTIONS_WITH_ARGS:
                next_token = next(it, None)
                if next_token is not None:
                    arguments.append(next_token)
        else:
            arguments.append(unpin_single_package(token))

    unpinned_command = "pip install " + shlex.join(arguments)

    return unpinned_command

def unpin_pep_or_semver_requirements(spec_str):
    def _convert_semver_to_pep(spec_str):
        spec_str = spec_str.lstrip("^")

        lower_bound = Version(spec_str)
        lower_bound_str = str(lower_bound)

        # get version numbers in tuple
        release = lower_bound.release

        # SemVer allows update if the new version number does not modify the left-most non-zero digit in the major, minor, patch grouping
        if release[0] != 0:
            # if major is not 0, increment major
            upper_bound_parts = (release[0] + 1, 0, 0)
        elif len(release) > 1 and release[1] != 0:
            # if major is 0 and minor is not 0, increment minor
            upper_bound_parts = (0, release[1] + 1, 0)
        elif len(release) > 2:
            # if major and minor are 0, increment patch
            upper_bound_parts = (0, 0, release[2] + 1)
        else:
            # "^0"
            upper_bound_parts = (1, 0, 0)

        upper_bound_str = ".".join(map(str, upper_bound_parts))

        return f">={lower_bound_str},<{upper_bound_str}"

    try:
        if spec_str.startswith("^"):
            # convert SemVer to PEP 440
            spec_str = _convert_semver_to_pep(spec_str)

        specifier = SpecifierSet(spec_str)

        lower_bound_specs = [spec for spec in specifier if spec.operator in ('>', '>=')]

        if lower_bound_specs:
            # Create a new specifier set with only lower bounds
            lower_bound_specifier = SpecifierSet(','.join(str(spec) for spec in lower_bound_specs))

        lower_bound_specifier_str = str(lower_bound_specifier)
    except Exception:
        # return original
        lower_bound_specifier_str = spec_str

    return lower_bound_specifier_str

# ast
def ast_find_setup_call(ast_tree):
    # find the call of `setup` method
    for node in ast.walk(ast_tree):
        if isinstance(node, ast.Call):
            if (isinstance(node.func, ast.Name) and node.func.id == 'setup') or \
            (isinstance(node.func, ast.Attribute) and node.func.attr == 'setup'):
                return node
    return

def ast_unpin_loop_list(list_node):
    # unpin all version contraints specified in a list
    if isinstance(list_node, ast.List):
        for el in list_node.elts:
            el.value = unpin_single_package(el.value)

def ast_unpin_list_or_reference(ast_tree, value_node):
    # unpin all version contraints specified in a list, but considers variables and look for references
    if isinstance(value_node, ast.List):
        return ast_unpin_loop_list(value_node)

    elif isinstance(value_node, ast.Name):
        var_name = value_node.id
        for assign_node in ast_find_variable_assignments(ast_tree, var_name):
            if isinstance(assign_node.value, ast.List):
                ast_unpin_loop_list(assign_node.value)

def ast_unpin_dict_of_list(ast_tree, value_node):
    # unpin all version dependencies in a dict of list (like `extras_require`)
    if isinstance(value_node, ast.Call) and hasattr(value_node.func, 'id') and value_node.func.id == "dict":
        # dict(key=value) format (constructor)
        for dict_node in value_node.keywords:
            ast_unpin_list_or_reference(ast_tree, dict_node.value)
    elif isinstance(value_node, ast.Dict):
        # dict object
        for value in value_node.values:
            ast_unpin_list_or_reference(ast_tree, value)

def ast_unpin_call_args(ast_tree, call_node):
    for i, key_node in enumerate(call_node.keywords):
        dep_key = key_node.arg

        if dep_key == "python_requires":
            val_node = key_node.value
            if isinstance(val_node, ast.Constant):
                val_node.value = unpin_pep_or_semver_requirements(val_node.value)

        if dep_key not in AST_SETUP_PY_VERSION_KEYWORDS:
            continue

        if dep_key in {"install_requires", "setup_requires", "tests_require"}:
            ast_unpin_list_or_reference(ast_tree, key_node.value)

        elif dep_key == "extras_require":
            ast_unpin_dict_of_list(ast_tree, key_node.value)

def ast_unpin_dict_args(ast_tree, keys_node, values_node):
    py_req_node_idxs = []

    for i, (key_node, value_node) in enumerate(zip(keys_node, values_node)):
        dep_key = key_node.value

        if dep_key == "python_requires":
            py_req_node_idxs.append(i)
            continue

        if dep_key not in AST_SETUP_PY_VERSION_KEYWORDS:
            continue

        if dep_key in {"install_requires", "setup_requires", "tests_require"}:
            ast_unpin_list_or_reference(ast_tree, value_node)

        elif dep_key == "extras_require":
            ast_unpin_dict_of_list(ast_tree, value_node)

    # remove `python requires`
    for i in reversed(py_req_node_idxs):
        del keys_node[i]
        del values_node[i]
