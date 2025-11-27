#!/usr/bin/env python3
# Copyright (c) Alibaba, Inc. and its affiliates.

"""
使用配置文件 API 评测 EQ-Bench 示例

这个脚本展示如何从 llm_config.yaml 配置文件读取 API 配置来评测 EQ-Bench。

环境要求：
    pip install evalscope pyyaml

配置方式（按优先级）：
    1. 环境变量（推荐）：
       export LLM_API_KEY='your-api-key'
       export LLM_BASE_URL='https://proxy.infix-ai.xyz/v1'
       export LLM_MODEL='openai/gpt-4o-mini'
       export LLM_TEMPERATURE='0'
       export LLM_MAX_TOKENS='60'  # EQ-Bench 官方建议: REVISE=False 时使用 60
    
    2. 配置文件（可选）：
       examples/api_test/llm_config.yaml
    
使用方法：
    # 方式 1: 使用环境变量（推荐）
    export LLM_API_KEY='your-api-key'
    python examples/example_eval_eq_bench_api.py
    
    # 方式 2: 使用配置文件
    # 确保 examples/api_test/llm_config.yaml 存在
    python examples/example_eval_eq_bench_api.py
    
配置说明：
    - 优先从环境变量读取配置
    - 如果环境变量未设置，会尝试从配置文件读取
    - API Key 必须设置（环境变量或配置文件）
    - 默认模型: openai/gpt-4o-mini
    - 默认 Base URL: https://proxy.infix-ai.xyz/v1
"""

import os
import yaml
from pathlib import Path
from evalscope import run_task, TaskConfig

# 获取项目根目录（脚本所在目录的父目录）
PROJECT_ROOT = Path(__file__).parent.parent
DATASET_PATH = PROJECT_ROOT / 'datasets' / 'EQ-bench'


def load_llm_config():
    """
    加载 LLM 配置
    
    优先从环境变量读取，如果没有则使用默认配置。
    也可以从配置文件读取（如果存在）。
    """
    # 优先从环境变量读取
    base_url = os.getenv('LLM_BASE_URL', 'https://proxy.infix-ai.xyz/v1')
    api_key = os.getenv('LLM_API_KEY') or os.getenv('DEEPSEEK_API_KEY', '')
    model = os.getenv('LLM_MODEL', 'openai/gpt-4o')
    temperature = float(os.getenv('LLM_TEMPERATURE', '0'))
    max_tokens = int(os.getenv('LLM_MAX_TOKENS', '0')) or 60  # EQ-Bench 官方建议: REVISE=False 时使用 60
    
    # 如果环境变量未设置，尝试从配置文件读取（可选）
    config_file = PROJECT_ROOT / 'examples' / 'api_test' / 'llm_config.yaml'
    if not api_key and config_file.exists():
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                file_config = yaml.safe_load(f)
                base_url = file_config.get('base_url', base_url)
                api_key = file_config.get('api_key', '') or api_key
                models = file_config.get('models', [model])
                model = models[0] if models else model
                temperature = file_config.get('temperature', temperature)
                max_tokens = file_config.get('max_tokens', 0) or max_tokens
        except Exception as e:
            print(f"警告: 无法读取配置文件 {config_file}: {e}")
    
    if not api_key:
        raise ValueError(
            "API Key 未设置！请通过以下方式之一设置：\n"
            "1. 环境变量: export LLM_API_KEY='your-api-key'\n"
            "2. 环境变量: export DEEPSEEK_API_KEY='your-api-key'\n"
            "3. 配置文件: examples/api_test/llm_config.yaml"
        )
    
    return {
        'base_url': base_url,
        'api_key': api_key,
        'models': [model],
        'temperature': temperature,
        'max_tokens': max_tokens,
    }


def eval_eq_bench_with_api():
    """使用配置文件中的 API 服务评测 EQ-Bench"""

    print("=" * 60)
    print("使用配置文件 API 评测 EQ-Bench")
    print("=" * 60)

    # 从配置文件加载配置
    llm_config = load_llm_config()
    
    # 获取模型名称（优先使用配置文件中的第一个模型）
    model_name = llm_config.get('models', ['openai/gpt-4o-mini'])[0]
    base_url = llm_config.get('base_url', '')
    api_key = llm_config.get('api_key', '') or os.getenv('DEEPSEEK_API_KEY', '')
    
    print(f"\n📋 配置信息:")
    print(f"   - 模型: {model_name}")
    print(f"   - Base URL: {base_url}")
    print(f"   - API Key: {api_key[:20]}..." if len(api_key) > 20 else f"   - API Key: {api_key}")
    print(f"   - Temperature: {llm_config.get('temperature', 0)}")
    print(f"   - Max Tokens: {llm_config.get('max_tokens', 0)}")

    # 方式 1: 使用 TaskConfig 对象
    task_cfg = TaskConfig(
        # 模型配置（从配置文件读取）
        model=model_name,  # 使用配置文件中的模型
        eval_type='openai_api',  # 使用 OpenAI 兼容的 API

        # API 配置（从配置文件读取）
        api_url=base_url,  # 从配置文件读取 base_url
        api_key=api_key,  # 从配置文件读取 api_key，如果为空则从环境变量获取

        # 数据集配置
        datasets=['eq_bench'],

        # 数据集参数（使用绝对路径确保能找到本地数据集）
        dataset_args={
            'eq_bench': {
                'dataset_id': str(DATASET_PATH),  # EQ-Bench 数据集的本地绝对路径
            }
        },

        # 评测配置
        #limit=2,  # 只评测前2个样本（用于快速测试）
        eval_batch_size=5,  # 批量大小

        # 生成配置（从配置文件读取，针对 EQ-Bench 优化）
        generation_config={
            'max_tokens': llm_config.get('max_tokens', 0) or 60,  # EQ-Bench 官方建议: REVISE=False 时使用 60
            'temperature': llm_config.get('temperature', 0.01),  # ⚠️ EQ-Bench 必须使用低温度
            'timeout': 120,  # 设置超时时间（秒），避免请求卡住
        },

        # 其他配置
        debug=False,  # 开启调试模式，可以看到详细的进度日志
        timeout=120,  # API 请求超时时间（秒）
        work_dir='outputs/eq_bench_api',  # 结果保存目录
    )

    # 运行评测
    print("\n开始评测...")
    result = run_task(task_cfg=task_cfg)

    print("\n评测完成！")
    print(f"结果保存在: {task_cfg.work_dir}")

    return result


def eval_eq_bench_with_dict():
    """使用字典配置评测 EQ-Bench（从配置文件读取）"""

    print("\n" + "=" * 60)
    print("使用字典配置评测 EQ-Bench（从配置文件读取）")
    print("=" * 60)

    # 从配置文件加载配置
    llm_config = load_llm_config()
    model_name = llm_config.get('models', ['openai/gpt-4o-mini'])[0]
    base_url = llm_config.get('base_url', '')
    api_key = llm_config.get('api_key', '') or os.getenv('DEEPSEEK_API_KEY', '')

    # 方式 2: 使用字典配置
    task_cfg = {
        # 模型配置（从配置文件读取）
        'model': model_name,
        'eval_type': 'openai_api',

        # API 配置（从配置文件读取）
        'api_url': base_url,
        'api_key': api_key,

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

        # 生成配置（从配置文件读取）
        'generation_config': {
            'max_tokens': llm_config.get('max_tokens', 0) or 60,  # EQ-Bench 官方建议: REVISE=False 时使用 60
            'temperature': llm_config.get('temperature', 0.01),  # ⚠️ EQ-Bench 必须使用低温度
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
    """完整评测 EQ-Bench（所有问题，从配置文件读取配置）"""

    print("\n" + "=" * 60)
    print("完整评测 EQ-Bench（所有问题）")
    print("=" * 60)
    print("\n⚠️  警告：这将评测全部样本，可能需要较长时间和一定的 API 费用。")

    # 询问用户确认
    import sys
    response = input("是否继续？(yes/no): ")
    if response.lower() not in ['yes', 'y']:
        print("已取消。")
        sys.exit(0)

    # 从配置文件加载配置
    llm_config = load_llm_config()
    model_name = llm_config.get('models', ['openai/gpt-4o-mini'])[0]
    base_url = llm_config.get('base_url', '')
    api_key = llm_config.get('api_key', '') or os.getenv('DEEPSEEK_API_KEY', '')

    task_cfg = TaskConfig(
        # 模型配置（从配置文件读取）
        model=model_name,
        eval_type='openai_api',

        # API 配置（从配置文件读取）
        api_url=base_url,
        api_key=api_key,

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

        # 生成配置（从配置文件读取）
        generation_config={
            'max_tokens': llm_config.get('max_tokens', 0) or 60,  # EQ-Bench 官方建议: REVISE=False 时使用 60
            'temperature': llm_config.get('temperature', 0.01),  # ⚠️ EQ-Bench 必须使用低温度
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
