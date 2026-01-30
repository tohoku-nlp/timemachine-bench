import ast
from typing import List, Tuple

class ImportStmtVisitor(ast.NodeVisitor):
    """
    find import or from-import statements included in the specified line
    """
    def __init__(self, line_no: int):
        self.line_no = line_no
        self.found_node = None

    def _check_node_included(self, node):
        start_line = node.lineno
        end_line = getattr(node, "end_lineno", start_line)
        if start_line <= self.line_no <= end_line:
            self.found_node = node

    def visit_Import(self, node: ast.Import):
        self._check_node_included(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        if node.level == 0:
            self._check_node_included(node)

class ImportMapVisitor(ast.NodeVisitor):
    """
    explore the AST tree and create a mapping from imported names to module names.
    'import numpy as np' -> {'np': 'numpy'}
    'from os.path import join' -> {'join': 'os.path'}
    """
    def __init__(self):
        self.import_map = {}

    # the name of the method must be like visit_{node.__class__.__name__}
    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            local_name = alias.asname or alias.name
            self.import_map[local_name] = alias.name

    def visit_ImportFrom(self, node: ast.ImportFrom):
        if node.level == 0:
            # "from {...}" part
            module_name = node.module or ""
            # "import {...}" part
            for alias in node.names:
                local_name = alias.asname or alias.name
                self.import_map[local_name] = module_name

class ImportedIdentifierVisitor(ast.NodeVisitor):
    """
    find module-related identifiers with in a Name node
    """
    def __init__(self, line_no, imported_name_set):
        self.line_no = line_no
        self.imported_name_set = imported_name_set
        # tuple of (line_number, column_number, identifier)
        self.found_identifiers: List[Tuple[int, int, str]] = []

    def visit_Name(self, node: ast.Name):
        if (hasattr(node, "lineno") and \
            node.lineno == self.line_no and \
            node.id in self.imported_name_set):
            self.found_identifiers.append((node.lineno, node.col_offset, node.id))

def ast_find_variable_assignments(ast_tree, target_name):
    # variables with same name can be defined more than twice in different conditional branches
    for node in ast.walk(ast_tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == target_name:
                    yield node

def ast_extract_func_kwargs(call_node):
    # find kwargs (variable length arguments) in function arguments
    for key_node in call_node.keywords:
        if key_node.arg is None:
            return key_node

def ast_find_related_module(fpath, line_no, local_modules=None):
    try:
        with open(fpath) as f:
            source_code = f.read()

        tree = ast.parse(source_code)

        stmt_visitor = ImportStmtVisitor(line_no)
        stmt_visitor.visit(tree)
        import_stmt_node = stmt_visitor.found_node

        if local_modules is None:
            local_modules = set()

        if import_stmt_node:
            # the line itself is an import statement
            if isinstance(import_stmt_node, ast.Import):
                return ", ".join(alias.name.split(".")[0] for alias in import_stmt_node.names if alias.name not in local_modules) or None
            if isinstance(import_stmt_node, ast.ImportFrom):
                return import_stmt_node.module.split(".")[0] if import_stmt_node.module not in local_modules else None
            return None
        else:
            # the line is ordinary expression
            map_visitor = ImportMapVisitor()
            map_visitor.visit(tree)
            import_map = map_visitor.import_map
            imported_name_set = set(import_map.keys())

            id_visitor = ImportedIdentifierVisitor(line_no, imported_name_set)
            id_visitor.visit(tree)
            candidates = sorted(id_visitor.found_identifiers, key=lambda x: (x[0], x[1]))

            if not candidates:
                return None

            if candidates:
                first_candidate = candidates[0][2]
                if first_candidate in import_map:
                    return import_map[first_candidate].split(".")[0] if import_map[first_candidate] not in local_modules else None
                else:
                    return None

    except Exception:
        return None

    return None
