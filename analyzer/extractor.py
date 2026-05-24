"""
# FILE IR (intermediate representaion)
{
    path: str,
    module_name: str,
    imports: [
    {
        module: str, # raw import target
        names: [str], # specific symbols imported (if any)
        alias: Optional[str],
        resolved_path: Optional[str], # resolved inside project if possible
        is_relative: bool
    }
    ],
    exports: [
    {
        name: str,
        type: "function" | "class" | "variable",
        is_public: bool
    }
    ],
    functions: [
    {
        name: str,
        params: [...],
        returns: Optional[str],
        decorators: [...],
        is_async: bool,
        calls: [str] # optional for v1
    }
    ],
    classes: [
    {
        name: str,
        bases: [...],
        methods: [...],
        decorators: [...]
    }
    ],
    has_main_guard: bool
}
"""

import ast
import json
from pathlib import Path
from analyzer.walker import ProjectTreeWalker
from analyzer.grapher import create_dependency_graph 

from analyzer.parsers.typescript.parser import parse_typescript
from analyzer.parsers.python.parser import parse_python

def extract_from_project(root_path, extensions, ignore_dirs, max_file_size_kb):
    walker = ProjectTreeWalker( root=root_path,
        extensions=extensions,
        ignore_dirs=ignore_dirs,
        max_file_size_kb=max_file_size_kb
    )
    file_irs = []
    for file_meta in walker.build_index():

        print(file_meta)
        ir = extract_from_file(file_meta, root_path)
        if ir is not None:
            file_irs.append(ir)

    Path("./irs.json").write_text(json.dumps(file_irs, indent=2))
    return file_irs    

def produce_ast(file_path, project_root, extension, source):
    if extension in ('tsx', 'ts'):
        return parse_typescript(file_path, project_root, source)
    elif extension == 'py':
        return parse_python(file_path, source)
    else:
        print(f"Unsupported extension: {extension}, skipping.")
        return None

def extract_from_file(file_meta, project_root):
    path = Path(project_root) / file_meta["path"]
    extension = file_meta["name"].split('.')[-1]
    source = Path(path).read_text(encoding="utf-8")
    
    print(extension, Path(file_meta["path"]), Path(project_root).resolve())
    return produce_ast(Path(file_meta["path"]), Path(project_root).resolve(), extension, source)

