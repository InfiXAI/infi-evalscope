# Copyright (c) Alibaba, Inc. and its affiliates.

import ast
import json
from functools import partial
from typing import Any, Dict, Optional, Tuple

from evalscope.api.benchmark import BenchmarkMeta, DefaultDataAdapter
from evalscope.api.dataset import DatasetDict, Sample
from evalscope.api.dataset.loader import LocalDataLoader
from evalscope.api.evaluator import TaskState
from evalscope.api.metric import Score
from evalscope.api.registry import register_benchmark
from evalscope.constants import Tags
from evalscope.utils.logger import get_logger

logger = get_logger()

PROMPT_TEMPLATE = """{question}"""


@register_benchmark(
    BenchmarkMeta(
        name='eq_bench',
        pretty_name='EQ-Bench',
        tags=[Tags.REASONING, Tags.QA],
        description=
        'EQ-Bench is a benchmark for evaluating language models on emotional intelligence tasks. '
        'It assesses the ability to predict the likely emotional responses of characters in dialogues '
        'by rating the intensity of possible emotional responses. '
        '[Paper](https://arxiv.org/abs/2312.06281) | [Homepage](https://eqbench.com/)',
        dataset_id='datasets/EQ-bench',  # Local dataset path
        subset_list=['main'],
        metric_list=['correlation', 'mae'],  # Mean Absolute Error and Correlation
        few_shot_num=0,
        train_split=None,
        eval_split='validation',  # Will look for main_validation.csv or validation.csv
        prompt_template=PROMPT_TEMPLATE,
    )
)
class EQBenchAdapter(DefaultDataAdapter):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
    
    def load_from_disk(self, use_local_loader: bool = True) -> Tuple[DatasetDict, Optional[DatasetDict]]:
        """
        Override to force use LocalDataLoader for CSV files.
        """
        test_dataset = None
        fewshot_dataset = None
        
        # Use LocalDataLoader for CSV file loading
        test_load_func = partial(self.load_subset, data_loader=LocalDataLoader)
        test_dataset = self.load_subsets(test_load_func)
        
        # Load few-shot examples if few-shot prompting is enabled
        if self._should_load_fewshot():
            fewshot_load_func = partial(self.load_fewshot_subset, data_loader=LocalDataLoader)
            fewshot_dataset = self.load_subsets(fewshot_load_func, is_fewshot=True)
        
        return test_dataset, fewshot_dataset
    
    def format_prompt_template(self, sample: Sample) -> str:
        """
        Override to use 'prompt' field from sample input directly.
        Since the prompt field already contains the full formatted prompt,
        we can return it directly or format with the template.
        """
        # The sample.input is already the full prompt text, so we can use it directly
        if isinstance(sample.input, str):
            return sample.input
        # If it's a list of messages, convert to string
        return str(sample.input)

    def record_to_sample(self, record: Dict[str, Any]) -> Sample:
        """
        Convert a data record to a Sample object.
        
        Args:
            record: Dictionary containing 'prompt', 'reference_answer', 'reference_answer_fullscale'
            
        Returns:
            Sample object with prompt as input and reference_answer as target
        """
        prompt = record.get('prompt', '').strip()
        reference_answer = record.get('reference_answer', '')
        reference_answer_fullscale = record.get('reference_answer_fullscale', '')
        
        # Parse the reference answer dictionaries
        # CSV files typically use Python dict format (single quotes), not JSON
        try:
            if isinstance(reference_answer, str):
                # Remove outer quotes if present (CSV may wrap the dict string in quotes)
                ref_str = reference_answer.strip()
                if ref_str.startswith('"') and ref_str.endswith('"'):
                    ref_str = ref_str[1:-1]
                elif ref_str.startswith("'") and ref_str.endswith("'"):
                    ref_str = ref_str[1:-1]
                
                # Try ast.literal_eval first (for Python dict format)
                try:
                    ref_answer_dict = ast.literal_eval(ref_str)
                except (ValueError, SyntaxError):
                    # Fallback to JSON if literal_eval fails
                    ref_answer_dict = json.loads(ref_str)
            else:
                ref_answer_dict = reference_answer
                
            if isinstance(reference_answer_fullscale, str):
                ref_str = reference_answer_fullscale.strip()
                if ref_str.startswith('"') and ref_str.endswith('"'):
                    ref_str = ref_str[1:-1]
                elif ref_str.startswith("'") and ref_str.endswith("'"):
                    ref_str = ref_str[1:-1]
                    
                try:
                    ref_fullscale_dict = ast.literal_eval(ref_str)
                except (ValueError, SyntaxError):
                    ref_fullscale_dict = json.loads(ref_str)
            else:
                ref_fullscale_dict = reference_answer_fullscale
        except (json.JSONDecodeError, ValueError, SyntaxError) as e:
            logger.warning(f'Failed to parse reference answer: {e}')
            ref_answer_dict = {}
            ref_fullscale_dict = {}
        
        return Sample(
            input=prompt,
            target=str(reference_answer),  # Store as string for comparison
            metadata={
                'reference_answer': ref_answer_dict,
                'reference_answer_fullscale': ref_fullscale_dict,
            }
        )

    def match_score(
        self, original_prediction: str, filtered_prediction: str, reference: str, task_state: TaskState
    ) -> Score:
        """
        Calculate evaluation scores by comparing prediction with reference.
        
        EQ-Bench evaluates based on correlation and mean absolute error between
        predicted emotion scores and reference scores.
        """
        import numpy as np
        
        score = Score(
            extracted_prediction=filtered_prediction,
            prediction=original_prediction,
        )
        
        try:
            # Get reference answer from metadata
            ref_answer = task_state.metadata.get('reference_answer', {})
            
            # Try to parse the prediction
            # Model output format is typically: "EmotionName: score\nEmotionName: score..."
            import re
            pred_dict = {}
            
            try:
                if isinstance(filtered_prediction, str):
                    # Try JSON/dict format first
                    if filtered_prediction.strip().startswith('{'):
                        try:
                            pred_dict = json.loads(filtered_prediction)
                        except json.JSONDecodeError:
                            pred_dict = ast.literal_eval(filtered_prediction)
                    else:
                        # Parse format like "EmotionName: score" or "EmotionName: score\n..."
                        # Extract emotion names and scores from the text
                        lines = filtered_prediction.strip().split('\n')
                        for line in lines:
                            line = line.strip()
                            if ':' in line:
                                # Match pattern like "EmotionName: score" or "EmotionName: score  "
                                match = re.match(r'^([^:]+):\s*(\d+)', line, re.IGNORECASE)
                                if match:
                                    emotion_name = match.group(1).strip()
                                    emotion_score = int(match.group(2))
                                    pred_dict[emotion_name] = emotion_score
                else:
                    pred_dict = filtered_prediction
            except (json.JSONDecodeError, ValueError, SyntaxError) as e:
                logger.warning(f'Failed to parse prediction: {e}')
                pred_dict = {}
            
            # Extract emotion scores for comparison
            # Reference format: {'emotion1': 'Remorseful', 'emotion1_score': 2, ...}
            # Need to map emotion names to scores
            ref_scores = []
            pred_scores = []
            
            for i in range(1, 5):
                emotion_name_key = f'emotion{i}'
                emotion_score_key = f'emotion{i}_score'
                
                if emotion_score_key in ref_answer:
                    ref_score = ref_answer[emotion_score_key]
                    # Convert to int if it's a string
                    if isinstance(ref_score, str):
                        ref_score = int(ref_score)
                    ref_scores.append(ref_score)
                    
                    # Get emotion name from reference
                    emotion_name = ref_answer.get(emotion_name_key, '').strip()
                    
                    # Try to find corresponding prediction score
                    # First try direct key match (emotion1_score)
                    pred_score = pred_dict.get(emotion_score_key)
                    if pred_score is None:
                        # Try emotion name match (case-insensitive)
                        for key, value in pred_dict.items():
                            if isinstance(key, str) and key.lower() == emotion_name.lower():
                                pred_score = value
                                break
                    
                    # If still not found, default to 0
                    if pred_score is None:
                        pred_score = 0
                    
                    # Convert to int if needed
                    if isinstance(pred_score, str):
                        pred_score = int(pred_score)
                    
                    pred_scores.append(pred_score)
            
            if len(ref_scores) > 0 and len(pred_scores) > 0:
                # Calculate Mean Absolute Error
                mae = np.mean(np.abs(np.array(ref_scores) - np.array(pred_scores)))
                
                # Calculate Pearson correlation
                if len(ref_scores) > 1:
                    correlation = np.corrcoef(ref_scores, pred_scores)[0, 1]
                    if np.isnan(correlation):
                        correlation = 0.0
                else:
                    correlation = 1.0 if ref_scores[0] == pred_scores[0] else 0.0
                
                score.value = {
                    'mae': float(mae),
                    'correlation': float(correlation),
                }
                score.main_score_name = 'correlation'
                score.explanation = f'MAE: {mae:.3f}, Correlation: {correlation:.3f}'
            else:
                score.value = {'mae': float('inf'), 'correlation': 0.0}
                score.explanation = 'Failed to extract emotion scores from prediction'
                
        except Exception as e:
            logger.error(f'Error calculating EQ-Bench metrics: {e}')
            score.value = {'mae': float('inf'), 'correlation': 0.0}
            score.explanation = f'Evaluation error: {str(e)}'
        
        return score

