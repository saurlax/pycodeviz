import os
import sys
import ast
import argparse
import fnmatch
import subprocess
import tempfile
from pathlib import Path
from collections import defaultdict
import logging


logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


class ClassInfo:
    def __init__(self, name, fullname, module, bases, lineno):
        self.name = name                
        self.fullname = fullname        
        self.module = module            
        self.bases = bases              
        self.lineno = lineno            


class ModuleInfo:
    def __init__(self, name, filepath):
        self.name = name                
        self.filepath = filepath        
        self.classes = {}               
        self.imports = {}               


class ClassGraphGenerator:
    def __init__(self, root_dir, exclude_patterns=None, verbose=False):
        self.root_dir = Path(root_dir).resolve()
        self.exclude_patterns = exclude_patterns or []
        self.verbose = verbose
        if verbose:
            logger.setLevel(logging.DEBUG)

        self.modules = []                 
        self.class_map = {}               
        self.global_imports = {}          

    def should_exclude(self, filepath):
        rel_path = str(filepath.relative_to(self.root_dir))
        for pat in self.exclude_patterns:
            if fnmatch.fnmatch(rel_path, pat) or fnmatch.fnmatch(filepath.name, pat):
                return True
        return False

    def parse_module(self, filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            logger.warning(f"无法读取文件 {filepath}: {e}")
            return None

        try:
            tree = ast.parse(content, filename=str(filepath))
        except SyntaxError as e:
            logger.warning(f"语法错误 {filepath}:{e.lineno}: {e.msg}")
            return None

        rel_path = filepath.relative_to(self.root_dir)
        if rel_path.name == '__init__.py':
            module_name = str(rel_path.parent).replace(os.sep, '.')
        else:
            module_name = str(rel_path.with_suffix('')).replace(os.sep, '.')

        mod = ModuleInfo(module_name, str(filepath))

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    asname = alias.asname or alias.name
                    mod.imports[asname] = alias.name  # import module
            elif isinstance(node, ast.ImportFrom):
                if node.module is None:  # from . import ...
                    level = node.level
                    parts = module_name.split('.')
                    if level <= len(parts):
                        base = '.'.join(parts[:-level] if level > 0 else parts)
                    else:
                        base = ''
                    module = base + ('.' + node.module if node.module else '')
                else:
                    module = node.module

                for alias in node.names:
                    asname = alias.asname or alias.name
                    mod.imports[asname] = f"{module}.{alias.name}"

        class_collector = ClassCollector(mod, module_name)
        class_collector.visit(tree)

        for cls in class_collector.classes:
            mod.classes[cls.name] = cls

        return mod

    def resolve_base(self, base_name, current_module):
        if '.' in base_name:
            return base_name

        if base_name in current_module.imports:
            return current_module.imports[base_name]

        if base_name in current_module.classes:
            return current_module.classes[base_name].fullname

        return base_name  

    def analyze(self):
        logger.info(f"分析目录: {self.root_dir}")

        # 收集所有 Python 文件
        py_files = list(self.root_dir.rglob('*.py'))
        logger.info(f"找到 {len(py_files)} 个 Python 文件")

        # 解析每个模块
        for filepath in py_files:
            if self.should_exclude(filepath):
                logger.debug(f"排除文件: {filepath}")
                continue
            mod = self.parse_module(filepath)
            if mod:
                self.modules.append(mod)

        logger.info(f"成功解析 {len(self.modules)} 个模块")

        for mod in self.modules:
            for cls in mod.classes.values():
                self.class_map[cls.fullname] = cls


        for mod in self.modules:
            for cls in mod.classes.values():
                resolved_bases = []
                for base in cls.bases:
                    resolved = self.resolve_base(base, mod)
                    resolved_bases.append(resolved)
                cls.bases = resolved_bases  

        total_classes = len(self.class_map)
        total_edges = sum(len(cls.bases) for cls in self.class_map.values())
        logger.info(f"找到 {total_classes} 个类，{total_edges} 条继承关系")

    def generate_dot_source(self):
        lines = ['digraph class_inheritance {', '  rankdir=BT;', '  node [shape=record];']

        for cls in self.class_map.values():
            label = f"{{ {cls.name} | {cls.module} }}"
            lines.append(f'  "{cls.fullname}" [label="{label}"];')

        for cls in self.class_map.values():
            for base in cls.bases:
                if base in self.class_map:
                    lines.append(f'  "{cls.fullname}" -> "{base}";')
                else:
                    logger.debug(f"忽略外部基类 {base} (来自 {cls.fullname})")

        lines.append('}')
        return '\n'.join(lines)

    def render(self, output_path, format=None):
        if format is None:
            ext = Path(output_path).suffix.lower().lstrip('.')
            if ext in ('svg', 'png', 'pdf'):
                format = ext
            else:
                format = 'svg'

        dot_source = self.generate_dot_source()

        with tempfile.NamedTemporaryFile(mode='w', suffix='.dot', delete=False) as f:
            f.write(dot_source)
            dot_file = f.name

        try:
            output_file = str(output_path)
            if not output_file.endswith(f'.{format}'):
                output_file = f"{output_file}.{format}"
            cmd = ['dot', '-T' + format, dot_file, '-o', output_file]
            subprocess.run(cmd, check=True, capture_output=True)
            logger.info(f"图形已保存到 {output_file} (格式: {format})")
        except subprocess.CalledProcessError as e:
            logger.error(f"dot 命令执行失败: {e.stderr.decode()}")
        except FileNotFoundError:
            logger.error("未找到 dot 命令，请确保 Graphviz 已安装且 dot 在 PATH 中。")
        finally:
            os.unlink(dot_file)


class ClassCollector(ast.NodeVisitor):
    def __init__(self, module_info, module_name):
        self.module_info = module_info
        self.module_name = module_name
        self.classes = []

    def visit_ClassDef(self, node):
        bases = []
        for base in node.bases:
            if isinstance(base, ast.Name):
                bases.append(base.id)
            elif isinstance(base, ast.Attribute):
                # 构建属性链，例如 module.Class
                parts = []
                x = base
                while isinstance(x, ast.Attribute):
                    parts.append(x.attr)
                    x = x.value
                if isinstance(x, ast.Name):
                    parts.append(x.id)
                else:
                    parts.append('<complex>')
                bases.append('.'.join(reversed(parts)))
            else:
                # 忽略复杂的基类表达式
                logger.debug(f"忽略复杂基类表达式: {ast.dump(base)} 在类 {node.name} 中")
                bases.append('<complex>')

        fullname = f"{self.module_name}.{node.name}"
        cls_info = ClassInfo(node.name, fullname, self.module_name, bases, node.lineno)
        self.classes.append(cls_info)

        # 继续遍历内部类（如果有）
        self.generic_visit(node)


def main():
    parser = argparse.ArgumentParser(description="生成 Python 项目的类继承图")
    parser.add_argument('directory', help="要分析的根目录")
    parser.add_argument('-o', '--output', default='class_inheritance.svg', help="输出文件路径 (默认: class_inheritance.svg)")
    parser.add_argument('-f', '--format', choices=['svg', 'png', 'pdf'], help="输出格式 (默认从文件扩展名推断)")
    parser.add_argument('-e', '--exclude', action='append', default=[], help="排除匹配的文件模式 (可多次使用，支持 glob)")
    parser.add_argument('--verbose', action='store_true', help="显示详细日志")
    args = parser.parse_args()

    if not os.path.isdir(args.directory):
        print(f"错误: 目录 '{args.directory}' 不存在")
        sys.exit(1)

    generator = ClassGraphGenerator(args.directory, args.exclude, args.verbose)
    generator.analyze()
    generator.render(args.output, args.format)


if __name__ == '__main__':
    main()