# EvalScope Viewer 架构设计

## 概述

EvalScope Viewer 使用 DuckDB + Parquet 数据湖方案，支持两种运行模式：

| 模式 | 说明 | 适用场景 |
|------|------|---------|
| `single` | 单人模式 | 本地开发、个人使用 |
| `team` | 团队模式 | 团队协作、服务器部署 |

## 架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                      EvalScope 评测                              │
│  evalscope eval --model xxx --datasets gsm8k                    │
│                           │                                      │
│                           ▼                                      │
│                 outputs/20241204_xxx/                            │
│                 (JSON/JSONL 原始输出)                            │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Viewer 服务                                 │
│                                                                  │
│   ┌──────────────────┐          ┌──────────────────┐            │
│   │   单人模式        │          │   团队模式        │            │
│   │   mode=single    │          │   mode=team      │            │
│   │                  │          │                  │            │
│   │  • 无用户管理     │          │  • 用户认证       │            │
│   │  • 扫描本地目录   │          │  • 权限控制       │            │
│   │  • 零配置启动     │          │  • 上传管理       │            │
│   └────────┬─────────┘          └────────┬─────────┘            │
│            │                             │                       │
│            └──────────┬──────────────────┘                       │
│                       ▼                                          │
│            ┌──────────────────────┐                             │
│            │  DuckDB + Parquet    │                             │
│            │  统一存储引擎         │                             │
│            └──────────────────────┘                             │
└─────────────────────────────────────────────────────────────────┘
```

## 单人模式 (single)

### 特点
- 无用户认证，所有数据可见
- 自动扫描 outputs 目录
- 零配置启动

### 使用方式

```bash
# 启动服务（自动扫描 outputs）
evalscope-viewer serve --mode single --outputs-dir ./outputs

# 手动同步缓存
evalscope-viewer sync --outputs-dir ./outputs

# 列出所有 runs
evalscope-viewer list
```

### 存储结构

```
project/
├── outputs/                  # EvalScope 原始输出（只读）
│   ├── 20241204_100000/
│   └── 20241204_110000/
└── .viewer/                  # Viewer 数据目录
    ├── viewer.duckdb         # DuckDB（视图定义 + 缓存索引）
    └── cache/                # Parquet 缓存
        ├── runs.parquet
        └── samples/{run_id}/*.parquet
```

## 团队模式 (team)

### 特点
- 用户认证（注册/登录）
- 数据按用户隔离
- 支持上传评测结果

### 使用方式

```bash
# 管理员：初始化
evalscope-viewer init --mode team \
  --data-dir /data/viewer \
  --admin-user admin \
  --admin-password xxx

# 管理员：启动服务
evalscope-viewer serve --mode team --data-dir /data/viewer

# 管理员：用户管理
evalscope-viewer user create --username alice
evalscope-viewer user list

# 用户：上传评测结果
evalscope-viewer upload \
  --api-url http://server:7862 \
  --username alice \
  --outputs-dir ./outputs
```

### 存储结构

```
/data/viewer/
├── viewer.duckdb             # DuckDB 数据库
│   ├── [表] users            # 用户信息
│   ├── [表] run_ownership    # Run 归属关系
│   └── [视图] runs_data      # 指向 Parquet
└── cache/                    # Parquet 数据
    ├── runs.parquet
    └── samples/{run_id}/*.parquet
```

## 技术选型

| 组件 | 技术 | 说明 |
|------|------|------|
| 查询引擎 | DuckDB | 高性能分析查询，支持直接读取 Parquet |
| 数据存储 | Parquet | 列式压缩，适合大规模评测数据 |
| 用户管理 | DuckDB 原生表 | 支持 ACID 事务，满足更新需求 |
| API | FastAPI | 高性能 Python Web 框架 |
| 前端 | Next.js | React 框架 |

## 数据流

```
单人模式：
  outputs/*.jsonl ──► Viewer 启动时扫描 ──► 生成 Parquet 缓存 ──► DuckDB 查询

团队模式：
  用户上传 ──► API 接收 ──► 生成 Parquet ──► 注册归属 ──► DuckDB 查询（带权限过滤）
```
