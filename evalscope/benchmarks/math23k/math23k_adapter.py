# Copyright (c) Alibaba, Inc. and its affiliates.

import os
import re
from typing import Any, Dict

from evalscope.api.benchmark import BenchmarkMeta, DefaultDataAdapter
from evalscope.api.dataset import LocalDataLoader, Sample
from evalscope.api.registry import register_benchmark
from evalscope.constants import Tags
from evalscope.utils.logger import get_logger

logger = get_logger()

PROMPT_TEMPLATE = """请解决以下数学问题。

{question}

请给出你的答案（只回答数字，不要包含单位或其他文字）。
""".lstrip()


@register_benchmark(
    BenchmarkMeta(
        name='math23k',
        pretty_name='Math23k',
        tags=[Tags.REASONING, Tags.MATH, Tags.CHINESE],
        description=
        'Math23k is a Chinese math word problem dataset. The task is to solve math problems and provide numerical answers.',
        dataset_id='',  # Will be set to local path
        subset_list=['default'],
        metric_list=['exact_match'],
        few_shot_num=0,
        train_split='train',
        eval_split='test',
        prompt_template=PROMPT_TEMPLATE,
    )
)
class Math23kAdapter(DefaultDataAdapter):
    """
    Adapter for Math23k Chinese math word problem dataset.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def load(self):
        """
        Load Math23k dataset from local JSONL files.
        Each line is a JSON object with problem information.
        """
        dataset_name_or_path = self.dataset_id
        if not os.path.exists(dataset_name_or_path):
            raise FileNotFoundError(f'Dataset path does not exist: {dataset_name_or_path}')

        # Math23k files are multi-line JSON format (each JSON object spans multiple lines)
        # We need to parse them by accumulating lines until we have a complete JSON object
        import json
        import re
        records = []
        
        with open(dataset_name_or_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
            # Try to parse as JSON array first
            try:
                data = json.loads(content)
                if isinstance(data, list):
                    records = data
                else:
                    records = [data]
            except json.JSONDecodeError:
                # If not a JSON array, try to parse as multiple JSON objects
                # Split by lines that start with '{' (new JSON object)
                # This is a heuristic approach for multi-line JSON objects
                buffer = ''
                brace_count = 0
                for char in content:
                    buffer += char
                    if char == '{':
                        brace_count += 1
                    elif char == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            # Complete JSON object found
                            try:
                                record = json.loads(buffer.strip())
                                records.append(record)
                            except json.JSONDecodeError:
                                pass
                            buffer = ''
                
                # If we still have a buffer, try to parse it
                if buffer.strip():
                    try:
                        record = json.loads(buffer.strip())
                        records.append(record)
                    except json.JSONDecodeError:
                        pass

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
        Convert a Math23k record to a Sample object.
        
        Args:
            record: Dict with problem information (e.g., 'original_text', 'equation', 'ans')
            
        Returns:
            Sample: Sample object with formatted input
        """
        # Try different possible field names
        question = record.get('original_text', record.get('question', record.get('text', '')))
        answer = record.get('ans', record.get('answer', record.get('target', '')))

        input_text = PROMPT_TEMPLATE.format(question=question)

        return Sample(
            input=input_text,
            target=str(answer),
            metadata={
                'id': record.get('id', ''),
                'equation': record.get('equation', ''),
            },
        )

    def extract_answer(self, prediction: str, task_state) -> str:
        """
        Extract the numerical answer from the prediction.
        
        Args:
            prediction: The model's prediction string
            task_state: The current task state
            
        Returns:
            str: The extracted numerical answer
        """
        prediction = prediction.strip()
        
        # Try to extract numbers from the prediction
        # Look for numbers (including decimals)
        numbers = re.findall(r'-?\d+\.?\d*', prediction)
        
        if numbers:
            # Return the last number found (usually the final answer)
            return numbers[-1]
        
        # If no number found, try to extract from common patterns
        patterns = [
            r'答案[：:]\s*([-]?\d+\.?\d*)',
            r'结果是\s*([-]?\d+\.?\d*)',
            r'等于\s*([-]?\d+\.?\d*)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, prediction)
            if match:
                return match.group(1)
        
        logger.warning(f'No valid number found in prediction: {prediction}')
        return prediction.strip()

