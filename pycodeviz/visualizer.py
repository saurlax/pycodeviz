import platform
import shutil
import sys

import networkx as nx
from typing import Dict, Set, Tuple
from pathlib import Path
from .parser import FunctionInfo, ClassInfo, ProjectAnalyzer

SUPPORTED_FORMATS = {"svg", "png", "pdf"}


def check_graphviz_installed() -> bool:
    """Check if Graphviz is installed on the system."""
    return shutil.which("dot") is not None


def graphviz_install_hint() -> str:
    """Return a friendly installation hint for Graphviz based on the OS."""
    system = platform.system()
    lines = [
        "Error: Graphviz is not installed or not found in PATH.",
        "Graphviz is required to render visualizations.",
        "",
        "Installation instructions:",
    ]
    if system == "Darwin":
        lines.append("  macOS:   brew install graphviz")
    elif system == "Linux":
        lines.append("  Ubuntu/Debian: sudo apt-get install graphviz")
        lines.append("  Fedora:        sudo dnf install graphviz")
        lines.append("  Arch:          sudo pacman -S graphviz")
    elif system == "Windows":
        lines.append("  Windows: choco install graphviz")
        lines.append("           or download from https://graphviz.org/download/")
    else:
        lines.append("  Please visit https://graphviz.org/download/ for installation instructions.")
    lines.append("")
    lines.append("After installation, make sure the 'dot' command is available in your PATH.")
    return "\n".join(lines)


class CallGraph:
    """Build and manage function call graph"""

    def __init__(self, functions: Dict[str, FunctionInfo], classes: Dict[str, ClassInfo]):
        self.functions = functions
        self.classes = classes
        self.graph = nx.DiGraph()
        self._build_graph()

    def _build_graph(self) -> None:
        """Build networkx graph from call relationships"""
        for func_id, func_info in self.functions.items():
            self.graph.add_node(func_id, label=func_info.name)

            for called_id in func_info.calls:
                if called_id in self.functions:
                    self.graph.add_edge(func_id, called_id)

    def find_call_paths(self, source: str, target: str, max_length: int = 10) -> list:
        """Find all call paths between two functions"""
        try:
            paths = list(nx.all_simple_paths(self.graph, source, target, cutoff=max_length))
            return paths
        except nx.NetworkXNoPath:
            return []

    def get_call_depth(self, func_id: str) -> int:
        """Calculate call depth (max distance from entry points)"""
        if self.graph.in_degree(func_id) == 0:
            return 0

        max_depth = 0
        for caller in self.graph.predecessors(func_id):
            max_depth = max(max_depth, self.get_call_depth(caller) + 1)
        return max_depth

    def get_callers(self, func_id: str) -> Set[str]:
        """Get all functions that call this function"""
        return set(self.graph.predecessors(func_id))

    def get_callees(self, func_id: str) -> Set[str]:
        """Get all functions called by this function"""
        return set(self.graph.successors(func_id))


class Visualizer:
    """Generate visualization of code structure"""

    def __init__(self, functions: Dict[str, FunctionInfo], classes: Dict[str, ClassInfo],
                 output_format: str = "svg"):
        self.functions = functions
        self.classes = classes
        self.call_graph = CallGraph(functions, classes)
        if output_format not in SUPPORTED_FORMATS:
            print(f"Warning: unsupported format '{output_format}', falling back to svg")
            output_format = "svg"
        self.output_format = output_format

    def get_graph_stats(self) -> Dict[str, int]:
        """Return node and edge counts for each visualization type."""
        modules = set()
        module_edges = set()
        for func_id, func_info in self.functions.items():
            source_module = func_id.split(":")[0]
            modules.add(source_module)
            for called_id in func_info.calls:
                target_module = called_id.split(":")[0]
                if source_module != target_module:
                    module_edges.add((source_module, target_module))

        call_edges = 0
        for func_info in self.functions.values():
            for called_id in func_info.calls:
                if called_id in self.functions:
                    call_edges += 1

        return {
            "call_graph_nodes": len(self.functions),
            "call_graph_edges": call_edges,
            "module_graph_nodes": len(modules),
            "module_graph_edges": len(module_edges),
            "hierarchy_nodes": len(self.functions),
        }

    def _make_output_path(self, base_path: str) -> str:
        """Ensure the output path uses the configured format extension."""
        p = Path(base_path)
        return str(p.with_suffix(f".{self.output_format}"))

    def generate_call_graph(self, output_path: str = "call_graph.svg") -> None:
        """Generate overall call graph"""
        from graphviz import Digraph
        output_path = self._make_output_path(output_path)
        dot = Digraph(comment="Function Call Graph", format=self.output_format)
        dot.attr(rankdir="LR", overlap="false", splines="curved")
        dot.attr("node", shape="box", style="rounded", fontname="Arial")
        dot.attr("graph", bgcolor="white")

        for func_id in self.functions:
            module, path = func_id.split(":")
            label = path.split(".")[-1]
            dot.node(func_id, label=label, tooltip=func_id)

        for func_id, func_info in self.functions.items():
            for called_id in func_info.calls:
                if called_id in self.functions:
                    dot.edge(func_id, called_id)

        output_file = Path(output_path).with_suffix("")
        dot.render(str(output_file), cleanup=True)
        print(f"Call graph generated: {output_path}")

    def generate_module_graph(self, output_path: str = "module_graph.svg") -> None:
        """Generate module dependency graph"""
        from graphviz import Digraph
        output_path = self._make_output_path(output_path)
        dot = Digraph(comment="Module Dependency Graph", format=self.output_format)
        dot.attr(rankdir="TB", overlap="false")
        dot.attr("node", shape="folder", style="filled", fillcolor="lightblue")

        modules = set()
        for func_id in self.functions:
            module = func_id.split(":")[0]
            modules.add(module)

        for module in modules:
            dot.node(module, label=module)

        added_edges = set()
        for func_id, func_info in self.functions.items():
            source_module = func_id.split(":")[0]
            for called_id in func_info.calls:
                target_module = called_id.split(":")[0]
                edge = (source_module, target_module)
                if edge not in added_edges and source_module != target_module:
                    dot.edge(source_module, target_module)
                    added_edges.add(edge)

        output_file = Path(output_path).with_suffix("")
        dot.render(str(output_file), cleanup=True)
        print(f"Module graph generated: {output_path}")

    def generate_function_hierarchy(self, output_path: str = "hierarchy.svg") -> None:
        """Generate function hierarchy by module"""
        from graphviz import Digraph
        output_path = self._make_output_path(output_path)
        dot = Digraph(comment="Function Hierarchy", format=self.output_format)
        dot.attr(rankdir="TB", overlap="false")
        dot.attr("node", shape="box", style="rounded")

        modules = {}
        for func_id in self.functions:
            module = func_id.split(":")[0]
            if module not in modules:
                modules[module] = []
            modules[module].append(func_id)

        for module, funcs in sorted(modules.items()):
            with dot.subgraph(name=f"cluster_{module}") as subgraph:
                subgraph.attr(label=module, style="filled", fillcolor="lightgrey")
                for func_id in funcs:
                    _, path = func_id.split(":")
                    func_name = path.split(".")[-1]
                    subgraph.node(func_id, label=func_name)

        output_file = Path(output_path).with_suffix("")
        dot.render(str(output_file), cleanup=True)
        print(f"Hierarchy graph generated: {output_path}")

    def generate_execution_flow(self, entry_point: str, max_depth: int = 5,
                               output_path: str = "execution_flow.svg") -> None:
        """Generate execution flow starting from entry point"""
        from graphviz import Digraph
        output_path = self._make_output_path(output_path)
        dot = Digraph(comment=f"Execution Flow from {entry_point}", format=self.output_format)
        dot.attr(rankdir="TB", overlap="false")
        dot.attr("node", shape="box", style="rounded,filled", fillcolor="lightyellow")

        visited = set()

        def add_subgraph(node_id: str, depth: int) -> None:
            if depth > max_depth or node_id in visited:
                return
            visited.add(node_id)

            _, path = node_id.split(":")
            label = path.split(".")[-1]
            dot.node(node_id, label=label, color="black")

            callees = self.call_graph.get_callees(node_id)
            for callee_id in callees:
                dot.edge(node_id, callee_id)
                add_subgraph(callee_id, depth + 1)

        add_subgraph(entry_point, 0)

        output_file = Path(output_path).with_suffix("")
        dot.render(str(output_file), cleanup=True)
        print(f"Execution flow generated: {output_path}")
