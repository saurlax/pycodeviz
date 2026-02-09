# PyCodeViz

PyCodeViz 是一个强大的Python项目代码分析和可视化工具，帮助你理解代码结构和执行流程。

## 功能特性

- **函数调用图** - 可视化所有函数之间的调用关系
- **模块依赖图** - 显示模块间的依赖关系
- **函数层级树** - 按模块组织的函数结构
- **执行流程图** - 从指定入口点生成调用流程树
- **代码分析** - 使用AST解析，提取类、函数、参数信息

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

# 指定输出目录
uv run pycodeviz examples --all --output-dir ./visualizations
```
