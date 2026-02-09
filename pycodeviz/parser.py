import ast
import os
from pathlib import Path
from typing import Dict, Set, List, Tuple
from dataclasses import dataclass, field


@dataclass
class FunctionInfo:
    """Function metadata"""
    name: str
    module: str
    lineno: int 
    calls: Set[str] = field(default_factory=set)
    called_by: Set[str] = field(default_factory=set)
    args: List[str] = field(default_factory=list)


@dataclass
class ClassInfo:
    """Class metadata"""
    name: str
    module: str
    lineno: int
    methods: Dict[str, FunctionInfo] = field(default_factory=dict)
    bases: List[str] = field(default_factory=list)


class CodeAnalyzer(ast.NodeVisitor):
    
    """AST visitor to extract code structure and call relationships"""

    def __init__(self, module_name: str):
        self.module_name = module_name
        self.functions: Dict[str, FunctionInfo] = {}
        self.classes: Dict[str, ClassInfo] = {}
        self.current_scope: str = ""
        self.current_function: str = ""

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        func_id = f"{self.module_name}:{self.current_scope}.{node.name}" if self.current_scope else f"{self.module_name}:{node.name}"
        
        func_info = FunctionInfo(
            name=node.name,
            module=self.module_name,
            lineno=node.lineno,
            args=[arg.arg for arg in node.args.args]
        )
        
        self.functions[func_id] = func_info
        
        prev_function = self.current_function
        self.current_function = func_id
        self.generic_visit(node)
        self.current_function = prev_function

    def visit_ExceptHandler(self, node):
     """Detect dangerous empty 'except:' blocks"""
     if len(node.body) == 0:
        print(f"\033[91m[SECURITY] Empty except at line {node.lineno}\033[0m")
     elif len(node.body) == 1 and isinstance(node.body[0], ast.Pass):
        print(f"\033[91m[SECURITY] 'except: pass' at line {node.lineno} (swallows all errors!)\033[0m")
     self.generic_visit(node)


    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self.visit_FunctionDef(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        class_id = f"{self.module_name}:{node.name}"
        base_names = [self._get_name(base) for base in node.bases]
        
        class_info = ClassInfo(
            name=node.name,
            module=self.module_name,
            lineno=node.lineno,
            bases=base_names
        )
        
        self.classes[class_id] = class_info
        
        prev_scope = self.current_scope
        self.current_scope = f"{self.current_scope}.{node.name}" if self.current_scope else node.name
        
        self.generic_visit(node)
        
        self.current_scope = prev_scope

    def visit_Call(self, node: ast.Call) -> None:
        if self.current_function:
            call_name = self._get_call_name(node.func)
            if call_name:
                current_func = self.functions.get(self.current_function)
                if current_func:
                    current_func.calls.add(call_name)
        
        self.generic_visit(node)

    def _get_call_name(self, node: ast.expr) -> str:
        """Extract function name from call node"""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            parts = []
            current = node
            while isinstance(current, ast.Attribute):
                parts.append(current.attr)
                current = current.value
            if isinstance(current, ast.Name):
                parts.append(current.id)
                return ".".join(reversed(parts))
        return ""

    def _get_name(self, node: ast.expr) -> str:
        """Extract name from various node types"""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return f"{self._get_name(node.value)}.{node.attr}"
        return ""



class ProjectAnalyzer:
    """Analyze entire Python project"""

    def __init__(self, project_path: str):
        self.project_path = Path(project_path)
        self.all_functions: Dict[str, FunctionInfo] = {}
        self.all_classes: Dict[str, ClassInfo] = {}

    def analyze(self) -> Tuple[Dict[str, FunctionInfo], Dict[str, ClassInfo]]:
        """Analyze all Python files in project"""
        for py_file in self.project_path.rglob("*.py"):
            if self._should_skip(py_file):
                continue
            
            self._analyze_file(py_file)
        
        # Resolve call relationships
        self._resolve_calls()
        
        return self.all_functions, self.all_classes

    def _analyze_file(self, file_path: Path) -> None:
        """Analyze single Python file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content)
            module_name = self._get_module_name(file_path)
            analyzer = CodeAnalyzer(module_name)
            analyzer.visit(tree)
            
            self.all_functions.update(analyzer.functions)
            self.all_classes.update(analyzer.classes)
        except Exception as e:
            print(f"Error analyzing {file_path}: {e}")

    def _get_module_name(self, file_path: Path) -> str:
        """Get module name from file path"""
        relative = file_path.relative_to(self.project_path)
        return str(relative.with_suffix("")).replace(os.sep, ".")

    def _should_skip(self, file_path: Path) -> bool:
        """Check if file should be skipped"""
        skip_dirs = {".venv", ".git", "__pycache__", ".pytest_cache", "venv", "env"}
        parts = file_path.parts
        return any(part in skip_dirs for part in parts)

    def _resolve_calls(self) -> None:
        """Resolve and record call relationships"""
        for func_id, func_info in self.all_functions.items():
            for call_name in func_info.calls.copy():
                # Try to resolve call to full identifier
                resolved = self._resolve_call_target(func_id, call_name)
                if resolved:
                    func_info.calls.discard(call_name)
                    func_info.calls.add(resolved)
                    if resolved in self.all_functions:
                        self.all_functions[resolved].called_by.add(func_id)

    def _resolve_call_target(self, caller_id: str, call_name: str) -> str:
        """Resolve function call to target identifier"""
        caller_module = caller_id.split(":")[0]
        
        # Check same module
        for func_id in self.all_functions:
            func_module, func_path = func_id.split(":")
            func_local_name = func_path.split(".")[-1]
            if func_module == caller_module and func_local_name == call_name:
                return func_id
        
        # Check with full module prefix
        for func_id in self.all_functions:
            func_module, func_path = func_id.split(":")
            if call_name.startswith(func_module):
                return func_id
        
        return call_name
