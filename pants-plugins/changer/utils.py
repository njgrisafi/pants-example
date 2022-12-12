from typing import Optional, Iterator
import ast


def get_file_line_by_functions(root: ast.Module) -> dict[str, Optional[ast.FunctionDef]]:
    line_to_func_map: dict[str, Optional[ast.FunctionDef]] = {}
    activate_function: Optional[ast.FunctionDef] = None
    to_visit: list[tuple[ast.AST, Optional[ast.FunctionDef]]] = [
        (
            root,
            activate_function,
        )
    ]
    while to_visit:
        curr_node, active_function = to_visit.pop()
        for child_node in ast.iter_child_nodes(curr_node):
            if not getattr(child_node, "lineno", None):
                continue
            if isinstance(child_node, ast.FunctionDef):
                line_to_func_map[str(child_node.lineno)] = child_node
                to_visit.append((child_node, child_node))
                continue
            line_to_func_map[str(child_node.lineno)] = active_function
            to_visit.append((child_node, active_function))
    return line_to_func_map


def get_all_functions(root: ast.Module) -> list[ast.FunctionDef]:
    return list(get_functions_from_ast(root=root))


def get_functions_from_ast(root: ast.Module) -> Iterator[ast.FunctionDef]:
    for node in ast.iter_child_nodes(root):
        if isinstance(node, ast.ClassDef):
            res = list(get_functions_from_ast(root=node))  # type: ignore
            for r in res:
                yield r
        if isinstance(node, ast.FunctionDef):
            yield node
