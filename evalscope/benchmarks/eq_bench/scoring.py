# Copyright (c) Alibaba, Inc. and its affiliates.
"""
EQ-Bench Scoring Module

This module implements the official EQ-Bench v2 scoring system.
Based on the reference implementation from EQ-Bench project.

References:
- Paper: https://arxiv.org/abs/2312.06281
- Homepage: https://eqbench.com
- GitHub: https://github.com/EQ-bench/EQ-Bench
"""

import math
import re
from typing import Dict, Optional, Tuple

from evalscope.utils.logger import get_logger

logger = get_logger()


def parse_answers(text: str, revise: bool = False) -> Tuple[Dict[str, str], Dict[str, str]]:
    """
    Parse emotion intensity scores from model output (English).

    Expected format:
    - Without revision: emotion1: score1\nemotionN: scoreN
    - With revision: First pass scores: ... Revised scores: ...

    Args:
        text: Model's raw output text
        revise: Whether revision mode is enabled

    Returns:
        tuple: (first_pass_answers, revised_answers) two dictionaries
    """
    first_pass_answers = {}
    revised_answers = {}

    # Remove markdown formatting
    text = text.replace('*', '').replace('#', '')

    if revise:
        # Extract first pass scores
        first_pass_match = re.search(r'First pass scores:(.*?)Revised scores:', text, re.DOTALL | re.IGNORECASE)
        if first_pass_match:
            first_pass_text = first_pass_match.group(1)
            first_pass_answers = dict(re.findall(r'(\w+):\s+(\d+)', first_pass_text))

        # Extract revised scores
        revised_match = re.search(r'Revised scores:(.*?)$', text, re.DOTALL | re.IGNORECASE)
        if revised_match:
            revised_text = revised_match.group(1)
            revised_answers = dict(re.findall(r'(\w+):\s+(\d+)', revised_text))
    else:
        # Extract all emotion:score pairs
        first_pass_answers = dict(re.findall(r'(\w+):\s+(\d+)', text))
        revised_answers = {}

    return first_pass_answers, revised_answers


def parse_answers_de(text: str, revise: bool = False) -> Tuple[Dict[str, str], Dict[str, str]]:
    """
    Parse emotion intensity scores from model output (German).

    Args:
        text: Model's raw output text
        revise: Whether revision mode is enabled

    Returns:
        tuple: (first_pass_answers, revised_answers) two dictionaries
    """
    first_pass_answers = {}
    revised_answers = {}

    # Remove markdown formatting
    text = text.replace('*', '').replace('#', '')

    first_pass_heading_pattern = r'(Erste.*?):\s*(.*?)(?=Überarbeitete|$)'
    revised_heading_pattern = r'(Überarbeitete.*?):\s*(.*)'

    if revise:
        first_pass_match = re.search(first_pass_heading_pattern, text, re.IGNORECASE | re.DOTALL)
        if first_pass_match:
            first_pass_text = first_pass_match.group(2)
            pairs = re.findall(r'([a-zA-ZäöüßÄÖÜ\s]+):\s*\**(\d+(?:,\d+)?)\**', first_pass_text)
            first_pass_answers = {label.strip(): score.replace('*', '') for label, score in pairs}

        revised_match = re.search(revised_heading_pattern, text, re.IGNORECASE | re.DOTALL)
        if revised_match:
            revised_text = revised_match.group(2)
            pairs = re.findall(r'([a-zA-ZäöüßÄÖÜ\s]+):\s*\**(\d+(?:,\d+)?)\**', revised_text)
            revised_answers = {label.strip(): score.replace('*', '') for label, score in pairs}
    else:
        pairs = re.findall(r'([a-zA-ZäöüßÄÖÜ\s]+):\s*\**(\d+(?:,\d+)?)\**', text)
        first_pass_answers = {label.strip(): score.replace('*', '') for label, score in pairs}
        revised_answers = {}

    return first_pass_answers, revised_answers


def calculate_score_fullscale(reference: Dict[str, any], user: Dict[str, str]) -> Optional[float]:
    """
    Calculate score using v2 full-scale scoring system.

    Scoring rules:
    1. Verify user provided 4 emotion scores, matching reference emotions
    2. Calculate difference between predicted and reference values for each emotion
    3. For differences <= 5, use sigmoid scaling function
    4. For differences > 5, use linear scaling
    5. Adjustment constant is set to make random answers score 0

    Args:
        reference: Reference answer dict containing emotion1-4 and corresponding _score
        user: User answer dict in format {emotion: score}

    Returns:
        float: Score for this question (0-10 range), or None if parsing failed
    """
    # First check if emotions match the reference
    if len(user.items()) != 4:
        logger.warning(f'Expected 4 emotions, got {len(user.items())}')
        return None

    emotions_dict = {}
    for emotion, user_emotion_score in user.items():
        for i in range(1, 5):
            emotion_key = f'emotion{i}'
            if emotion_key in reference:
                ref_emotion = reference[emotion_key]
                if emotion.lower() == str(ref_emotion).lower():
                    emotions_dict[emotion.lower()] = True

    if len(emotions_dict) != 4:
        logger.warning('Error: emotions did not match reference')
        logger.debug(f'User emotions: {user}')
        logger.debug(f'Reference emotions: {[reference.get(f"emotion{i}") for i in range(1, 5)]}')
        return None

    difference_tally = 0  # Cumulative difference from reference

    # Iterate through each emotion in user answer
    for emotion, user_emotion_score in user.items():
        # If this emotion is in the reference, calculate difference
        for i in range(1, 5):
            emotion_key = f'emotion{i}'
            emotion_score_key = f'emotion{i}_score'

            if emotion_key in reference and emotion_score_key in reference:
                ref_emotion = reference[emotion_key]
                if emotion.lower() == str(ref_emotion).lower():
                    try:
                        user_score = float(user_emotion_score)
                        ref_score = float(reference[emotion_score_key])
                        d = abs(user_score - ref_score)

                        # d ranges from 0 to 10
                        if d == 0:
                            scaled_difference = 0
                        elif d <= 5:
                            # Sigmoid scaling function
                            # https://www.desmos.com/calculator
                            # 6.5 * (1 / (1 + e^(-1.2*(x-4))))
                            scaled_difference = 6.5 * (1 / (1 + math.e ** (-1.2 * (d - 4))))
                        else:
                            scaled_difference = d

                        difference_tally += scaled_difference
                    except (ValueError, TypeError) as e:
                        logger.warning(f'Error converting scores to float: {e}')
                        return None

    # Invert difference tally so closer answers get higher scores
    # Adjustment constant chosen to make random answers score 0
    adjust_const = 0.7477
    final_score = 10 - (difference_tally * adjust_const)

    return final_score


def calculate_score(reference: Dict[str, any], user: Dict[str, str]) -> Optional[float]:
    """
    Calculate score using v1 normalized scoring system (legacy version).

    Scoring rules:
    1. Verify user provided 4 emotion scores, matching reference emotions
    2. Normalize user scores so they sum to 10
    3. Calculate absolute difference between normalized scores and reference
    4. Use fixed constant adjustment to make random answers score 0

    Note: v1 and v2 scores are not directly comparable.

    Args:
        reference: Reference answer dict
        user: User answer dict

    Returns:
        float: Score for this question, or None if parsing failed
    """
    # First check if emotions match the reference
    if len(user.items()) != 4:
        logger.warning(f'Error: 4 emotions were not returned, got {len(user.items())}')
        logger.debug(f'User emotions: {user}')
        return None

    emotions_dict = {}
    for emotion, user_emotion_score in user.items():
        for i in range(1, 5):
            emotion_key = f'emotion{i}'
            if emotion_key in reference:
                ref_emotion = reference[emotion_key]
                if emotion.lower() == str(ref_emotion).lower():
                    emotions_dict[emotion.lower()] = True

    if len(emotions_dict) != 4:
        logger.warning('Error: emotions did not match reference')
        logger.debug(f'User emotions: {user}')
        return None

    # Normalize user scores so they sum to 10
    try:
        total_user_score = sum(float(score) for score in user.values())
        if total_user_score <= 0:
            logger.warning('Error: total of scores must be > 0')
            logger.debug(f'User emotions: {user}')
            return None
        user = {emotion: float(score) / total_user_score * 10 for emotion, score in user.items()}
    except (ValueError, TypeError) as e:
        logger.warning(f'Error normalizing scores: {e}')
        return None

    difference_tally = 0  # Cumulative difference from reference

    # Iterate through each emotion in user answer
    for emotion, user_emotion_score in user.items():
        # If this emotion is in the reference, calculate difference
        for i in range(1, 5):
            emotion_key = f'emotion{i}'
            emotion_score_key = f'emotion{i}_score'

            if emotion_key in reference and emotion_score_key in reference:
                ref_emotion = reference[emotion_key]
                if emotion.lower() == str(ref_emotion).lower():
                    try:
                        ref_score = float(reference[emotion_score_key])
                        difference_tally += abs(user_emotion_score - ref_score)
                    except (ValueError, TypeError) as e:
                        logger.warning(f'Error calculating difference: {e}')
                        return None

    # Invert difference tally so closer answers get higher scores
    # Subtract from 10 because this constant makes random answers score 0
    final_score = 10 - difference_tally

    return final_score


def validate_answer_format(user_answers: Dict[str, str],
                          reference_emotions: list) -> Tuple[bool, str]:
    """
    Validate if user answer format is correct.

    Args:
        user_answers: User answer dict {emotion: score}
        reference_emotions: List of emotion names from reference

    Returns:
        tuple: (is_valid, error_message)
    """
    # Check if there are 4 emotions
    if len(user_answers) != 4:
        return False, f"Expected 4 emotions, got {len(user_answers)}"

    # Check if emotions match
    user_emotions = set(e.lower() for e in user_answers.keys())
    ref_emotions = set(e.lower() for e in reference_emotions)

    if user_emotions != ref_emotions:
        missing = ref_emotions - user_emotions
        extra = user_emotions - ref_emotions
        error_msg = ""
        if missing:
            error_msg += f"Missing emotions: {missing}. "
        if extra:
            error_msg += f"Extra emotions: {extra}."
        return False, error_msg

    # Check if scores are valid numbers
    try:
        for emotion, score in user_answers.items():
            score_float = float(score)
            if score_float < 0 or score_float > 10:
                return False, f"Score for {emotion} out of range (0-10): {score_float}"
    except (ValueError, TypeError):
        return False, f"Invalid score format: {user_answers}"

    return True, ""
