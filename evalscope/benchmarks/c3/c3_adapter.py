# Copyright (c) Alibaba, Inc. and its affiliates.

import os
from typing import Any, Dict, List

from evalscope.api.benchmark import BenchmarkMeta, MultiChoiceAdapter
from evalscope.api.dataset import LocalDataLoader, Sample
from evalscope.api.registry import register_benchmark
from evalscope.constants import Tags
from evalscope.utils.logger import get_logger
from evalscope.utils.multi_choices import MultipleChoiceTemplate

logger = get_logger()

SUBSET_LIST = ['c3-m', 'c3-d']  # mixed-genre and dialogue


@register_benchmark(
    BenchmarkMeta(
        name='c3',
        pretty_name='C³',
        tags=[Tags.KNOWLEDGE, Tags.MULTIPLE_CHOICE, Tags.CHINESE, Tags.READING_COMPREHENSION],
        description=
        'C³ (C-Cube) is a free-form multiple-choice Chinese machine reading comprehension dataset. It includes both mixed-genre and dialogue formats.',
        dataset_id='',  # Will be set to local path
        subset_list=SUBSET_LIST,
        metric_list=['acc'],
        few_shot_num=0,
        train_split='train',
        eval_split='test',
        prompt_template=MultipleChoiceTemplate.CHINESE_SINGLE_ANSWER_TEMPLATE_COT,
    )
)
class C3Adapter(MultiChoiceAdapter):
    """
    Adapter for C³ (C-Cube) Chinese reading comprehension dataset.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def load(self):
        """
        Load C³ dataset from local JSON files.
        The dataset format is a JSON array where each item is:
        [document, questions, id]
        - document: list of strings (document paragraphs)
        - questions: list of dicts with 'question', 'choice', 'answer'
        - id: document id
        """
        dataset_name_or_path = self.dataset_id
        if not os.path.exists(dataset_name_or_path):
            raise FileNotFoundError(f'Dataset path does not exist: {dataset_name_or_path}')

        from evalscope.api.dataset import DatasetDict
        test_dataset = DatasetDict({})
        
        # Load all subsets (c3-m and c3-d)
        for subset in self.subset_list:
            # Construct file path
            # If dataset_name_or_path is a directory, look for files directly in it or in a 'data' subdirectory
            if os.path.isdir(dataset_name_or_path):
                # Try direct path first
                json_file = os.path.join(dataset_name_or_path, f'{subset}-{self.eval_split}.json')
                if not os.path.exists(json_file):
                    # Try in 'data' subdirectory
                    json_file = os.path.join(dataset_name_or_path, 'data', f'{subset}-{self.eval_split}.json')
            else:
                json_file = dataset_name_or_path
            
            if not os.path.exists(json_file):
                logger.warning(f'File not found: {json_file}, skipping subset {subset}')
                continue

            # Load JSON file
            import json
            with open(json_file, 'r', encoding='utf-8') as f:
                raw_data = json.load(f)

            # Convert to list of records
            records = []
            for item in raw_data:
                document = item[0]  # List of document paragraphs
                questions = item[1]  # List of questions
                doc_id = item[2]  # Document ID
                
                # Combine document paragraphs
                context = '\n'.join(document)
                
                # Create a record for each question
                for q_idx, q in enumerate(questions):
                    record = {
                        'id': f'{doc_id}_{q_idx}',
                        'context': context,
                        'question': q['question'],
                        'choices': q['choice'],
                        'answer': q['answer'],
                        'subset': subset,
                    }
                    records.append(record)

            # Use DictDataLoader to load from records
            from evalscope.api.dataset import DictDataLoader
            dataset = DictDataLoader(
                dict_list=records,
                sample_fields=self.record_to_sample,
                limit=self.limit,
                shuffle=self.shuffle,
            ).load()
            
            test_dataset[subset] = dataset

        return test_dataset, None

    def record_to_sample(self, record: Dict[str, Any]) -> Sample:
        """
        Convert a C³ record to a Sample object.
        
        Args:
            record: Dict with 'context', 'question', 'choices', 'answer'
            
        Returns:
            Sample: Sample object with formatted input and choices
        """
        context = record['context']
        question = record['question']
        choices = record['choices']
        answer_text = record['answer']  # Answer is the full text, not a letter

        # Find the index of the answer in choices
        answer_letter = 'A'  # Default
        for i, choice in enumerate(choices):
            if choice == answer_text:
                answer_letter = chr(65 + i)  # Convert index to letter (A, B, C, D)
                break

        # Format the input with context and question
        # Combine context and question into a single input string
        # The MultiChoiceAdapter will add choices formatting using {question} and {choices}
        input_text = f"""阅读以下文章，然后回答问题。

{context}

问题：{question}"""

        return Sample(
            input=input_text,
            choices=choices,
            target=answer_letter,  # Use letter instead of full text
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
            str: The extracted answer (A, B, C, or D)
        """
        import re
        
        # Try to find answer in format "答案：A" or "答案是A" or just "A"
        patterns = [
            r'答案[：:]\s*([A-D])',
            r'答案是\s*([A-D])',
            r'选择\s*([A-D])',
            r'\b([A-D])\b',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, prediction, re.IGNORECASE)
            if match:
                return match.group(1).upper()
        
        # If no match found, return the first character if it's A-D
        prediction = prediction.strip()
        if prediction and prediction[0].upper() in ['A', 'B', 'C', 'D']:
            return prediction[0].upper()
        
        logger.warning(f'No valid answer found in prediction: {prediction}')
        return ''

