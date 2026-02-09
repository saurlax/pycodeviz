import argparse
import logging
import sys
from pathlib import Path
from .parser import ProjectAnalyzer
from .complexity_analyzer import ComplexityAnalyzer
from .visualizer import Visualizer, check_graphviz_installed, graphviz_install_hint, SUPPORTED_FORMATS
from .report import ReportGenerator

logger = logging.getLogger(__name__)


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
    parser.add_argument(
        "--complexity",
        action="store_true",
        help="Generate code complexity report",
    )
    parser.add_argument(
        "--exclude",
        nargs="+",
        metavar="PATTERN",
        default=[],
        help="Exclude files/modules matching patterns (e.g. 'test_*' '*_legacy*')"
    )
    parser.add_argument(
        "--include",
        nargs="+",
        metavar="PATTERN",
        default=[],
        help="Only include files/modules matching patterns (e.g. 'core*' 'utils*')"
    )
    parser.add_argument(
        "--format",
        choices=sorted(SUPPORTED_FORMATS),
        default="svg",
        dest="output_format",
        help="Output format for visualizations (default: svg)"
    )
    parser.add_argument(
        "--report",
        nargs="?",
        const="report.html",
        metavar="FILE",
        help="Generate a self-contained HTML report with embedded SVG and metadata (default: report.html)"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output with detailed error messages for failed files"
    )

    args = parser.parse_args()

    # ── Configure logging ──────────────────────────────────────────────
    log_level = logging.DEBUG if args.verbose else logging.WARNING
    logging.basicConfig(
        format="%(levelname)s: %(message)s",
        level=log_level,
    )

    # ── Validate project path ──────────────────────────────────────────
    project_path = Path(args.project_path).resolve()
    if not project_path.exists():
        print(f"Error: Project path '{project_path}' does not exist")
        sys.exit(1)

    # ── Check Graphviz installation ────────────────────────────────────
    should_generate = args.all or args.call_graph or args.module_graph or args.hierarchy or args.flow or args.report
    if should_generate and not check_graphviz_installed():
        print(graphviz_install_hint())
        sys.exit(1)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # ── Analyze project ────────────────────────────────────────────────
    print(f"Analyzing project: {project_path}")
    if args.exclude:
        print(f"  Exclude patterns: {', '.join(args.exclude)}")
    if args.include:
        print(f"  Include patterns: {', '.join(args.include)}")

    analyzer = ProjectAnalyzer(
        str(project_path),
        exclude_patterns=args.exclude,
        include_patterns=args.include,
    )
    functions, classes = analyzer.analyze()

    # ── Analysis summary ───────────────────────────────────────────────
    print(f"\nAnalysis summary:")
    print(f"  Files analyzed : {len(analyzer.analyzed_files)}")
    print(f"  Files failed   : {len(analyzer.failed_files)}")
    print(f"  Functions found: {len(functions)}")
    print(f"  Classes found  : {len(classes)}")

    # Report failed files
    if analyzer.failed_files:
        print(f"\nWarning: {len(analyzer.failed_files)} file(s) failed to parse:")
        for fpath, err in analyzer.failed_files:
            print(f"  ✗ {fpath}")
            if args.verbose:
                print(f"    └─ {err}")
        if not args.verbose:
            print("  (use --verbose for detailed error messages)")

    if not functions and not classes:
        print("\nNo Python code found to analyze")
        return

    visualizer = Visualizer(functions, classes, output_format=args.output_format)

    # Generate requested visualizations
    should_generate = args.all or args.call_graph or args.module_graph or args.hierarchy or args.flow or args.complexity or args.report
    # ── Graph scale preview ────────────────────────────────────────────
    if should_generate:
        stats = visualizer.get_graph_stats()
        print(f"\nGraph scale preview (output format: {args.output_format}):")
        if args.all or args.call_graph:
            print(f"  Call graph     : {stats['call_graph_nodes']} nodes, {stats['call_graph_edges']} edges")
        if args.all or args.module_graph:
            print(f"  Module graph   : {stats['module_graph_nodes']} nodes, {stats['module_graph_edges']} edges")
        if args.all or args.hierarchy:
            print(f"  Hierarchy      : {stats['hierarchy_nodes']} nodes")
        print()

    # ── Generate visualizations ────────────────────────────────────────
    fmt = args.output_format
    if args.all or args.call_graph:
        visualizer.generate_call_graph(str(output_dir / f"call_graph.{fmt}"))

    if args.all or args.module_graph:
        visualizer.generate_module_graph(str(output_dir / f"module_graph.{fmt}"))

    if args.all or args.hierarchy:
        visualizer.generate_function_hierarchy(str(output_dir / f"hierarchy.{fmt}"))

    if args.flow:
        visualizer.generate_execution_flow(
            args.flow,
            max_depth=args.depth,
            output_path=str(output_dir / f"execution_flow.{fmt}")
        )

    if args.complexity:
        complexity_analyzer = ComplexityAnalyzer()
        complexity_analyzer.analyze(project_path, output_dir / "complexity_report.txt")

    if args.report:
        report_path = output_dir / args.report
        report_gen = ReportGenerator(
            functions=functions,
            classes=classes,
            project_path=project_path,
            analyzed_files=analyzer.analyzed_files,
            failed_files=analyzer.failed_files,
        )
        report_gen.generate(
            str(report_path),
            call_graph=True,
            module_graph=True,
            hierarchy=True,
            flow_entry=args.flow if args.flow else None,
            flow_depth=args.depth,
            include_complexity=True,
        )

    if not should_generate:
        print("\nNo visualization options specified. Use --help for available options.")
        print("Examples:")
        print("  pycodeviz . --all                          # Generate all visualizations")
        print("  pycodeviz . --call-graph                   # Generate call graph only")
        print("  pycodeviz . --flow mymodule:main           # Generate execution flow from entry point")
        print("  pycodeviz . --all --format png             # Output as PNG")
        print("  pycodeviz . --all --exclude 'test_*'       # Exclude test files")
        print("  pycodeviz . --report                       # Generate HTML report")
        print("  pycodeviz . --report my_report.html         # Specify report filename")


if __name__ == "__main__":
    main()
