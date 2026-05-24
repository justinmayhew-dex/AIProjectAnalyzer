import subprocess
import json

def parse_typescript(file_path, project_root, file_contents):
    print('project_root', project_root, "file_path", file_path)
    result = subprocess.run(
        ["node", "./analyzer/parsers/typescript/parser.es", file_path, project_root],
        input=file_contents,
        encoding="utf-8",
        capture_output=True,
        text=True
    )
    print(result.stderr)
    ast = json.loads(result.stdout)
    return ast

