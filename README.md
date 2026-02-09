# PyCodeViz

PyCodeViz 是一个强大的Python项目代码分析和可视化工具，帮助你理解代码结构和执行流程。

## 功能特性

- **函数调用图** - 可视化所有函数之间的调用关系
- **模块依赖图** - 显示模块间的依赖关系
- **函数层级树** - 按模块组织的函数结构
- **执行流程图** - 从指定入口点生成调用流程树
- **代码分析** - 使用AST解析，提取类、函数、参数信息
- **代码复杂度分析** - 生成函数级别的圈复杂度报告
- **HTML 报告** - 生成嵌入 SVG 图表和元数据的自包含 HTML 报告
- **文件过滤** - 通过 `--exclude` / `--include` 灵活选择分析范围
- **多格式输出** - 支持 SVG、PNG、PDF 输出格式
- **图规模预览** - 生成前提示节点/边数量
- **详细日志** - 通过 `--verbose` 查看解析失败的详细原因
- **环境检测** - Graphviz 未安装时给出友好提示和安装建议

## 前置条件

PyCodeViz 依赖 [Graphviz](https://graphviz.org/) 进行图形渲染，请先安装：

```bash
# macOS
brew install graphviz

# Ubuntu / Debian
sudo apt-get install graphviz

# Fedora
sudo dnf install graphviz

# Arch Linux
sudo pacman -S graphviz

# Windows
choco install graphviz
# 或从 https://graphviz.org/download/ 下载安装
```

安装后确保 `dot` 命令在 PATH 中可用。如果未安装 Graphviz，PyCodeViz 会自动检测并给出对应平台的安装建议。

## 使用方法

### 基本命令

```bash
# 生成所有可视化
uv run pycodeviz examples --all

# 仅生成函数调用图
uv run pycodeviz examples --call-graph

# 生成模块依赖图
uv run pycodeviz examples --module-graph

# 生成函数层级树
uv run pycodeviz examples --hierarchy

# 生成从特定函数出发的执行流程
uv run pycodeviz examples --flow mymodule:main
# 指定流程深度
uv run pycodeviz examples --flow mymodule:main --depth 10

#生成代码复杂度分析报告
uv run pycodeviz examples --complexity

# 生成 HTML 报告（默认输出 report.html）
uv run pycodeviz examples --report

# 生成 HTML 报告到指定文件名
uv run pycodeviz examples --report my_report.html

# 指定输出目录
uv run pycodeviz examples --all --output-dir ./visualizations
```

### 输出格式

通过 `--format` 指定输出格式，支持 `svg`（默认）、`png`、`pdf`：

```bash
# 输出为 PNG 格式
uv run pycodeviz examples --all --format png

# 输出为 PDF 格式
uv run pycodeviz examples --all --format pdf
```

### 文件过滤

使用 `--exclude` 和 `--include` 过滤要分析的文件或模块（支持 glob 通配符）：

```bash
# 排除测试文件
uv run pycodeviz . --all --exclude 'test_*' '*_test.py'

# 只分析特定模块
uv run pycodeviz . --all --include 'core*' 'utils*'

# 排除多个目录下的文件
uv run pycodeviz . --all --exclude 'tests/*' 'docs/*'
```

**规则说明：**
- `--include`：仅分析匹配的文件（白名单模式）
- `--exclude`：跳过匹配的文件（黑名单模式）
- 模式会同时匹配文件名、相对路径和模块名

### 详细日志

使用 `--verbose` 查看解析过程中失败文件的详细错误信息：

```bash
uv run pycodeviz . --all --verbose
```

默认情况下，解析失败的文件仅列出路径；加上 `--verbose` 后会显示具体的错误原因（如语法错误行号、编码问题等）。

### HTML 报告

通过 `--report` 生成一份自包含的 HTML 报告，报告中嵌入了所有 SVG 可视化图表和项目元数据：

```bash
# 生成默认的 report.html
uv run pycodeviz . --report

# 指定输出文件名
uv run pycodeviz . --report analysis.html

# 结合输出目录
uv run pycodeviz . --report --output-dir ./reports
```

报告包含：
- **项目概览** — 分析文件数、函数/类/模块数量、图规模等元数据
- **函数调用图** — 嵌入的 SVG 交互图
- **模块依赖图** — 嵌入的 SVG 交互图
- **函数层级树** — 嵌入的 SVG 交互图
- **代码复杂度表** — 按复杂度排序的函数列表，带颜色标签
- **失败文件列表** — 解析失败的文件及错误原因

### 图规模预览

执行可视化之前，PyCodeViz 会自动输出分析摘要和图规模预览：

```
Analysis summary:
  Files analyzed : 5
  Files failed   : 1
  Functions found: 42
  Classes found  : 8

Graph scale preview (output format: svg):
  Call graph     : 42 nodes, 15 edges
  Module graph   : 5 nodes, 8 edges
  Hierarchy      : 42 nodes
```
