#!/usr/bin/env python3
# Copyright (c) Alibaba, Inc. and its affiliates.

"""
使用 SiliconFlow API 评测 EQ-Bench 示例

这个脚本展示如何使用 SiliconFlow API 来评测 EQ-Bench。

环境要求：
    pip install evalscope

使用方法：
    # 设置环境变量（推荐，避免 API Key 暴露在代码中）
    export SILICONFLOW_API_KEY='your-api-key-here'
    python examples/example_eval_eq_bench_api.py
    
    # 或者直接在命令行设置
    SILICONFLOW_API_KEY='your-api-key-here' python examples/example_eval_eq_bench_api.py
    
注意：
    - API Key 已从代码中移除，必须通过环境变量 SILICONFLOW_API_KEY 提供
    - 这样可以避免敏感信息泄露到代码仓库中
"""

import os
from pathlib import Path
from evalscope import run_task, TaskConfig

# 获取项目根目录（脚本所在目录的父目录）
PROJECT_ROOT = Path(__file__).parent.parent
DATASET_PATH = PROJECT_ROOT / 'datasets' / 'EQ-bench'


def eval_eq_bench_with_api():
    """使用 SiliconFlow API 服务评测 EQ-Bench"""

    print("=" * 60)
    print("使用 SiliconFlow API 评测 EQ-Bench")
    print("=" * 60)

    # 方式 1: 使用 TaskConfig 对象
    task_cfg = TaskConfig(
        # 模型配置
        model='Qwen/QwQ-32B',  # SiliconFlow 模型名称
        eval_type='openai_api',  # 使用 OpenAI 兼容的 API

        # API 配置
        api_url='https://api.siliconflow.cn/v1',  # SiliconFlow API 基础 URL
        api_key=os.getenv('SILICONFLOW_API_KEY', ''),  # 从环境变量获取 API Key，避免暴露在代码中

        # 数据集配置
        datasets=['eq_bench'],

        # 数据集参数（使用绝对路径确保能找到本地数据集）
        dataset_args={
            'eq_bench': {
                'dataset_id': str(DATASET_PATH),  # EQ-Bench 数据集的本地绝对路径
            }
        },

        # 评测配置
        limit=2,  # 只评测前10个样本（用于快速测试）
        eval_batch_size=5,  # 批量大小

        # 生成配置（针对 EQ-Bench 优化）
        generation_config={
            'max_tokens': 256,  # EQ-Bench 每个问题需要约 60 tokens
            'temperature': 0.01,  # ⚠️ EQ-Bench 必须使用低温度（0.01）保证一致性
            'top_p': 0.7,  # SiliconFlow 推荐值
            'top_k': 50,  # SiliconFlow 推荐值
            'frequency_penalty': 0.5,
            'min_p': 0.05,  # SiliconFlow 支持的参数
            # 'enable_thinking': False,  # QwQ 模型特有参数（EvalScope 可能不支持）
        },

        # 其他配置
        debug=True,  # 开启调试模式
        work_dir='outputs/eq_bench_api',  # 结果保存目录
    )

    # 运行评测
    print("\n开始评测...")
    result = run_task(task_cfg=task_cfg)

    print("\n评测完成！")
    print(f"结果保存在: {task_cfg.work_dir}")

    return result


def eval_eq_bench_with_dict():
    """使用字典配置评测 EQ-Bench（更灵活的方式）"""

    print("\n" + "=" * 60)
    print("使用字典配置评测 EQ-Bench")
    print("=" * 60)

    # 方式 2: 使用字典配置
    task_cfg = {
        # 模型配置
        'model': 'Qwen/QwQ-32B',  # SiliconFlow 模型名称
        'eval_type': 'openai_api',

        # API 配置
        'api_url': 'https://api.siliconflow.cn/v1',  # SiliconFlow API URL
        'api_key': os.getenv('SILICONFLOW_API_KEY', ''),  # 从环境变量获取 API Key

        # 数据集配置
        'datasets': ['eq_bench'],

        # 数据集参数
        'dataset_args': {
            'eq_bench': {
                'dataset_id': str(DATASET_PATH),  # EQ-Bench 数据集绝对路径
            }
        },

        # 评测配置
        'limit': 10,  # 只评测前10个样本
        'eval_batch_size': 5,

        # 生成配置（针对 EQ-Bench 优化）
        'generation_config': {
            'max_tokens': 256,
            'temperature': 0.01,  # ⚠️ EQ-Bench 必须使用低温度
            'top_p': 0.7,
            'top_k': 50,
            'frequency_penalty': 0.5,
            'min_p': 0.05,
        },

        # 其他配置
        'debug': True,
        'work_dir': 'outputs/eq_bench_api_dict',
    }

    # 运行评测
    print("\n开始评测...")
    result = run_task(task_cfg=task_cfg)

    print("\n评测完成！")
    print(f"结果保存在: {task_cfg['work_dir']}")

    return result


def eval_eq_bench_full():
    """完整评测 EQ-Bench（所有 171 个问题）"""

    print("\n" + "=" * 60)
    print("完整评测 EQ-Bench（所有问题）")
    print("=" * 60)
    print("\n⚠️  警告：这将评测全部 171 个问题，可能需要较长时间和一定的 API 费用。")

    # 询问用户确认
    import sys
    response = input("是否继续？(yes/no): ")
    if response.lower() not in ['yes', 'y']:
        print("已取消。")
        sys.exit(0)

    task_cfg = TaskConfig(
        # 模型配置
        model='Qwen/QwQ-32B',  # SiliconFlow 模型
        eval_type='openai_api',

        # API 配置
        api_url='https://api.siliconflow.cn/v1',  # SiliconFlow API URL
        api_key=os.getenv('SILICONFLOW_API_KEY', ''),  # 从环境变量获取 API Key

        # 数据集配置
        datasets=['eq_bench'],
        dataset_args={
            'eq_bench': {
                'dataset_id': str(DATASET_PATH),  # 使用绝对路径
            }
        },

        # 评测配置
        limit=None,  # 评测所有样本
        eval_batch_size=10,  # 提高批量大小以加快速度

        # 生成配置（针对 EQ-Bench 优化）
        generation_config={
            'max_tokens': 256,
            'temperature': 0.01,  # ⚠️ EQ-Bench 必须使用低温度
            'top_p': 0.7,
            'top_k': 50,
            'frequency_penalty': 0.5,
            'min_p': 0.05,
        },

        # 其他配置
        debug=False,  # 关闭调试模式以减少日志
        work_dir='outputs/eq_bench_full',

        # 使用缓存以便中断后继续
        use_cache=None,  # 设置为之前的输出目录可以继续之前的评测
    )

    # 运行评测
    print("\n开始完整评测...")
    result = run_task(task_cfg=task_cfg)

    print("\n评测完成！")
    print(f"结果保存在: {task_cfg.work_dir}")
    print("\n查看结果：")
    print(f"  - 详细日志: {task_cfg.work_dir}/logs/")
    print(f"  - 预测结果: {task_cfg.work_dir}/predictions/")
    print(f"  - 评分结果: {task_cfg.work_dir}/reviews/")
    print(f"  - 最终报告: {task_cfg.work_dir}/reports/")

    return result


if __name__ == '__main__':
    # 选择要运行的评测方式

    # 方式 1: 使用 TaskConfig 对象（推荐）
    print("\n方式 1: 使用 TaskConfig 对象")
    eval_eq_bench_with_api()

    # 方式 2: 使用字典配置
    # print("\n方式 2: 使用字典配置")
    # eval_eq_bench_with_dict()

    # 方式 3: 完整评测（所有问题）
    # print("\n方式 3: 完整评测")
    # eval_eq_bench_full()
