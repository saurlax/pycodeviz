# complexity_analyzer.py
import ast
from pathlib import Path
from typing import List, Dict


class ComplexityAnalyzer:
    def analyze(self, project_path: Path, output_path: Path) -> None:
        """Analyze code complexity of project"""
        functions = []
        
        for py_file in project_path.rglob("*.py"):
            if self._should_skip(py_file):
                continue
            
            functions.extend(self._analyze_file(py_file, project_path))
        
        if functions:
            self._generate_report(functions, output_path)
    
    def _should_skip(self, file_path: Path) -> bool:
        skip_dirs = {".venv", ".git", "__pycache__", ".pytest_cache", "venv", "env"}
        return any(part in skip_dirs for part in file_path.parts)
    
    def _analyze_file(self, file_path: Path, project_root: Path) -> List[Dict]:
        """Analyze single file"""
        results = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                tree = ast.parse(f.read())
            
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    results.append(self._analyze_function(node, file_path, project_root))
        
        except Exception:
            pass
        
        return results
    
    def _analyze_function(self, node: ast.AST, file_path: Path, project_root: Path) -> Dict:
        """Analyze single function"""
        # Calculate complexity
        complexity = 1
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.IfExp, ast.For, ast.While, ast.Try)):
                complexity += 1
        
        return {
            'name': node.name,
            'file': str(file_path.relative_to(project_root)),
            'line': node.lineno,
            'complexity': complexity,
            'lines': node.end_lineno - node.lineno + 1 if hasattr(node, 'end_lineno') else 0,
            'params': len(node.args.args) if hasattr(node, 'args') else 0,
        }
    
    def _generate_report(self, functions: List[Dict], output_path: Path) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            # Title
            f.write("Code Complexity Analysis\n\n")
            
            # Header
            f.write(f"{'Function':<25} {'Complexity':<12} {'Lines':<8} {'Params':<8} {'Location'}\n")
            f.write("-" * 70 + "\n")
            
            # Sort by complexity
            for func in sorted(functions, key=lambda x: x['complexity'], reverse=True):
                f.write(
                    f"{func['name']:<25} "
                    f"{func['complexity']:<12} "
                    f"{func['lines']:<8} "
                    f"{func['params']:<8} "
                    f"{func['file']}:{func['line']}\n"
                )
            
            # Statistics
            f.write("-" * 70 + "\n")
            f.write(f"Total Functions: {len(functions)}\n")
            if functions:
                avg = sum(func['complexity'] for func in functions) / len(functions)
                f.write(f"Average Complexity: {avg:.1f}\n")
                f.write(f"Max Complexity: {max(func['complexity'] for func in functions)}\n")