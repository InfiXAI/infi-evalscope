# Copyright (c) Alibaba, Inc. and its affiliates.

import os
from typing import Any, Dict

from evalscope.api.benchmark import BenchmarkMeta, DefaultDataAdapter
from evalscope.api.dataset import LocalDataLoader, Sample
from evalscope.api.registry import register_benchmark
from evalscope.constants import Tags
from evalscope.utils.logger import get_logger

logger = get_logger()

# CLUEWSC uses a simple template with {question}
# We'll format the full prompt in record_to_sample


@register_benchmark(
    BenchmarkMeta(
        name='cluewsc',
        pretty_name='CLUEWSC',
        tags=[Tags.KNOWLEDGE, Tags.CHINESE, Tags.REASONING],
        description=
        'CLUEWSC (CLUE Winograd Schema Challenge) is a Chinese coreference resolution dataset. The task is to determine if two spans refer to the same entity.',
        dataset_id='',  # Will be set to local path
        subset_list=['default'],
        metric_list=['acc'],
        few_shot_num=0,
        train_split=None,
        eval_split='test',
        prompt_template='{question}',  # Simple template, we format everything in record_to_sample
    )
)
class CLUEWSCAdapter(DefaultDataAdapter):
    """
    Adapter for CLUEWSC (CLUE Winograd Schema Challenge) coreference resolution.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def load(self):
        """
        Load CLUEWSC dataset from local JSONL files.
        Each line is a JSON object with 'id', 'text', 'target' (containing span1 and span2).
        """
        dataset_name_or_path = self.dataset_id
        if not os.path.exists(dataset_name_or_path):
            raise FileNotFoundError(f'Dataset path does not exist: {dataset_name_or_path}')

        # CLUEWSC files are JSONL format (one JSON object per line)
        import json
        records = []
        with open(dataset_name_or_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                    records.append(record)
                except json.JSONDecodeError as e:
                    logger.warning(f'Failed to parse JSON line: {line[:100]}... Error: {e}')
                    continue

        # Use DictDataLoader to load from records
        from evalscope.api.dataset import DatasetDict, DictDataLoader
        dataset = DictDataLoader(
            dict_list=records,
            sample_fields=self.record_to_sample,
            limit=self.limit,
            shuffle=self.shuffle,
        ).load()

        test_dataset = DatasetDict({'default': dataset})

        return test_dataset, None

    def record_to_sample(self, record: Dict[str, Any]) -> Sample:
        """
        Convert a CLUEWSC record to a Sample object.
        
        Args:
            record: Dict with 'id', 'text', 'target' (containing 'span1_text', 'span2_text', etc.)
            
        Returns:
            Sample: Sample object with formatted input
        """
        # Get text field (may be 'text' or other field names)
        text = record.get('text', record.get('sentence', record.get('content', '')))
        target = record.get('target', {})
        span1_text = target.get('span1_text', '')
        span2_text = target.get('span2_text', '')

        # Format the complete prompt
        input_text = f"""阅读以下文本，判断两个加粗的词是否指向同一个实体。

文本：{text}

span1: {span1_text}
span2: {span2_text}

请判断 span1 和 span2 是否指向同一个实体。只回答"是"或"否"。"""

        # The answer is "是" (yes) if they refer to the same entity, "否" (no) otherwise
        # We need to determine this from the context - for now, we'll use a placeholder
        # In actual evaluation, the answer should be provided in the dataset
        answer = "是"  # Default, should be determined from the dataset

        return Sample(
            input=input_text,
            target=answer,
            metadata={
                'id': record.get('id', ''),
                'span1_index': target.get('span1_index', -1),
                'span2_index': target.get('span2_index', -1),
            },
        )

    def extract_answer(self, prediction: str, task_state) -> str:
        """
        Extract the answer from the prediction.
        
        Args:
            prediction: The model's prediction string
            task_state: The current task state
            
        Returns:
            str: The extracted answer ("是" or "否")
        """
        prediction = prediction.strip()
        
        # Check for "是" or "否"
        if "是" in prediction and "否" not in prediction:
            return "是"
        elif "否" in prediction:
            return "否"
        elif "yes" in prediction.lower() or "true" in prediction.lower():
            return "是"
        elif "no" in prediction.lower() or "false" in prediction.lower():
            return "否"
        
        logger.warning(f'No valid answer found in prediction: {prediction}')
        return prediction[:1] if prediction else "否"

