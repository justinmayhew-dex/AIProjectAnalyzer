import argparse
import json
from pathlib import Path


from analyzer.walker import ProjectTreeWalker
from analyzer.analysis import analyze_project, save_analysis, summarize_with_llm, analyze_from_graph
from analyzer.extractor import extract_from_project
from analyzer.grapher import create_dependency_graph
def cmd_analyze(args):
    analysis = analyze_project(
        root_path=args.path,
        extensions=args.extensions,
        ignore_dirs=args.ignore,
        max_file_size_kb=args.max_size
    )

    if args.output:
        save_analysis(analysis, args.output)
    else:
        print(json.dumps(analysis, indent=2))
    return
    print('its')
    if getattr(args, "summarize", False):
        print('true')
        try:
            summary = summarize_with_llm(analysis, model=args.model)
            print("\n=== LLM Summary ===")
            print(json.dumps(summary, indent=2))
        except Exception as e:
            print(f"Error generating LLM summary: {e}")

def cmd_extract(args):
    #file_irs = extract_from_project(args.path, args.extensions, args.ignore, args.max_size)
    with open("irs.json", "r") as f:
        file_irs = json.load(f)
    print(file_irs[0])
    processed_irs = create_dependency_graph(file_irs) 
    irs_with_summary = analyze_from_graph(processed_irs, args.path)
    
    Path("./summarized.json").write_text(json.dumps(irs_with_summary, indent=2))

def cmd_index(args):
    walker = ProjectTreeWalker(
        root=args.path,
        extensions=args.extensions,
        ignore_dirs=args.ignore,
        max_file_size_kb=args.max_size
    )

    index = walker.build_index()

    if args.output:
        output_path = Path(args.output)
        output_path.write_text(json.dumps(index, indent=2))
    else:
        print(json.dumps(index, indent=2))


def cmd_list(args):
    absolute_path = Path(args.path).resolve()
    print(absolute_path)
    walker = ProjectTreeWalker(
        root=absolute_path,
        extensions=args.extensions,
        ignore_dirs=args.ignore
    )

    for path in walker.walk():
        print(path.relative_to(absolute_path))


def build_parser():
    parser = argparse.ArgumentParser(
        prog="project-analyzer",
        description="Deterministic project tree analysis tool."
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # index command
    index_parser = subparsers.add_parser(
        "index",
        help="Build JSON metadata index of project files"
    )
    index_parser.add_argument("path", help="Path to project root")
    
    index_parser.add_argument("--extensions", nargs="*", default=None)
    index_parser.add_argument("--ignore", nargs="*", default=None)
    index_parser.add_argument("--max-size", type=int, default=500)
    index_parser.add_argument("--output", help="Write output to file")
    index_parser.set_defaults(func=cmd_index)

    # list command
    list_parser = subparsers.add_parser(
        "list",
        help="List filtered project files"
    )
    list_parser.add_argument("path", help="Path to project root")
    list_parser.add_argument("--extensions", nargs="*", default=None)
    list_parser.add_argument("--ignore", nargs="*", default=None)
    list_parser.set_defaults(func=cmd_list)
   
    analyze_parser = subparsers.add_parser(
        "analyze",
        help="analyze project files and produce structured notes"
    )
    analyze_parser.add_argument("path", help="Path to project root")
    analyze_parser.add_argument("--extensions", nargs="*", default=None)
    analyze_parser.add_argument("--ignore", nargs="*", default=None)
    analyze_parser.add_argument("--max-size", type=int, default=500)
    analyze_parser.add_argument("--output", help="Write analysis to file")
    analyze_parser.set_defaults(func=cmd_analyze)
    analyze_parser.add_argument(
        "--summarize",
        action="store_true",
        help="Generate high-level summary using LLM"
    )
    analyze_parser.add_argument(
        "--model",
        default="ministral-3:3b",
        help="Specify local Ollama model for summarization"
    )
    extract_parser = subparsers.add_parser(
        "extract",
        help="Extract intermediate representation data (IR) from a file"
    )

    extract_parser.add_argument("path")
    extract_parser.add_argument("--extensions", nargs="*", default=None)
    extract_parser.add_argument("--ignore", nargs="*", default=None)
    extract_parser.add_argument("--max-size", type=int, default=500)

    extract_parser.set_defaults(func=cmd_extract)
    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    print(args)
    args.func(args)


if __name__ == "__main__":
    main()
