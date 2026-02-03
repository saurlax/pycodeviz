import argparse
import sys
from pathlib import Path
from .parser import ProjectAnalyzer
from .visualizer import Visualizer


def main():
    parser = argparse.ArgumentParser(
        description="Visualize Python project code structure and call relationships"
    )
    parser.add_argument(
        "project_path",
        nargs="?",
        default=".",
        help="Path to Python project (default: current directory)"
    )
    parser.add_argument(
        "--call-graph",
        action="store_true",
        help="Generate function call graph"
    )
    parser.add_argument(
        "--module-graph",
        action="store_true",
        help="Generate module dependency graph"
    )
    parser.add_argument(
        "--hierarchy",
        action="store_true",
        help="Generate function hierarchy"
    )
    parser.add_argument(
        "--flow",
        type=str,
        metavar="ENTRY_POINT",
        help="Generate execution flow starting from entry point (format: module:function)"
    )
    parser.add_argument(
        "--depth",
        type=int,
        default=5,
        help="Max depth for execution flow (default: 5)"
    )
    parser.add_argument(
        "--output-dir",
        default=".",
        help="Output directory for visualizations (default: current directory)"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Generate all visualizations"
    )

    args = parser.parse_args()

    project_path = Path(args.project_path).resolve()
    if not project_path.exists():
        print(f"Error: Project path '{project_path}' does not exist")
        sys.exit(1)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Analyzing project: {project_path}")
    analyzer = ProjectAnalyzer(str(project_path))
    functions, classes = analyzer.analyze()

    print(f"Found {len(functions)} functions and {len(classes)} classes")

    if not functions and not classes:
        print("No Python code found to analyze")
        return

    visualizer = Visualizer(functions, classes)

    # Generate requested visualizations
    should_generate = args.all or args.call_graph or args.module_graph or args.hierarchy or args.flow

    if args.all or args.call_graph:
        visualizer.generate_call_graph(str(output_dir / "call_graph.svg"))

    if args.all or args.module_graph:
        visualizer.generate_module_graph(str(output_dir / "module_graph.svg"))

    if args.all or args.hierarchy:
        visualizer.generate_function_hierarchy(str(output_dir / "hierarchy.svg"))

    if args.flow:
        visualizer.generate_execution_flow(
            args.flow,
            max_depth=args.depth,
            output_path=str(output_dir / "execution_flow.svg")
        )

    if not should_generate:
        print("\nNo visualization options specified. Use --help for available options.")
        print("Examples:")
        print("  pycodeviz . --all                          # Generate all visualizations")
        print("  pycodeviz . --call-graph                   # Generate call graph only")
        print("  pycodeviz . --flow mymodule:main           # Generate execution flow from entry point")


if __name__ == "__main__":
    main()
