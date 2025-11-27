# 一键数据集接入规范

以下规范适用于需要“一键启动”评测的数据集：用户仅需运行一条 `evalscope eval ... --datasets xxx` 命令，即可自动完成数据下载、格式转换、环境准备和评分。

## 1. Benchmark 适配器

1. 在 `evalscope/benchmarks/<dataset>/<dataset>_adapter.py` 中注册 `BenchmarkMeta`。
2. `dataset_id` 指向默认数据源（本地目录或远程数据集 ID），`subset_list`、`metric_list` 等与常规 benchmark 一致。
3. 如需额外参数，通过 `extra_params` 暴露，便于 CLI/TaskConfig 覆盖。
4. 适配器需要：
   - **自动检测/准备数据**：在 `__init__` 或 `load()` 中调用确保数据存在的逻辑；
   - **实现 `record_to_sample`**：将原始记录转成 EvalScope 的 `Sample`；
   - **自定义 `_post_process_samples`（可选）**：执行镜像构建、额外字段注入等步骤；
   - **实现 `_on_inference` / `match_score`**：定义推理流程和指标计算。

## 2. 数据下载与转换脚本

1. 如果需要从远程仓库下载原始数据：
   - 推荐上传到 ModelScope / HuggingFace；
   - 在适配器里调用 `huggingface_hub.snapshot_download()` 或 `RemoteDataLoader` 自动拉取，下载路径建议放在 `new_data/<Dataset>/...`；
   - 下载完成后，检查数据目录是否存在。
2. 若需要本地转换流程（如 JSON → EvalScope JSONL），在 `new_data/<Dataset>/prepare_xxx.py` 中实现：
   - 支持命令行参数（语言、子集等）；
   - 成功运行后把数据写到统一目录（例如 `new_data/<Dataset>/data_all/general_fc_en`）；
   - 适配器检测到输出缺失时自动调用脚本。

## 3. 环境准备（镜像 / 依赖）

1. 依赖包：在适配器 `__init__` 里通过 `check_import()` 检查，缺失时给出 pip 安装提示；
2. 若需要 Docker 镜像或其他外部资源：
   - 在 `evalscope/benchmarks/<dataset>/build_*.py` 等模块里封装准备逻辑；
   - 在 `_post_process_samples()` 中自动执行（参考 `swe_bench` 的 `build_images.py`）；
   - 提供参数（例如 `extra_params.build_docker_images`）允许用户控制是否构建/拉取。

## 4. 示例任务与文档

1. 在 `examples/tasks/` 中添加或更新示例配置，演示如何设置 `datasets`、`dataset_args`、`extra_params`；
2. 在 `docs/zh/third_party/` 或 `docs/zh/advanced_guides/` 补充使用说明：
   - 命令示例（本地 / 云端）；
   - 必备依赖（Python 包、Docker、环境变量等）；
   - 首次运行时的自动下载/转换流程。

## 5. 一键体验要求

1. 用户只需运行一次 `evalscope eval ... --datasets <dataset>` 即可启动评测；
2. 所有准备步骤（下载、转换、镜像）由适配器自动完成；
3. 错误提示清晰，例如缺少依赖、下载失败或转换失败时明确告知；
4. 结果文件（日志、预测、报告）仍按照 EvalScope 既有目录结构输出，便于复现和分析。

符合上述规范的数据集，即可实现与 `swe_bench`、`ace_bench` 等相同的一键评测体验。
