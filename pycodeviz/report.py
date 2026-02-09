"""
HTML Report Generator for PyCodeViz

Generates a self-contained HTML report embedding SVG visualizations
and project metadata.
"""

import ast
import html
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .parser import FunctionInfo, ClassInfo
from .visualizer import Visualizer


class ReportGenerator:
    """Generate a self-contained HTML report with embedded SVG and metadata."""

    def __init__(
        self,
        functions: Dict[str, FunctionInfo],
        classes: Dict[str, ClassInfo],
        project_path: Path,
        analyzed_files: List[str],
        failed_files: List[Tuple[str, str]],
    ):
        self.functions = functions
        self.classes = classes
        self.project_path = project_path
        self.analyzed_files = analyzed_files
        self.failed_files = failed_files
        self.visualizer = Visualizer(functions, classes, output_format="svg")

    # ── SVG generation helpers ─────────────────────────────────────────

    def _generate_svg(self, gen_method, filename: str) -> Optional[str]:
        """Call a Visualizer generate_* method and return the SVG content."""
        with tempfile.TemporaryDirectory() as tmpdir:
            out = str(Path(tmpdir) / filename)
            try:
                gen_method(out)
                svg_path = Path(out)
                if svg_path.exists():
                    return svg_path.read_text(encoding="utf-8")
            except Exception:
                return None
        return None

    def _collect_svgs(
        self,
        call_graph: bool = True,
        module_graph: bool = True,
        hierarchy: bool = True,
        flow_entry: Optional[str] = None,
        flow_depth: int = 5,
    ) -> Dict[str, Optional[str]]:
        """Generate requested SVG diagrams and return as a dict."""
        svgs: Dict[str, Optional[str]] = {}
        if call_graph:
            svgs["call_graph"] = self._generate_svg(
                self.visualizer.generate_call_graph, "call_graph.svg"
            )
        if module_graph:
            svgs["module_graph"] = self._generate_svg(
                self.visualizer.generate_module_graph, "module_graph.svg"
            )
        if hierarchy:
            svgs["hierarchy"] = self._generate_svg(
                self.visualizer.generate_function_hierarchy, "hierarchy.svg"
            )
        if flow_entry:
            def _gen_flow(path: str):
                self.visualizer.generate_execution_flow(
                    flow_entry, max_depth=flow_depth, output_path=path
                )
            svgs["execution_flow"] = self._generate_svg(_gen_flow, "execution_flow.svg")
        return svgs

    # ── Complexity data ────────────────────────────────────────────────

    def _compute_complexity(self) -> List[Dict]:
        """Compute per-function complexity metrics."""
        results: List[Dict] = []
        for py_file in self.project_path.rglob("*.py"):
            skip_dirs = {".venv", ".git", "__pycache__", ".pytest_cache", "venv", "env"}
            if any(part in skip_dirs for part in py_file.parts):
                continue
            try:
                source = py_file.read_text(encoding="utf-8")
                tree = ast.parse(source)
            except Exception:
                continue
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    complexity = 1
                    for child in ast.walk(node):
                        if isinstance(child, (ast.If, ast.IfExp, ast.For, ast.While, ast.Try)):
                            complexity += 1
                    results.append({
                        "name": node.name,
                        "file": str(py_file.relative_to(self.project_path)),
                        "line": node.lineno,
                        "complexity": complexity,
                        "lines": (node.end_lineno - node.lineno + 1)
                        if hasattr(node, "end_lineno") and node.end_lineno
                        else 0,
                        "params": len(node.args.args) if hasattr(node, "args") else 0,
                    })
        results.sort(key=lambda x: x["complexity"], reverse=True)
        return results

    # ── HTML rendering ─────────────────────────────────────────────────

    def generate(
        self,
        output_path: str,
        *,
        call_graph: bool = True,
        module_graph: bool = True,
        hierarchy: bool = True,
        flow_entry: Optional[str] = None,
        flow_depth: int = 5,
        include_complexity: bool = True,
    ) -> None:
        """Generate the HTML report and write to *output_path*."""
        svgs = self._collect_svgs(
            call_graph=call_graph,
            module_graph=module_graph,
            hierarchy=hierarchy,
            flow_entry=flow_entry,
            flow_depth=flow_depth,
        )
        complexity = self._compute_complexity() if include_complexity else []
        stats = self.visualizer.get_graph_stats()
        html_content = self._render_html(svgs, complexity, stats)
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(html_content, encoding="utf-8")
        print(f"HTML report generated: {output_path}")

    # ── Internal HTML template ─────────────────────────────────────────

    def _render_html(
        self,
        svgs: Dict[str, Optional[str]],
        complexity: List[Dict],
        stats: Dict[str, int],
    ) -> str:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        project_name = html.escape(self.project_path.name)

        sections: List[str] = []

        # ── Metadata section ───────────────────────────────────────────
        sections.append(self._section_metadata(project_name, now, stats))

        # ── SVG sections ───────────────────────────────────────────────
        svg_titles = {
            "call_graph": ("函数调用图 / Call Graph", "call-graph"),
            "module_graph": ("模块依赖图 / Module Graph", "module-graph"),
            "hierarchy": ("函数层级树 / Hierarchy", "hierarchy"),
            "execution_flow": ("执行流程图 / Execution Flow", "execution-flow"),
        }
        for key, (title, anchor) in svg_titles.items():
            svg_content = svgs.get(key)
            if svg_content is not None:
                sections.append(self._section_svg(title, anchor, svg_content))

        # ── Complexity table ───────────────────────────────────────────
        if complexity:
            sections.append(self._section_complexity(complexity))

        # ── Failed files ───────────────────────────────────────────────
        if self.failed_files:
            sections.append(self._section_failed_files())

        body = "\n".join(sections)
        return self._page_template(project_name, body)

    # ── Section builders ───────────────────────────────────────────────

    def _section_metadata(self, project_name: str, timestamp: str, stats: Dict[str, int]) -> str:
        modules = set()
        for fid in self.functions:
            modules.add(fid.split(":")[0])
        return f"""
<section id="metadata" class="card">
  <h2>项目概览 / Project Overview</h2>
  <table class="meta-table">
    <tr><td>项目 / Project</td><td><strong>{project_name}</strong></td></tr>
    <tr><td>生成时间 / Generated</td><td>{timestamp}</td></tr>
    <tr><td>已分析文件 / Files Analyzed</td><td>{len(self.analyzed_files)}</td></tr>
    <tr><td>解析失败 / Failed</td><td>{len(self.failed_files)}</td></tr>
    <tr><td>函数数量 / Functions</td><td>{len(self.functions)}</td></tr>
    <tr><td>类数量 / Classes</td><td>{len(self.classes)}</td></tr>
    <tr><td>模块数量 / Modules</td><td>{len(modules)}</td></tr>
    <tr><td>调用图边数 / Call Edges</td><td>{stats.get('call_graph_edges', 0)}</td></tr>
    <tr><td>模块依赖边数 / Module Edges</td><td>{stats.get('module_graph_edges', 0)}</td></tr>
  </table>
</section>"""

    @staticmethod
    def _section_svg(title: str, anchor: str, svg: str) -> str:
        return f"""
<section id="{anchor}" class="card">
  <h2>{title}</h2>
  <div class="svg-container">{svg}</div>
</section>"""

    def _section_complexity(self, complexity: List[Dict]) -> str:
        rows: List[str] = []
        for f in complexity:
            badge = "high" if f["complexity"] >= 10 else ("medium" if f["complexity"] >= 5 else "low")
            rows.append(
                f"<tr>"
                f"<td>{html.escape(f['name'])}</td>"
                f'<td><span class="badge {badge}">{f["complexity"]}</span></td>'
                f"<td>{f['lines']}</td>"
                f"<td>{f['params']}</td>"
                f"<td>{html.escape(f['file'])}:{f['line']}</td>"
                f"</tr>"
            )
        avg = (
            sum(f["complexity"] for f in complexity) / len(complexity)
            if complexity
            else 0
        )
        max_c = max((f["complexity"] for f in complexity), default=0)
        summary = (
            f"<p>共 {len(complexity)} 个函数 &middot; "
            f"平均复杂度 {avg:.1f} &middot; 最大复杂度 {max_c}</p>"
        )
        return f"""
<section id="complexity" class="card">
  <h2>代码复杂度 / Code Complexity</h2>
  {summary}
  <div class="table-wrapper">
  <table class="data-table">
    <thead>
      <tr>
        <th>函数 / Function</th>
        <th>复杂度 / Complexity</th>
        <th>行数 / Lines</th>
        <th>参数 / Params</th>
        <th>位置 / Location</th>
      </tr>
    </thead>
    <tbody>
      {"".join(rows)}
    </tbody>
  </table>
  </div>
</section>"""

    def _section_failed_files(self) -> str:
        items = "\n".join(
            f"<li><code>{html.escape(fp)}</code> — {html.escape(err)}</li>"
            for fp, err in self.failed_files
        )
        return f"""
<section id="failed" class="card">
  <h2>解析失败文件 / Failed Files</h2>
  <ul class="failed-list">{items}</ul>
</section>"""

    # ── Full-page HTML template ────────────────────────────────────────

    @staticmethod
    def _page_template(title: str, body: str) -> str:
        return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>PyCodeViz Report — {title}</title>
<style>
:root {{
  --bg: #f5f7fa;
  --card-bg: #ffffff;
  --text: #1e293b;
  --muted: #64748b;
  --accent: #3b82f6;
  --border: #e2e8f0;
  --high: #ef4444;
  --medium: #f59e0b;
  --low: #22c55e;
}}
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
  background: var(--bg);
  color: var(--text);
  line-height: 1.6;
  padding: 2rem;
}}
h1 {{
  font-size: 1.8rem;
  margin-bottom: 0.5rem;
}}
h1 small {{
  font-weight: 400;
  color: var(--muted);
  font-size: 0.9rem;
}}
h2 {{
  font-size: 1.3rem;
  margin-bottom: 1rem;
  padding-bottom: 0.5rem;
  border-bottom: 2px solid var(--accent);
}}
.container {{
  max-width: 1200px;
  margin: 0 auto;
}}
nav {{
  margin-bottom: 2rem;
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}}
nav a {{
  text-decoration: none;
  color: var(--accent);
  padding: 0.3rem 0.8rem;
  border: 1px solid var(--accent);
  border-radius: 6px;
  font-size: 0.85rem;
  transition: background 0.2s, color 0.2s;
}}
nav a:hover {{
  background: var(--accent);
  color: #fff;
}}
.card {{
  background: var(--card-bg);
  border-radius: 12px;
  padding: 1.5rem;
  margin-bottom: 1.5rem;
  box-shadow: 0 1px 3px rgba(0,0,0,0.08);
}}
.meta-table {{
  border-collapse: collapse;
  width: 100%;
  max-width: 500px;
}}
.meta-table td {{
  padding: 0.4rem 1rem 0.4rem 0;
  border-bottom: 1px solid var(--border);
}}
.meta-table td:first-child {{
  color: var(--muted);
  white-space: nowrap;
}}
.svg-container {{
  overflow-x: auto;
  text-align: center;
}}
.svg-container svg {{
  max-width: 100%;
  height: auto;
}}
.table-wrapper {{
  overflow-x: auto;
}}
.data-table {{
  border-collapse: collapse;
  width: 100%;
  font-size: 0.9rem;
}}
.data-table th, .data-table td {{
  text-align: left;
  padding: 0.5rem 0.75rem;
  border-bottom: 1px solid var(--border);
}}
.data-table thead th {{
  background: var(--bg);
  position: sticky;
  top: 0;
}}
.badge {{
  display: inline-block;
  padding: 0.15rem 0.5rem;
  border-radius: 9999px;
  font-size: 0.8rem;
  font-weight: 600;
  color: #fff;
}}
.badge.high   {{ background: var(--high); }}
.badge.medium {{ background: var(--medium); }}
.badge.low    {{ background: var(--low); }}
.failed-list {{
  list-style: none;
  padding: 0;
}}
.failed-list li {{
  padding: 0.4rem 0;
  border-bottom: 1px solid var(--border);
}}
.failed-list code {{
  color: var(--high);
}}
footer {{
  text-align: center;
  color: var(--muted);
  font-size: 0.8rem;
  margin-top: 2rem;
}}
</style>
</head>
<body>
<div class="container">
  <h1>PyCodeViz Report <small>{title}</small></h1>
  <nav>
    <a href="#metadata">概览 / Overview</a>
    <a href="#call-graph">调用图 / Call Graph</a>
    <a href="#module-graph">模块图 / Module Graph</a>
    <a href="#hierarchy">层级树 / Hierarchy</a>
    <a href="#complexity">复杂度 / Complexity</a>
  </nav>
  {body}
  <footer>Generated by <strong>PyCodeViz</strong></footer>
</div>
</body>
</html>"""
