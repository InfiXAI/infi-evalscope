# EvalScope Viewer 用户操作指南

本文档介绍如何使用 EvalScope Viewer 进行模型评测结果的可视化。

---

## 环境要求

| 依赖 | 版本要求 | 说明 |
|------|---------|------|
| Python | 3.8+ | 运行 EvalScope 和 API 服务 |
| Node.js | 18+ | 运行前端服务（使用 `--with-web` 时需要） |
| npm | 8+ | 安装前端依赖（随 Node.js 一起安装） |

检查环境：

```bash
python --version   # Python 3.8+
node --version     # v18.0.0+
npm --version      # 8.0.0+
```

> 如果没有 Node.js，请访问 https://nodejs.org/ 下载 LTS 版本。

---

## 快速开始（30 秒上手）

```bash
# 1. 安装依赖
pip install -e '.[viewer]'

# 2. 运行评测（API 方式）
evalscope eval \
    --model Qwen2.5-3B-Instruct \
    --api-url http://192.168.1.250:30000/v1 \
    --api-key EMPTY \
    --eval-type openai_api \
    --datasets gsm8k \
    --limit 10 \
    --eval-batch-size 8

# 3. 启动可视化
evalscope-viewer serve --outputs-dir ./outputs --with-web

# 4. 打开浏览器访问
# http://localhost:3000
```

---

## 完整操作流程

### 第一步：安装依赖

```bash
# 安装 evalscope 和 viewer 依赖
pip install -e '.[viewer]'
```

> 确保已满足上方"环境要求"中的 Python、Node.js、npm 版本要求。

---

### 第二步：运行模型评测

#### 方式一：API 服务评测（推荐）

通过 OpenAI 兼容接口评测已部署的模型服务：

```bash
evalscope eval \
    --model Qwen2.5-3B-Instruct \
    --api-url http://192.168.1.250:30000/v1 \
    --api-key EMPTY \
    --eval-type openai_api \
    --datasets gsm8k arc \
    --limit 50 \
    --eval-batch-size 8
```

#### 方式二：本地模型评测

直接加载本地模型进行评测：

```bash
evalscope eval \
    --model Qwen/Qwen2.5-0.5B-Instruct \
    --datasets gsm8k arc \
    --limit 50
```

#### 方式三：Python 代码

```python
from evalscope import run_task, TaskConfig

run_task(TaskConfig(
    model='Qwen2.5-3B-Instruct',
    api_url='http://192.168.1.250:30000/v1',
    api_key='EMPTY',
    eval_type='openai_api',
    datasets=['gsm8k', 'arc'],
    limit=50,
    eval_batch_size=8
))
```

**评测完成后**，结果会保存在 `outputs/` 目录：

```
outputs/
└── 20251204_143025/          # 时间戳命名的运行目录
    ├── configs/              # 配置文件
    ├── predictions/          # 模型预测结果
    ├── reviews/              # 评分结果
    └── reports/              # 汇总报告
```

---

### 第三步：启动可视化服务

```bash
# 一键启动（API + 前端）
evalscope-viewer serve --outputs-dir ./outputs --with-web
```

这个命令会自动完成：
1. ✅ 扫描 `outputs/` 目录中的所有评测结果
2. ✅ 同步数据到 `.viewer/` 缓存目录（DuckDB + Parquet）
3. ✅ 启动 API 服务（默认端口 7862）
4. ✅ **自动安装前端依赖**（首次启动时执行 `npm install`）
5. ✅ 启动前端服务（默认端口 3000）

> **首次启动说明**：第一次使用 `--with-web` 时，系统会自动在 `evalscope/viewer/web/` 目录下执行 `npm install` 安装前端依赖，这可能需要 1-2 分钟，请耐心等待。

启动成功后，访问 **http://localhost:3000** 即可查看结果。

---

## CLI 命令参考

### serve - 启动服务

```bash
# 完整启动（API + 前端）
evalscope-viewer serve --outputs-dir ./outputs --with-web

# 只启动 API（不启动前端）
evalscope-viewer serve --outputs-dir ./outputs

# 自定义端口
evalscope-viewer serve --outputs-dir ./outputs --with-web \
  --port 8000 --frontend-port 3001

# 绑定到所有网卡（允许外部访问）
evalscope-viewer serve --outputs-dir ./outputs --with-web --host 0.0.0.0
```

**参数说明：**

| 参数 | 默认值 | 说明 |
|-----|--------|-----|
| `--outputs-dir` | `./outputs` | EvalScope 评测输出目录 |
| `--data-dir` | `.viewer` | Viewer 缓存目录 |
| `--mode` | `single` | 存储模式：`single`（单人）或 `team`（团队） |
| `--host` | `127.0.0.1` | API 服务绑定地址 |
| `--port` | `7862` | API 服务端口 |
| `--with-web` | - | 同时启动前端服务 |
| `--frontend-port` | `3000` | 前端服务端口 |

### sync - 同步数据

手动同步 outputs 目录到缓存：

```bash
evalscope-viewer sync --outputs-dir ./outputs
```

### list - 列出运行

```bash
# 列出所有已缓存的运行
evalscope-viewer list --outputs-dir ./outputs

# 限制显示数量
evalscope-viewer list --outputs-dir ./outputs --limit 10
```

### delete - 删除运行

```bash
# 删除指定运行（会提示确认）
evalscope-viewer delete 20251204_143025 --outputs-dir ./outputs

# 强制删除（跳过确认）
evalscope-viewer delete 20251204_143025 --outputs-dir ./outputs -f
```

---

## Web 界面功能

访问 http://localhost:3000 后，你可以：

### 首页 - 运行列表
- 查看所有评测运行
- 按模型名、时间、分数筛选
- 快速预览每次评测的总体得分

### 运行详情页
- 查看评测配置信息
- 查看各数据集的分数分布
- 交互式图表展示评测指标

### 样本浏览页
- 逐条查看模型的输入/输出/评分
- 筛选正确/错误样本
- 分析模型的具体表现

---

## 数据存储说明

Viewer 使用 **DuckDB + Parquet** 进行数据存储：

```
.viewer/                      # 缓存目录（可通过 --data-dir 自定义）
├── viewer.duckdb            # DuckDB 数据库（索引和视图）
└── cache/                   # Parquet 缓存文件
    ├── runs.parquet         # 所有运行的元数据
    └── samples/             # 样本数据
        └── {run_id}/
            └── {dataset}.parquet
```

> 注意：`.viewer/` 目录是自动生成的缓存，建议添加到 `.gitignore`。

---

## 典型使用场景

### 场景一：快速查看单次评测结果

```bash
# 运行评测
evalscope eval \
    --model Qwen2.5-3B-Instruct \
    --api-url http://192.168.1.250:30000/v1 \
    --api-key EMPTY \
    --eval-type openai_api \
    --datasets gsm8k \
    --limit 20 \
    --eval-batch-size 8

# 立即可视化
evalscope-viewer serve --outputs-dir ./outputs --with-web
```

### 场景二：对比多个模型的评测结果

```bash
# 评测模型 A（3B）
evalscope eval \
    --model Qwen2.5-3B-Instruct \
    --api-url http://192.168.1.250:30000/v1 \
    --api-key EMPTY \
    --eval-type openai_api \
    --datasets gsm8k arc \
    --eval-batch-size 8

# 评测模型 B（7B）
evalscope eval \
    --model Qwen2.5-7B-Instruct \
    --api-url http://192.168.1.250:30001/v1 \
    --api-key EMPTY \
    --eval-type openai_api \
    --datasets gsm8k arc \
    --eval-batch-size 8

# 启动可视化，所有运行都会自动显示
evalscope-viewer serve --outputs-dir ./outputs --with-web
```

### 场景三：团队共享评测结果

```bash
# 部署到服务器，允许外部访问
evalscope-viewer serve \
  --outputs-dir ./outputs \
  --host 0.0.0.0 \
  --with-web

# 团队成员可以通过 http://<server-ip>:3000 访问
```

---

## 常见问题

### Q: 前端启动失败？

1. **检查 Node.js 环境**：
   ```bash
   node --version   # 需要 v18.0.0+
   npm --version    # 需要 8.0.0+
   ```

2. **首次启动较慢是正常的**：系统会自动在 `evalscope/viewer/web/` 目录执行 `npm install`

3. **手动安装前端依赖**（如果自动安装失败）：
   ```bash
   cd evalscope/viewer/web
   npm install
   ```

4. **常见错误及解决方法**：
   - `npm not found`：请安装 Node.js，访问 https://nodejs.org/
   - `EACCES permission denied`：尝试使用 `sudo npm install` 或修复 npm 权限
   - 网络问题：尝试使用国内镜像 `npm config set registry https://registry.npmmirror.com`

### Q: 数据没有显示？

1. 确保 `outputs/` 目录存在且包含评测结果
2. 检查评测是否成功完成（目录中应有 `reports/` 文件夹）
3. 尝试手动同步：`evalscope-viewer sync --outputs-dir ./outputs`

### Q: 如何更新已有的评测数据？

Viewer 会在每次启动时自动同步 outputs 目录。如需手动同步：

```bash
evalscope-viewer sync --outputs-dir ./outputs
```

### Q: 缓存数据存储在哪里？

默认在当前目录的 `.viewer/` 文件夹中，可通过 `--data-dir` 参数自定义：

```bash
evalscope-viewer serve --outputs-dir ./outputs --data-dir /path/to/cache
```

---

## 端口说明

| 服务 | 默认端口 | 自定义参数 |
|------|---------|-----------|
| API Server | 7862 | `--port` |
| Frontend | 3000 | `--frontend-port` |

---

## 下一步

- 查看 [架构设计](./viewer-architecture.md) 了解技术细节
- 查看 [数据设计](./viewer-data-design.md) 了解数据模型
- 查看 [REST API 文档](../evalscope/viewer/README.md) 进行自定义集成
