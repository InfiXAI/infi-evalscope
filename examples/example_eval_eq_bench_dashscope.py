#!/usr/bin/env python3
# Copyright (c) Alibaba, Inc. and its affiliates.

"""
使用阿里云 DashScope API（百炼平台）评测 EQ-Bench

环境要求：
    pip install evalscope

使用方法：
    # 设置环境变量
    export DASHSCOPE_API_KEY='your-dashscope-api-key'
    export DASHSCOPE_MODEL='qwen2.5-72b-instruct'  # 可选

    # 运行评测
    python examples/example_eval_eq_bench_dashscope.py

支持的模型：
    - qwen2.5-72b-instruct (默认)
    - qwen2.5-32b-instruct
    - qwen-plus
    - qwen-turbo
    - qwen-max
    等其他百炼平台支持的模型

获取 API Key：
    https://dashscope.console.aliyun.com/apiKey

参考文档：
    https://help.aliyun.com/zh/dashscope/
"""

import os
from pathlib import Path
from evalscope import run_task, TaskConfig

# 获取项目根目录
PROJECT_ROOT = Path(__file__).parent.parent
DATASET_PATH = PROJECT_ROOT / 'datasets' / 'EQ-bench'


def main():
    """使用阿里云 DashScope API 评测 EQ-Bench"""

    print("=" * 60)
    print("使用阿里云 DashScope API 评测 EQ-Bench")
    print("=" * 60)

    # 从环境变量获取配置
    api_key = os.getenv('DASHSCOPE_API_KEY', '')
    model_name = os.getenv('DASHSCOPE_MODEL', 'qwen2.5-72b-instruct')
    base_url = 'https://dashscope.aliyuncs.com/compatible-mode/v1'

    # 验证 API Key
    if not api_key:
        print("\n❌ 错误: DASHSCOPE_API_KEY 未设置！")
        print("\n请按以下步骤操作：")
        print("1. 访问 https://dashscope.console.aliyun.com/apiKey 获取 API Key")
        print("2. 设置环境变量:")
        print("   export DASHSCOPE_API_KEY='your-dashscope-api-key'")
        print("3. 重新运行此脚本")
        return

    print(f"\n📋 配置信息:")
    print(f"   - 模型: {model_name}")
    print(f"   - Base URL: {base_url}")
    print(f"   - API Key: {api_key[:20]}...{api_key[-4:]}" if len(api_key) > 24 else f"   - API Key: {api_key}")

    # 配置评测任务
    task_cfg = TaskConfig(
        # 模型配置
        model=model_name,
        eval_type='openai_api',  # DashScope 兼容 OpenAI API 格式

        # API 配置
        api_url=base_url,
        api_key=api_key,

        # 数据集配置
        datasets=['eq_bench'],
        dataset_args={
            'eq_bench': {
                'dataset_id': str(DATASET_PATH),
            }
        },

        # 评测配置
        #limit=10,  # 只评测前10个样本（用于快速测试）
        # limit=None,  # 取消注释以评测所有样本
        eval_batch_size=5,

        # 生成配置（针对 EQ-Bench 优化）
        generation_config={
            'max_tokens': 60,  # EQ-Bench 官方建议: REVISE=False 时使用 60
            'temperature': 0.01,  # ⚠️ EQ-Bench 必须使用低温度
            'timeout': 120,
        },

        # 其他配置
        debug=True,
        timeout=120,
        work_dir='outputs/eq_bench_dashscope',
    )

    # 运行评测
    print("\n开始评测...")
    print(f"数据集路径: {DATASET_PATH}")
    print(f"评测样本数: {'全部' if task_cfg.limit is None else task_cfg.limit}")

    try:
        result = run_task(task_cfg=task_cfg)

        print("\n✅ 评测完成！")
        print(f"\n结果保存在: {task_cfg.work_dir}")
        print("\n查看结果：")
        print(f"  - 详细日志: {task_cfg.work_dir}/logs/")
        print(f"  - 预测结果: {task_cfg.work_dir}/predictions/")
        print(f"  - 评分结果: {task_cfg.work_dir}/reviews/")
        print(f"  - 最终报告: {task_cfg.work_dir}/reports/")

        return result

    except Exception as e:
        print(f"\n❌ 评测失败: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == '__main__':
    main()
