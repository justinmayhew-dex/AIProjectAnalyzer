import os
import fnmatch
from pathlib import Path
from typing import List, Dict, Generator, Optional

DEFAULT_IGNORES = [
    ".git",
    "node_modules",
    "__pycache__",
    "dist",
    "build",
    ".venv",
    "venv"
]

DEFAULT_EXTENSIONS = [
    ".py", ".js", ".ts", ".tsx", ".jsx",
    ".java", ".go", ".rs", ".cpp", ".c",
    ".cs", ".php", ".rb"
]


class ProjectTreeWalker:
    def __init__(
        self,
        root: str,
        extensions: Optional[List[str]] = None,
        ignore_dirs: Optional[List[str]] = None,
        max_file_size_kb: int = 500
    ):
        self.root = Path(root).resolve()
        self.extensions = extensions or DEFAULT_EXTENSIONS
        self.ignore_dirs = set(ignore_dirs or DEFAULT_IGNORES)
        self.max_file_size_kb = max_file_size_kb

    def should_ignore(self, path: Path) -> bool:
        for ignore in self.ignore_dirs:
            if ignore in path.parts:
                return True
        return False

    def valid_extension(self, path: Path) -> bool:
        return path.suffix.lower() in self.extensions

    def walk(self) -> Generator[Path, None, None]:
        for dirpath, dirnames, filenames in os.walk(self.root):
            dirpath = Path(dirpath)

            # mutate dirnames in-place to prevent descent
            dirnames[:] = [
                d for d in dirnames
                if d not in self.ignore_dirs
            ]

            for filename in filenames:
                file_path = dirpath / filename
                if self.should_ignore(file_path):
                    continue
                if not self.valid_extension(file_path):
                    continue
                yield file_path

    def file_metadata(self, path: Path) -> Dict:
        stat = path.stat()
        return {
            "name": path.name,
            "path": str(path.relative_to(self.root)),
            "size_bytes": stat.st_size,
            "modified_time": stat.st_mtime,
        }

    def read_file_chunks(self, path: Path, chunk_size: int = 4000) -> Generator[str, None, None]:
        if path.stat().st_size > self.max_file_size_kb * 1024:
            return

        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            buffer = ""
            for line in f:
                buffer += line
                if len(buffer) >= chunk_size:
                    yield buffer
                    buffer = ""
            if buffer:
                yield buffer

    def build_index(self) -> List[Dict]:
        index = []
        for path in self.walk():
            meta = self.file_metadata(path)
            index.append(meta)
        return index
