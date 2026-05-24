import json
from pathlib import Path
import networkx as nx

# -----------------------------
# CONFIG
# -----------------------------
JSON_FILE = "summarized.json"       # Path to your JSON file
OUTPUT_FILE = "summaries.txt"      # File to save readable summaries
USE_GRAPH_ORDER = False            # Set True if you have a dependency graph
GRAPH_FILE = None                  # Optional: load or build a graph if needed
# -----------------------------

# 1. Load JSON
with open(JSON_FILE, "r", encoding="utf8") as f:
    modules = json.load(f)  # dict: {module_name: metadata}

# 2. Optional: Build dependency graph if you want topological order
G = nx.DiGraph()
if USE_GRAPH_ORDER:
    # Assuming each module has a "dependants" or "imports" field
    for name, info in modules.items():
        G.add_node(name)
        for dep in info.get("dependants", []):
            G.add_edge(name, dep)

    try:
        topo_order = list(nx.topological_sort(G))
        # Reverse topological order: leaves first
        ordered_modules = topo_order[::-1]
    except nx.NetworkXUnfeasible:
        print("Cycle detected in graph! Falling back to JSON order.")
        ordered_modules = list(modules.keys())
else:
    ordered_modules = list(modules.keys())

# 3. Extract summaries
summaries = {
    name: info.get("summary", "<no summary>")
    for name, info in modules.items()
}

# 4. Print and save readable output
output_lines = []
for name in ordered_modules:
    summary_text = summaries.get(name, "<no summary>")
    print(f"=== {name} ===\n")
    print(summary_text)
    print("\n" + "="*80 + "\n")

    output_lines.append(f"=== {name} ===\n")
    output_lines.append(summary_text + "\n")
    output_lines.append("="*80 + "\n")

# Save to file
with open(OUTPUT_FILE, "w", encoding="utf8") as f:
    f.writelines(output_lines)

print(f"Summaries saved to {OUTPUT_FILE}")
