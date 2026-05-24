import json
from pathlib import Path
from analyzer.walker import ProjectTreeWalker
from pydantic import BaseModel
from typing import Literal

try:
    from ollama import chat, ChatResponse
    _ollama_available = True
except ImportError:
    _ollama_available = False



def analyze_from_graph(processed_irs, root_path):
    num_files = len(processed_irs.items())
    count = 0
    for node, ir in processed_irs.items():
        file_path = Path(root_path) / Path(ir["path"])
        contents = file_path.read_text(encoding="utf8")
        dependency_summaries = list(
            map(
                lambda x: processed_irs.get(x, {}).get('summary', '<external>'),
                ir["dependants"]
            )
        )
        count += 1
        print("num_files", num_files, "count", count)
        summary = analyze_file_with_llm(ir, contents, dependency_summaries)
        #print(summary)
        processed_irs[node]["summary"] = summary

    return processed_irs

# Small placeholder heuristics for now
def simple_file_analysis(file_meta: dict, walker: ProjectTreeWalker) -> dict:
    """
    Performs a lightweight per-file analysis.
    Returns structured notes: size, complexity estimate, code smells (stub).
    """
    path = Path(file_meta["path"])
    full_path = walker.root / path

    # Chunking limit
    content_chunks = list(walker.read_file_chunks(full_path, chunk_size=4000))
    content_length = sum(len(chunk) for chunk in content_chunks)

    # Basic heuristics
    complexity_score = min(max(content_length // 500, 1), 5)
    code_smells = []

    if content_length > 5000:
        code_smells.append("large_file")
    if full_path.suffix in [".js", ".ts", ".tsx"] and "console.log" in "".join(content_chunks):
        code_smells.append("debug_statements")

    notes = {
        "file": str(path),
        "size_bytes": file_meta["size_bytes"],
        "chunks": len(content_chunks),
        "complexity_estimate": complexity_score,
        "code_smells": code_smells,
    }
    return notes


def analyze_project(root_path: str, extensions=None, ignore_dirs=None, max_file_size_kb=500) -> dict:
    """
    Walks the project and returns a structured analysis:
    {
        "files": [... per-file notes ...],
        "summary": {... aggregated info ...}
    }
    """
    walker = ProjectTreeWalker(
        root=root_path,
        extensions=extensions,
        ignore_dirs=ignore_dirs,
        max_file_size_kb=max_file_size_kb
    )

    file_notes = []
    file_anaysis = []
    for file_meta in walker.build_index():
        notes = simple_file_analysis(file_meta, walker)
        file_notes.append(notes)
        print(file_meta)
        full_path = walker.root / Path(file_meta["path"])
        file_contents = full_path.read_text(encoding="utf-8", errors="ignore")
        file_analysis_with_llm = analyze_file_with_llm(file_meta, file_contents, [])
        file_anaysis.append(file_analysis_with_llm)

    # Aggregation
    summary = {
        "total_files": len(file_notes),
        "high_complexity_files": [f["file"] for f in file_notes if f["complexity_estimate"] >= 4],
        "files_with_code_smells": [f["file"] for f in file_notes if f["code_smells"]],
        "total_code_smells": sum(len(f["code_smells"]) for f in file_notes)
    }
    return {
        "files": file_notes,
        "analysis": file_anaysis,
        "summary": summary
    }

class FileIssue(BaseModel):
    id: str
    category: Literal["security | reliability | types | performance | maintainability | architecture | accessibility | ux | docs | integration"]
    line: int | None
    description: str
    impact: str
    fix: str

class FileAnalysis(BaseModel):
    name: str
    responsibility_summary: str
    issues: list[FileIssue]



def analyze_file_with_llm(file_ir: dict, file_contents: str, depandancy_summaries: list, model: str = "ministral-3:3b") -> dict:
    if not _ollama_available:
        raise RuntimeError("Ollama client not installed. Install via pip.")
    file_name = file_ir["name"]

    prompt = f"""
    You are a static code analyzer.

    Analyze this file in isolation.
    Name: {file_name}
    Dependant: {depandancy_summaries}
    Contents: {file_contents}

    Provide a short summary and list of issues with concise descriptions, impact and fixes.
    
    Return strictly valid JSON matching this schema:
    {FileAnalysis.model_json_schema()}
    
    Rules:

    Only report concrete, observable issues.

    Each issue must belong to exactly one allowed category.

    No speculation.

    No extra keys.

    If no issues, return empty issues array.
    """
    #print(prompt)
    response: ChatResponse = chat(model=model, messages=[
        {
            'role': "user",
            'content': prompt,
            'format': FileAnalysis.model_json_schema()
        }
    ])
    # Attempt to parse JSON from response
    print("load_duration", response.load_duration / 1_000_000_000, "s")
    print("prompt_eval_duration", response.prompt_eval_duration /  1_000_000_000, "s")
    print("eval_duration", response.eval_duration /  1_000_000_000, "s")
    print("")
    print(response.message.content)
    return response.message.content


def summarize_with_llm(analysis: dict, model: str = "ministral-3:3b") -> dict:
    """
    Uses Ollama to generate a high-level summary of project analysis.
    Returns structured JSON with keys: key_files, hotspots, recommendations.
    """
    if not _ollama_available:
        raise RuntimeError("Ollama client not installed. Install via pip.")


    prompt = f"""
You are a project analyst. Here are the structured file notes:

{json.dumps(analysis, indent=2)}

Please summarize:
- Key files to review
- Overall complexity hotspots
- Suggestions for attention

    """

    response: ChatResponse = chat(model=model, messages=[
        {
            'role': "user",
            'content': prompt,
        }
    ])
    # Attempt to parse JSON from response
    try:
        return response.message.content
    except:
        # fallback: return raw text
        return {"raw_summary": response.message.content}

def save_analysis(analysis: dict, output_path: str):
    Path(output_path).write_text(json.dumps(analysis, indent=2))
