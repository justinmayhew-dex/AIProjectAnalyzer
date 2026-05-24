import ast
import os
from typing import Optional

def parse_python(file_name, file_contents):
    tree = ast.parse(file_contents, filename=file_name)
    
    ir = {
        "path": file_path,
        "module_name": os.path.splitext(os.path.basename(file_path))[0],
        "imports": [],
        "exports": [],
        "functions": [],
        "classes": [],
        "has_main_guard": False
    }
    
    class Analyzer(ast.NodeVisitor):
        def visit_Import(self, node):
            for alias in node.names:
                ir["imports"].append({
                    "module": alias.name,
                    "names": [],
                    "alias": alias.asname,
                    "resolved_path": None,
                    "is_relative": False
                })
            self.generic_visit(node)
        
        def visit_ImportFrom(self, node):
            ir["imports"].append({
                "module": node.module if node.module else "",
                "names": [alias.name for alias in node.names],
                "alias": None,
                "resolved_path": None,
                "is_relative": node.level > 0
            })
            self.generic_visit(node)
        
        def visit_FunctionDef(self, node):
            ir["functions"].append({
                "name": node.name,
                "params": [arg.arg for arg in node.args.args],
                "returns": ast.unparse(node.returns) if node.returns else None,
                "decorators": [ast.unparse(d) for d in node.decorator_list],
                "is_async": isinstance(node, ast.AsyncFunctionDef),
                "calls": []  # optional for v1
            })
            # also check if function is top-level export
            if not node.name.startswith("_"):
                ir["exports"].append({
                    "name": node.name,
                    "type": "function",
                    "is_public": True
                })
            self.generic_visit(node)
        
        def visit_AsyncFunctionDef(self, node):
            self.visit_FunctionDef(node)  # same processing
        
        def visit_ClassDef(self, node):
            ir["classes"].append({
                "name": node.name,
                "bases": [ast.unparse(b) for b in node.bases],
                "methods": [
                    {
                        "name": m.name,
                        "params": [arg.arg for arg in m.args.args],
                        "returns": ast.unparse(m.returns) if m.returns else None,
                        "decorators": [ast.unparse(d) for d in m.decorator_list],
                        "is_async": isinstance(m, ast.AsyncFunctionDef),
                        "calls": []
                    } for m in node.body if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef))
                ],
                "decorators": [ast.unparse(d) for d in node.decorator_list]
            })
            # top-level export if public
            if not node.name.startswith("_"):
                ir["exports"].append({
                    "name": node.name,
                    "type": "class",
                    "is_public": True
                })
            self.generic_visit(node)
        
        def visit_Assign(self, node):
            for target in node.targets:
                if isinstance(target, ast.Name) and not target.id.startswith("_"):
                    ir["exports"].append({
                        "name": target.id,
                        "type": "variable",
                        "is_public": True
                    })
            self.generic_visit(node)
        
        def visit_If(self, node):
            # detect main guard: if __name__ == "__main__"
            if isinstance(node.test, ast.Compare):
                left = getattr(node.test.left, "id", None)
                comparators = [getattr(c, "s", getattr(c, "value", None)) for c in node.test.comparators]
                if left == "__name__" and comparators and comparators[0] == "__main__":
                    ir["has_main_guard"] = True
            self.generic_visit(node)
    
    Analyzer().visit(tree)
    return ir

# Example usage:
# ir = analyze_python_file("example.py")
# print(ir)
