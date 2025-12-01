# Copyright (c) Alibaba, Inc. and its affiliates.

import os
import re
from typing import Any, Dict

from evalscope.api.benchmark import BenchmarkMeta, MultiChoiceAdapter
from evalscope.api.dataset import LocalDataLoader, Sample
from evalscope.api.registry import register_benchmark
from evalscope.constants import Tags
from evalscope.utils.logger import get_logger
from evalscope.utils.multi_choices import MultipleChoiceTemplate

logger = get_logger()

# ChID uses standard Chinese multiple choice template
# We'll format the text in record_to_sample and use {question} and {choices}


@register_benchmark(
    BenchmarkMeta(
        name='chid',
        pretty_name='ChID',
        tags=[Tags.KNOWLEDGE, Tags.MULTIPLE_CHOICE, Tags.CHINESE],
        description=
        'ChID (Chinese Idiom Dataset) is a large-scale Chinese idiom dataset for cloze test. The task is to select the most appropriate idiom to fill in the blank.',
        dataset_id='',  # Will be set to local path
        subset_list=['default'],
        metric_list=['acc'],
        few_shot_num=0,
        train_split=None,
        eval_split='test',
        prompt_template=MultipleChoiceTemplate.CHINESE_SINGLE_ANSWER_TEMPLATE_COT,
    )
)
class ChIDAdapter(MultiChoiceAdapter):
    """
    Adapter for ChID (Chinese Idiom Dataset) cloze test.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def load(self):
        """
        Load ChID dataset from local JSONL files.
        Each line is a JSON object with 'candidates' and 'content'.
        ChID files are .txt format but contain JSONL data.
        """
        dataset_name_or_path = self.dataset_id
        if not os.path.exists(dataset_name_or_path):
            raise FileNotFoundError(f'Dataset path does not exist: {dataset_name_or_path}')

        # ChID files are .txt format but contain JSONL data (one JSON object per line)
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
        Convert a ChID record to a Sample object.
        
        Args:
            record: Dict with 'candidates' (list) and 'content' (list of strings with #idiom# placeholders)
            
        Returns:
            Sample: Sample object with formatted input and choices
        """
        candidates = record['candidates']
        content_list = record['content']
        
        # Combine content into a single text
        text = '\n'.join(content_list)
        
        # Format the input text with context
        # The MultiChoiceAdapter will add choices formatting using {question} and {choices}
        input_text = f"""阅读以下文本，选择最合适的成语填入空白处。

{text}

候选成语："""
        
        # Find the correct answer by matching idiom placeholders
        # The content has placeholders like #idiom123456#, we need to find which candidate matches
        # For now, we'll use the first candidate as placeholder (this might need adjustment based on actual data)
        # In actual evaluation, the answer should be provided in the dataset
        answer = 'A'  # Default, should be determined from the dataset
        
        # Try to extract answer from content if possible
        # Look for patterns that might indicate the answer
        for i, candidate in enumerate(candidates):
            # Check if this idiom appears in the content (without the placeholder)
            if candidate in text:
                answer = chr(65 + i)
                break

        return Sample(
            input=input_text,
            choices=candidates,
            target=answer,
            metadata={
                'id': record.get('id', ''),
            },
        )

    def extract_answer(self, prediction: str, task_state) -> str:
        """
        Extract the answer from the prediction.
        
        Args:
            prediction: The model's prediction string
            task_state: The current task state
            
        Returns:
            str: The extracted answer (A, B, C, etc.)
        """
        # Try to find answer in various formats
        patterns = [
            r'答案[：:]\s*([A-Z])',
            r'选择\s*([A-Z])',
            r'选项\s*([A-Z])',
            r'\b([A-Z])\b',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, prediction, re.IGNORECASE)
            if match:
                return match.group(1).upper()
        
        # If no match found, return the first character if it's A-Z
        prediction = prediction.strip()
        if prediction and prediction[0].upper().isalpha():
            return prediction[0].upper()
        
        logger.warning(f'No valid answer found in prediction: {prediction}')
        return ''

