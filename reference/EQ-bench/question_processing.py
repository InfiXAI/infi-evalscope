"""
EQ-Bench 问题处理流程代码
从 lib/eq_bench_utils.py 提取

这个模块负责处理单个 EQ-Bench 问题的完整流程：
1. 准备问题提示词
2. 调用模型推理
3. 解析模型输出
4. 计算评分
5. 存储结果
6. 处理重试逻辑
"""

import json
from answer_validation import (
    parse_answers,
    parse_answers_de,
    calculate_score,
    calculate_score_fullscale
)
from inference_logic import run_query


def process_question(question_id, q, model_path, prompt_type, model, tokenizer,
                    results, run_index, run_iter, verbose, n_question_attempts,
                    inference_engine, ooba_instance, launch_ooba, ooba_request_timeout,
                    openai_client, eqbench_version, language, REVISE):
    """
    处理单个问题并更新结果

    工作流程：
    1. 从问题数据中提取提示词和参考答案
    2. 设置完成 token 数（带修订则更多）
    3. 可选：移除修订指令（v2 且不启用修订时）
    4. 循环尝试（最多 n_question_attempts 次）：
       a. 调用 run_query 进行推理
       b. 解析答案（根据语言选择解析函数）
       c. 计算得分（v1 或 v2 评分系统）
       d. 存储结果
       e. 如果失败，增加温度重试
    5. 如果所有尝试失败但有部分成功，使用部分结果

    Args:
        question_id: 问题 ID
        q: 问题数据字典，包含 'prompt' 和 'reference_answer'
        model_path: 模型路径
        prompt_type: 提示词类型
        model: 加载的模型
        tokenizer: 分词器
        results: 结果字典（将被更新）
        run_index: 当前运行索引
        run_iter: 当前迭代次数
        verbose: 是否输出详细信息
        n_question_attempts: 每个问题的尝试次数
        inference_engine: 推理引擎类型
        ooba_instance: Oobabooga 实例
        launch_ooba: 是否自动启动 ooba
        ooba_request_timeout: ooba 请求超时时间
        openai_client: OpenAI 客户端
        eqbench_version: EQ-Bench 版本 ('v1' 或 'v2')
        language: 语言代码 ('en' 或 'de')
        REVISE: 是否启用修订模式

    Returns:
        dict: 更新后的结果字典
    """
    # 从问题数据中提取提示词和参考答案
    prompt = q['prompt']
    ref = q['reference_answer']
    if 'reference_answer_fullscale' in q:
        ref_fullscale = q['reference_answer_fullscale']
    else:
        ref_fullscale = None

    # 设置完成 token 数
    COMPLETION_TOKENS = 60
    if REVISE:
        COMPLETION_TOKENS = 600

    # v2 版本且不启用修订时，移除修订指令
    if eqbench_version == 'v2' and not REVISE:
        prompt = remove_revision_instructions(prompt, language)

    # 重试逻辑
    tries = 0
    success = False
    temp = 0.01  # 低温度对结果一致性很重要
    prev_result = None  # 存储之前的部分成功结果
    prev_result_fullscale = None
    prev_result_inference = None
    prev_result_parsed_answers = None

    while tries < n_question_attempts and not success:
        # 调用推理函数
        inference = run_query(
            model_path, prompt_type, prompt, [], COMPLETION_TOKENS,
            model, tokenizer, temp, inference_engine, ooba_instance,
            launch_ooba, ooba_request_timeout, openai_client
        )

        try:
            if verbose:
                print('\n' + inference)
                print('________________')

            # 解析并计算该问题的得分
            if language == "de":
                first_pass_answers, revised_answers = parse_answers_de(inference, REVISE)
            else:
                first_pass_answers, revised_answers = parse_answers(inference, REVISE)

            parsed_answers = {
                'first_pass': first_pass_answers,
                'revised': revised_answers
            }

            # 计算首次评分
            first_pass_score = calculate_score(ref, first_pass_answers)
            if REVISE:
                revised_score = calculate_score(ref, revised_answers)
            else:
                revised_score = None

            this_result = {
                'first_pass_score': first_pass_score,
                'revised_score': revised_score
            }

            # 如果有 v2 参考答案，计算全尺度得分
            if ref_fullscale:
                first_pass_score_fullscale = calculate_score_fullscale(ref_fullscale, first_pass_answers)
                if REVISE:
                    revised_score_fullscale = calculate_score_fullscale(ref_fullscale, revised_answers)
                else:
                    revised_score_fullscale = None

                this_result_fullscale = {
                    'first_pass_score': first_pass_score_fullscale,
                    'revised_score': revised_score_fullscale
                }
            else:
                this_result_fullscale = {
                    'first_pass_score': None,
                    'revised_score': None
                }

            # 检查得分是否成功解析和计算
            if first_pass_score == None or (REVISE and revised_score == None):
                if REVISE:
                    # 如果有部分结果，保存下来作为后备
                    if not prev_result and (first_pass_score != None or revised_score != None):
                        prev_result = dict(this_result)
                        prev_result_fullscale = dict(this_result_fullscale)
                        prev_result_inference = inference
                        prev_result_parsed_answers = dict(parsed_answers)
                raise Exception("Failed to parse scores")

            # 存储到结果字典
            results[run_index]['iterations'][run_iter]['respondent_answers'][question_id] = parsed_answers
            results[run_index]['iterations'][run_iter]['individual_scores'][question_id] = this_result
            results[run_index]['iterations'][run_iter]['individual_scores_fullscale'][question_id] = this_result_fullscale
            results[run_index]['iterations'][run_iter]['raw_inference'][question_id] = inference

            if verbose:
                if eqbench_version == 'v1':
                    print('first pass:', round(first_pass_score, 1))
                    if REVISE:
                        print('revised:', round(revised_score, 1))
                elif eqbench_version == 'v2':
                    if ref_fullscale:
                        print('first pass:', round(first_pass_score_fullscale, 1))
                        if REVISE:
                            print('revised:', round(revised_score_fullscale, 1))

            success = True

        except KeyboardInterrupt:
            raise  # 重新抛出 KeyboardInterrupt 异常
        except Exception as e:
            print(e)
            tries += 1

            # 重试前增加温度，以期获得可解析的结果
            temp += 0.15

            if tries < n_question_attempts:
                print('Retrying...')
            elif prev_result:
                # 用完所有重试次数，但有部分结果，将其存储到结果字典
                results[run_index]['iterations'][run_iter]['respondent_answers'][question_id] = prev_result_parsed_answers
                results[run_index]['iterations'][run_iter]['individual_scores'][question_id] = prev_result
                results[run_index]['iterations'][run_iter]['individual_scores_fullscale'][question_id] = prev_result_fullscale
                results[run_index]['iterations'][run_iter]['raw_inference'][question_id] = prev_result_inference

    # 保存结果到文件
    safe_dump(results, RAW_RESULTS_PATH)


def remove_revision_instructions(prompt, language):
    """
    从提示词中移除修订指令部分

    当使用 v2 版本且不启用修订时调用此函数，
    简化提示词以提高效率。

    Args:
        prompt: 原始提示词
        language: 语言代码 ('en' 或 'de')

    Returns:
        str: 移除修订指令后的提示词
    """
    # 移除要求修订答案的部分
    if language == 'en':
        prompt = prompt.replace(' Then critique your answer by thinking it through step by step. Finally, give your revised scores.', '')
        prompt = prompt.replace('First pass scores:\n', '')
        prompt = prompt[:prompt.find('Critique: <your critique here>')] + '\n' + prompt[prompt.find('[End of answer]'):]
        prompt += '\nYour answer:\n'
    elif language == 'de':
        # 德语翻译有一些变体需要处理
        substring_to_match = "Geben Sie jeder dieser möglichen Emotionen"
        replacement_string = "Geben Sie jeder dieser möglichen Emotionen eine Punktzahl von 0-10 für die relative Intensität, die sie wahrscheinlich fühlen werden."
        start_index = prompt.find(substring_to_match)
        end_index = prompt.find('\n', start_index)
        prompt = prompt[:start_index] + replacement_string + prompt[end_index:]
        prompt = prompt.replace('Erste Bewertung:\n', '')
        prompt = prompt[:prompt.find('Kritik: <Ihre Kritik hier>')] + '\n' + prompt[prompt.find('[Ende der Antwort]'):]
        prompt += '\nIhre Antwort:\n'
    return prompt


def safe_dump(data, filepath, max_retries=3):
    """
    安全地将数据保存到 JSON 文件

    Args:
        data: 要保存的数据
        filepath: 文件路径
        max_retries: 最大重试次数
    """
    for attempt in range(max_retries):
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return
        except Exception as e:
            print(f"Error saving file (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt == max_retries - 1:
                raise


# 常量
RAW_RESULTS_PATH = './raw_results.json'


# 重试策略说明
RETRY_STRATEGY_INFO = """
重试策略：

1. 初始温度：0.01（低温度保证一致性）
2. 每次重试增加温度：+0.15
3. 最大重试次数：n_question_attempts（默认 3）
4. 部分成功处理：如果启用修订模式，会保存部分成功的结果
5. 失败处理：所有重试失败后，如果有部分结果则使用部分结果

温度递增的原因：
- 低温度可能导致模型输出格式过于固定，解析失败
- 增加温度可能产生更多样化的输出格式，提高解析成功率
- 但温度过高会影响结果的一致性

建议：
- 对于格式严格的模型，可以考虑减少重试次数
- 对于输出格式不稳定的模型，可以增加重试次数
"""
