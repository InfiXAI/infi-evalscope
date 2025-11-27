# Copyright (c) Alibaba, Inc. and its affiliates.
"""ACEBench adapter built on top of general function-calling logic."""

import subprocess
import sys
from pathlib import Path

from evalscope.api.benchmark import BenchmarkMeta
from evalscope.api.registry import register_benchmark
from evalscope.benchmarks.general_fc.general_fc_adapter import GeneralFCAdapter
from evalscope.constants import Tags
from evalscope.utils import get_logger

logger = get_logger()


ACE_BENCH_SUBSETS = [
    'data_agent_multi_step',
    'data_agent_multi_turn',
    'data_normal_atom_bool',
    'data_normal_atom_enum',
    'data_normal_atom_list',
    'data_normal_atom_number',
    'data_normal_atom_object_deep',
    'data_normal_atom_object_short',
    'data_normal_multi_turn_user_adjust',
    'data_normal_multi_turn_user_switch',
    'data_normal_preference',
    'data_normal_similar_api',
    'data_normal_single_turn_parallel_function',
    'data_normal_single_turn_single_function',
    'data_special_error_param',
    'data_special_incomplete',
    'data_special_irrelevant',
]


DATASET_REPO_ID = 'oliveirabruno01/acebench'


def _default_dataset_path() -> Path:
    repo_root = Path(__file__).resolve().parents[3]
    return repo_root / 'new_data' / 'ACEBench' / 'data_all' / 'general_fc_en'


def _ace_root() -> Path:
    return Path(__file__).resolve().parents[3] / 'new_data' / 'ACEBench'


def _raw_dataset_root(lang: str = 'en') -> Path:
    return _ace_root() / 'data_all' / f'data_{lang}'


def _ensure_raw_dataset(lang: str = 'en') -> None:
    raw_root = _raw_dataset_root(lang)
    if raw_root.exists() and any(raw_root.glob('*.jsonl')):
        return

    try:
        from huggingface_hub import snapshot_download
    except ImportError as e:  # pragma: no cover - missing optional dependency
        raise ImportError('请先安装 huggingface_hub 以自动下载 ACEBench 数据: `pip install huggingface_hub`') from e

    target_dir = _ace_root()
    target_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f'Downloading ACEBench dataset from HuggingFace repo {DATASET_REPO_ID} ...')
    snapshot_download(
        repo_id=DATASET_REPO_ID,
        repo_type='dataset',
        local_dir=str(target_dir),
        local_dir_use_symlinks=False,
    )

    if not raw_root.exists() or not any(raw_root.glob('*.jsonl')):
        raise RuntimeError('ACEBench 数据下载后仍缺失，请检查 HuggingFace 数据布局或手动放置数据。')


def _prepare_dataset(lang: str = 'en') -> str:
    target_dir = _default_dataset_path()
    has_converted_files = target_dir.exists() and any(target_dir.glob('*.jsonl'))
    if has_converted_files:
        return str(target_dir)

    _ensure_raw_dataset(lang)

    converter = Path(__file__).resolve().parents[3] / 'new_data' / 'ACEBench' / 'prepare_general_fc_dataset.py'
    if not converter.exists():
        raise FileNotFoundError('[ace_bench] 转换脚本缺失: prepare_general_fc_dataset.py')

    logger.info('Preparing ACEBench dataset (first run only)...')
    cmd = [sys.executable, str(converter), '--languages', lang]
    subprocess.run(cmd, check=True)

    if not any(target_dir.glob('*.jsonl')):
        raise RuntimeError('[ace_bench] 数据转换失败，请检查 prepare_general_fc_dataset.py 的输出。')

    return str(target_dir)


@register_benchmark(
    BenchmarkMeta(
        name='ace_bench',
        pretty_name='ACEBench',
        description='ACEBench tool-use benchmark in EvalScope general_fc format.',
        tags=[Tags.FUNCTION_CALLING, Tags.CUSTOM, Tags.AGENT],
        dataset_id=_prepare_dataset(),
        subset_list=ACE_BENCH_SUBSETS,
        metric_list=[
            'count_finish_reason_tool_call',
            'count_successful_tool_call',
            'schema_accuracy',
            'tool_call_f1',
        ],
        aggregation='f1',
        eval_split='test',
    ))
class AceBenchAdapter(GeneralFCAdapter):
    """Reuse GeneralFCAdapter behavior for ACEBench."""

    pass
