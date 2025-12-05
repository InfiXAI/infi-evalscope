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
│   │  • 无认证        │          │  • Access Key    │            │
│   │  • 扫描本地目录   │          │  • 按 Key 隔离    │            │
│   │  • 零配置启动     │          │  • 远程上传       │            │
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
- Access Key 认证（无需用户名密码）
- 数据按 Key 隔离
- 支持远程上传评测结果
- 服务器集中部署

### 部署架构

```
┌─────────────────────────────────────────────────────────────────┐
│                         服务器                                   │
│                                                                  │
│   evalscope-viewer serve --mode team --host 0.0.0.0             │
│                                                                  │
│              ┌──────────────────┐                               │
│              │   API Server     │◄──── 接收上传、提供查询         │
│              │   :7862          │                                │
│              └──────────────────┘                               │
│              ┌──────────────────┐                               │
│              │   Frontend       │◄──── Web 界面                  │
│              │   :3000          │                                │
│              └──────────────────┘                               │
│              ┌──────────────────┐                               │
│              │  /data/viewer/   │◄──── 数据存储                  │
│              └──────────────────┘                               │
└─────────────────────────────────────────────────────────────────┘
                           ▲
                           │ HTTP (上传/查询)
┌──────────────────────────┴──────────────────────────────────────┐
│                      用户本地                                    │
│                                                                  │
│   evalscope eval --model xxx --datasets gsm8k                   │
│   evalscope-viewer upload --key evs_ak_xxx ./outputs            │
└─────────────────────────────────────────────────────────────────┘
```

### Access Key 设计

```
Key 格式: evs_ak_<random_string>
示例:     evs_ak_7f3d8a2b1c9e4f5a
```

| Role | 查看自己 | 查看全部 | 上传 | 删除 | 管理 Key |
|------|---------|---------|------|------|---------|
| `readonly` | ✓ | ✗ | ✗ | ✗ | ✗ |
| `user` | ✓ | ✗ | ✓ | ✓ | ✗ |
| `admin` | ✓ | ✓ | ✓ | ✓ | ✓ |

### 使用方式

```bash
# 管理员：启动服务（首次自动生成 admin key）
evalscope-viewer serve --mode team \
  --data-dir /data/viewer \
  --host 0.0.0.0 \
  --with-web
# 输出: ✓ Admin key: evs_ak_admin_xxxxxxxxx

# 管理员：创建 Key
evalscope-viewer key create --name "alice"
evalscope-viewer key create --name "ci-server" --role readonly
evalscope-viewer key list

# 用户：上传评测结果
evalscope-viewer upload \
  --api-url http://server:7862 \
  --key evs_ak_7f3d8a2b1c9e4f5a \
  ./outputs/20251205_135602

# 或使用环境变量
export EVALSCOPE_API_URL=http://server:7862
export EVALSCOPE_KEY=evs_ak_7f3d8a2b1c9e4f5a
evalscope-viewer upload ./outputs/20251205_135602
```

### 存储结构

```
/data/viewer/
├── viewer.duckdb             # DuckDB 数据库
│   ├── [表] access_keys      # Key 信息 (key_id, name, role, ...)
│   ├── [表] run_ownership    # Run 归属 (run_id, key_id, uploaded_at)
│   └── [表] cache_index      # 缓存索引
└── cache/                    # Parquet 数据
    ├── runs.parquet
    └── samples/{run_id}/*.parquet
```

## 技术选型

| 组件 | 技术 | 说明 |
|------|------|------|
| 查询引擎 | DuckDB | 高性能分析查询，支持直接读取 Parquet |
| 数据存储 | Parquet | 列式压缩，适合大规模评测数据 |
| 认证 | Access Key | 简单的 Key 认证，存储在 DuckDB |
| API | FastAPI | 高性能 Python Web 框架 |
| 前端 | Next.js | React 框架 |

## 数据流

```
单人模式：
  outputs/ ──► 启动时扫描 ──► 生成 Parquet 缓存 ──► DuckDB 查询

团队模式：
  用户上传 ──► API 验证 Key ──► 生成 Parquet ──► 注册归属 ──► DuckDB 查询（按 Key 过滤）
       └── POST /api/runs/upload (Header: X-API-Key)
```
