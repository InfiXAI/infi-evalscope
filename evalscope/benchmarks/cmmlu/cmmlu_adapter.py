# Copyright (c) Alibaba, Inc. and its affiliates.

import os
import csv
from typing import Any, Dict

from evalscope.api.benchmark import BenchmarkMeta, MultiChoiceAdapter
from evalscope.api.dataset import Sample, DatasetDict, DictDataLoader
from evalscope.api.registry import register_benchmark
from evalscope.constants import Tags
from evalscope.utils.logger import get_logger
from evalscope.utils.multi_choices import MultipleChoiceTemplate

# flake8: noqa

logger = get_logger()

SUBJECT_MAPPING = {
    'agronomy': ['other', 'Other'],
    'anatomy': ['biology', 'STEM'],
    'ancient_chinese': ['china specific', 'China specific'],
    'arts': ['arts', 'Humanities'],
    'astronomy': ['physics', 'STEM'],
    'business_ethics': ['business', 'Social Science'],
    'chinese_civil_service_exam': ['china specific', 'China specific'],
    'chinese_driving_rule': ['china specific', 'China specific'],
    'chinese_food_culture': ['china specific', 'China specific'],
    'chinese_foreign_policy': ['china specific', 'China specific'],
    'chinese_history': ['china specific', 'China specific'],
    'chinese_literature': ['china specific', 'China specific'],
    'chinese_teacher_qualification': ['china specific', 'China specific'],
    'college_actuarial_science': ['math', 'STEM'],
    'college_education': ['education', 'Social Science'],
    'college_engineering_hydrology': ['engineering', 'STEM'],
    'college_law': ['law', 'Humanities'],
    'college_mathematics': ['math', 'STEM'],
    'college_medical_statistics': ['statistics', 'STEM'],
    'clinical_knowledge': ['other', 'Other'],
    'college_medicine': ['other', 'Other'],
    'computer_science': ['computer science', 'STEM'],
    'computer_security': ['other', 'Other'],
    'conceptual_physics': ['physics', 'STEM'],
    'construction_project_management': ['china specific', 'China specific'],
    'economics': ['economics', 'Social Science'],
    'education': ['education', 'Social Science'],
    'elementary_chinese': ['china specific', 'China specific'],
    'elementary_commonsense': ['china specific', 'China specific'],
    'elementary_information_and_technology': ['other', 'Other'],
    'electrical_engineering': ['engineering', 'STEM'],
    'elementary_mathematics': ['math', 'STEM'],
    'ethnology': ['china specific', 'China specific'],
    'food_science': ['other', 'Other'],
    'genetics': ['biology', 'STEM'],
    'global_facts': ['global', 'Humanities'],
    'high_school_biology': ['biology', 'STEM'],
    'high_school_chemistry': ['chemistry', 'STEM'],
    'high_school_geography': ['geography', 'Social Science'],
    'high_school_mathematics': ['math', 'STEM'],
    'high_school_physics': ['physics', 'STEM'],
    'high_school_politics': ['china specific', 'China specific'],
    'human_sexuality': ['other', 'Other'],
    'international_law': ['law', 'Humanities'],
    'journalism': ['sociology', 'Social Science'],
    'jurisprudence': ['law', 'Humanities'],
    'legal_and_moral_basis': ['other', 'Other'],
    'logical': ['philosophy', 'Humanities'],
    'machine_learning': ['computer science', 'STEM'],
    'management': ['business', 'Social Science'],
    'marketing': ['business', 'Social Science'],
    'marxist_theory': ['philosophy', 'Humanities'],
    'modern_chinese': ['china specific', 'China specific'],
    'nutrition': ['other', 'Other'],
    'philosophy': ['philosophy', 'Humanities'],
    'professional_accounting': ['business', 'Social Science'],
    'professional_law': ['law', 'Humanities'],
    'professional_medicine': ['other', 'Other'],
    'professional_psychology': ['psychology', 'Social Science'],
    'public_relations': ['politics', 'Social Science'],
    'security_study': ['politics', 'Social Science'],
    'sociology': ['culture', 'Social Science'],
    'sports_science': ['other', 'Other'],
    'traditional_chinese_medicine': ['china specific', 'China specific'],
    'virology': ['biology', 'STEM'],
    'world_history': ['history', 'Humanities'],
    'world_religions': ['global', 'Humanities']
}


@register_benchmark(
    BenchmarkMeta(
        name='cmmlu',
        pretty_name='C-MMLU',
        tags=[Tags.KNOWLEDGE, Tags.MULTIPLE_CHOICE, Tags.CHINESE],
        description=
        'C-MMLU is a benchmark designed to evaluate the performance of AI models on Chinese language tasks, including reading comprehension, text classification, and more.',
        dataset_id='evalscope/cmmlu',
        metric_list=['acc'],
        subset_list=list(SUBJECT_MAPPING.keys()),
        few_shot_num=0,
        train_split=None,
        eval_split='test',
        prompt_template=MultipleChoiceTemplate.CHINESE_SINGLE_ANSWER_TEMPLATE_COT,
    )
)
class CMMLUAdapter(MultiChoiceAdapter):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.reformat_subset = True
        self.category_map = {k: v[-1] for k, v in SUBJECT_MAPPING.items()}

    def load(self):
        """
        Load C-MMLU dataset from local CSV files or remote source.
        For local loading, expects CSV files in structure:
        {dataset_id}/test/{subset}.csv
        """
        dataset_name_or_path = self.dataset_id
        
        # Check if this is a local path
        if os.path.exists(dataset_name_or_path) and os.path.isdir(dataset_name_or_path):
            # Local loading from CSV files
            return self._load_from_local_csv(dataset_name_or_path)
        else:
            # Remote loading (original behavior)
            return super().load()

    def _load_from_local_csv(self, dataset_path: str):
        """
        Load C-MMLU dataset from local CSV files.
        
        Args:
            dataset_path: Path to the dataset directory (should contain test/ and dev/ subdirectories)
            
        Returns:
            Tuple of (test_dataset, fewshot_dataset)
        """
        from evalscope.api.dataset import DatasetDict
        
        test_dataset = DatasetDict({})
        split_dir = os.path.join(dataset_path, self.eval_split)
        
        if not os.path.exists(split_dir):
            raise FileNotFoundError(
                f'Dataset split directory does not exist: {split_dir}. '
                f'Expected structure: {dataset_path}/test/ or {dataset_path}/dev/'
            )
        
        # Load all subsets from CSV files
        for subset in self.subset_list:
            csv_file = os.path.join(split_dir, f'{subset}.csv')
            
            if not os.path.exists(csv_file):
                logger.warning(f'CSV file not found for subset {subset}: {csv_file}, skipping')
                continue
            
            # Read CSV file
            records = []
            with open(csv_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # CSV format: ,Question,A,B,C,D,Answer
                    # Skip the first column (index)
                    question = row.get('Question', '').strip()
                    answer = row.get('Answer', '').strip()
                    
                    # Build choices list
                    choices = []
                    for choice_letter in ['A', 'B', 'C', 'D']:
                        choice_text = row.get(choice_letter, '').strip()
                        if choice_text:
                            choices.append(f'({choice_letter}) {choice_text}')
                    
                    if not question or not answer or len(choices) == 0:
                        logger.warning(f'Skipping invalid row in {csv_file}: {row}')
                        continue
                    
                    # Get category from mapping
                    category = self.category_map.get(subset, 'Other')
                    
                    record = {
                        'question': question,
                        'choices': choices,
                        'answer': answer,  # e.g., "B"
                        'category': category,
                        'subject': subset,
                    }
                    records.append(record)
            
            if not records:
                logger.warning(f'No valid records found in {csv_file}')
                continue
            
            # Use DictDataLoader to load from records
            dataset = DictDataLoader(
                dict_list=records,
                sample_fields=self.record_to_sample,
                limit=self.limit,
                shuffle=self.shuffle,
            ).load()
            
            test_dataset[subset] = dataset
        
        return test_dataset, None

    def record_to_sample(self, record) -> Sample:

        # choices: ["(A) 农业生产工具","(B) 土地","(C) 劳动力","(D) 资金"]
        # remove the leading (A), (B), (C), (D)
        raw_choices = record['choices']
        choice_list = [choice[3:].strip() for choice in raw_choices]

        return Sample(
            input=record['question'],
            choices=choice_list,
            target=record['answer'],  # answer is like "B" (already extracted from CSV)
            subset_key=record['category'],
            metadata={'subject': record.get('subject', '')},
        )
