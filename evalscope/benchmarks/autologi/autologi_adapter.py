# Copyright (c) Alibaba, Inc. and its affiliates.
# flake8: noqa: E501
import re
from typing import Any, Dict

from evalscope.api.benchmark import BenchmarkMeta, DefaultDataAdapter
from evalscope.api.dataset import Sample
from evalscope.api.evaluator import TaskState
from evalscope.api.messages.chat_message import ChatMessageUser
from evalscope.api.metric import Score
from evalscope.api.registry import register_benchmark
from evalscope.constants import Tags
from evalscope.utils.logger import get_logger

from .utils import compute_coding_pass1, get_prompt_list

logger = get_logger()


@register_benchmark(
    BenchmarkMeta(
        name='autologi',
        pretty_name='AutoLogi',
        tags=[Tags.CODING],
        description=
        'HumanEval is a benchmark for evaluating the ability of code generation models to write Python functions based on given specifications. It consists of programming tasks with a defined input-output behavior. '
        '**By default the code is executed in local environment. We recommend using sandbox execution to safely run and evaluate the generated code, please refer to the [documentation](https://evalscope.readthedocs.io/en/latest/user_guides/sandbox.html) for more details.**',  # noqa: E501
        dataset_id='opencompass/humaneval',
        subset_list=['default'],
        aggregation='mean_and_pass_at_k',
        eval_split='test',
        prompt_template='{question}',
    )
)
class AutoLogiAdapter(DefaultDataAdapter):
    """
    AutoLogi adapter using the new data processing framework.
    """

    def record_to_sample(self, record: Dict[str, Any]) -> Sample:
        """Convert a data record to a Sample object."""
        return Sample(
            input=record['prompt'],
            target="",
            metadata={
                'Inputs_Check_code': record['code']['Inputs_Check_code'],
                'Constraint_List_code': record['code']['Constraint_List_code'],
                'Traverse_code': record['code']['Traverse_code'],
                'idx': record['idx'],
            }
        )

    def extract_answer(self, prediction: str, task_state: TaskState) -> str:
        """Extract code from the prediction."""
        code_block_pattern = re.compile(r"```(?:\s*[\w]+)?\s*\n(.*?)```", re.DOTALL)
        code_blocks = code_block_pattern.findall(prediction)
        
        if code_blocks:
            return code_blocks[-1]
        else:
            return ""

    def match_score(
        self, original_prediction: str, filtered_prediction: str, reference: str, task_state: TaskState
    ) -> Score:

        score = Score(
            extracted_prediction=filtered_prediction,
            prediction=original_prediction,
        )
        
        input_example = get_prompt_list(filtered_prediction, task_state)
        res = compute_coding_pass1(input_example)

        # Set score values
        score.value = {'acc': res['acc']}
        score.metadata = {'task_id': task_state.metadata['idx'], 'error': res['error'], 'extraction_failed': res['extraction_failed']}
        score.main_score_name = 'acc'

        return score
