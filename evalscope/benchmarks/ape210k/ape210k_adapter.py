# Copyright (c) Alibaba, Inc. and its affiliates.

import re
from typing import Any, Dict

from evalscope.api.benchmark import BenchmarkMeta, DefaultDataAdapter
from evalscope.api.dataset import Sample
from evalscope.api.evaluator import TaskState
from evalscope.api.registry import register_benchmark
from evalscope.constants import Tags
from evalscope.utils.logger import get_logger

logger = get_logger()


@register_benchmark(
    BenchmarkMeta(
        name='ape210k',
        pretty_name='Ape210K',
        dataset_id='https://github.com/Chenny0808/ape210k',
        tags=[Tags.MATH, Tags.REASONING],
        description=
        'Ape210K is a large-scale and template-rich math word problem (MWP) dataset. Ape210K contains 210,488 problems and 56,532 templates. We split the whole dataset into train/valid/test.',  # noqa: E501
        subset_list=['default'],
        few_shot_num=0,
        train_split='train',
        eval_split='test',
        metric_list=[{
            'acc': {
                'numeric': True
            }
        }],
        prompt_template='{question}\n请逐步推理，并将最终答案放在 \\boxed{{}} 中。'
    )
)
class Ape210KAdapter(DefaultDataAdapter):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def record_to_sample(self, record: Dict[str, Any]) -> Sample:
        return Sample(
            input=record['original_text'], 
            target=record['ans'], 
            metadata={
                'question_id': record['id'],
                'solution': record['equation'],
            }
        )

    def extract_answer(self, prediction: str, task_state: TaskState):
        from evalscope.metrics.math_parser import extract_answer

        return extract_answer(prediction)
