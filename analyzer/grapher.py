import networkx as nx
import collections
from graphviz import Digraph

def create_dependency_graph(file_irs):
    G = nx.DiGraph()

    # Map module paths for quick lookup
    project_modules = {ir["name"]: ir for ir in file_irs}

    # Add all modules as nodes (internal)
    for path in project_modules:
        G.add_node(path, type="internal")

    # Add edges for imports
    for ir in file_irs:
        src = ir["name"]

        for imp in ir.get("imports", []):
            target_path = imp["name"]

            # Check if internal or external
            if target_path in project_modules:
                G.add_edge(src, target_path)
            else:
                # External dependency
                G.add_node(target_path, type="external")
                G.add_edge(src, target_path)

    # Build Graphviz output
    dot = Digraph("DependencyTree")
    dot.attr(rankdir="LR")

    for node, data in G.nodes(data=True):
        if data.get("type") == "external":
            dot.node(node, shape="box", style="filled", fillcolor="lightgray")
        else:
            dot.node(node, shape="ellipse")

    for u, v in G.edges():
        dot.edge(u, v)

    dot.render("dependency_tree", format="png", cleanup=True)
    
    graph_metrics = analyze_graph(G)
    processed_irs = collections.OrderedDict()
    print(graph_metrics['topo_order'])
    for node in graph_metrics["topo_order"]:
        for ir in file_irs:
            if ir["name"] == node:
                dependants = list(G.successors(node))
                ir["betweenness"] = graph_metrics["betweenness"][node]
                ir["dependants"] = dependants
                processed_irs[node] = ir

    return processed_irs

def analyze_graph(graph):
    betweenness = nx.betweenness_centrality(graph)
    try:
        topo_order = list(nx.topological_sort(graph))[::-1]
    except nx.NetworkXUnfeasible:
        print("Cycle detected! Resolve circular dependencies first.")
    
    return {
        "topo_order": topo_order,
        "betweenness": betweenness,
    }
# Example usage:
# create_dependency_graph([your IR list])

