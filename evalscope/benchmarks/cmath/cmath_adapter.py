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
        name='cmath',
        pretty_name='CMATH',
        dataset_id='HuggingFace/weitianwen/cmath',
        tags=[Tags.MATH, Tags.REASONING],
        description=
        'We present the Chinese Elementary School Math Word Problems (CMATH) dataset, comprising 1.7k elementary school-level math word problems with detailed annotations, source from actual Chinese workbooks and exams. This dataset aims to provide a benchmark tool for assessing the following question: to what grade level of elementary school math do the abilities of popular large language models (LLMs) correspond? We evaluate a variety of popular LLMs, including both commercial and open-source options, and discover that only GPT-4 achieves success (accuracy >= 60%) across all six elementary school grades, while other models falter at different grade levels. Furthermore, we assess the robustness of LLMs by augmenting the original problems in the CMATH dataset with distracting information. Our findings reveal that GPT-4 is the sole model that maintains robustness, further distinguishing its performance from competing models. We anticipate that our CMATH dataset will expose limitations in LLMs\' capabilities and promote their ongoing development and advancement.',  # noqa: E501
        subset_list=['Grade 1', 'Grade 2', 'Grade 3', 'Grade 4', 'Grade 5'],
        few_shot_num=0,
        train_split=None,
        eval_split='test',
        metric_list=[{
            'acc': {
                'numeric': True
            }
        }],
        prompt_template='{question}\n请逐步推理，并将最终答案放在 \\boxed{{}} 中。'
    )
)
class CMATHAdapter(DefaultDataAdapter):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.reformat_subset = True

    def record_to_sample(self, record: Dict[str, Any]) -> Sample:
        return Sample(
            input=record['question'], 
            target=record['golden'], 
            subset_key=f"Grade {record['grade']}",
            metadata={
                'reasoning_step': record['reasoning_step'],
                'num_digits': record['num_digits'],
            }
        )

    def extract_answer(self, prediction: str, task_state: TaskState):
        from evalscope.metrics.math_parser import extract_answer

        return extract_answer(prediction)
