"""
EQ-Bench 推理逻辑代码
从 lib/run_query.py 提取

这个模块负责运行模型推理，支持多种推理引擎：
- transformers: HuggingFace transformers 库
- openai: OpenAI API
- anthropic: Claude API
- mistralai: Mistral API
- gemini: Google Gemini API
- ooba: Oobabooga 服务器
- llama.cpp: llama.cpp 服务器
"""

from transformers import pipeline, StoppingCriteria, StoppingCriteriaList
import requests
import json
import yaml


class MyStoppingCriteria(StoppingCriteria):
    """自定义停止条件，用于在特定序列出现时停止生成"""
    def __init__(self, stopping_sequences, tokenizer):
        self.stopping_sequences = stopping_sequences
        self.tokenizer = tokenizer

    def __call__(self, input_ids, scores, **kwargs):
        # 获取生成的文本
        generated_text = self.tokenizer.decode(input_ids[0])
        # 检查目标序列是否出现在生成的文本中
        for seq in self.stopping_sequences:
            if seq in generated_text:
                return True  # 停止生成
        return False  # 继续生成


# 自定义停止标准（可根据需要配置）
STOPPING_CRITERIA = []


def run_pipeline_query(prompt, completion_tokens, model, tokenizer, temp):
    """
    使用 HuggingFace pipeline 进行推理

    Args:
        prompt: 输入提示词
        completion_tokens: 最大生成 token 数
        model: 加载的模型
        tokenizer: 分词器
        temp: 温度参数

    Returns:
        str: 模型生成的文本
    """
    if STOPPING_CRITERIA:
        print('Using custom stopping criteria:', STOPPING_CRITERIA)
        my_stopping_criteria = MyStoppingCriteria(STOPPING_CRITERIA, tokenizer)
        text_gen = pipeline(
            task="text-generation",
            model=model,
            tokenizer=tokenizer,
            do_sample=True,
            temperature=temp,
            max_new_tokens=completion_tokens,
            generation_kwargs={"stopping_criteria": StoppingCriteriaList([my_stopping_criteria])},
            min_p=0.1
        )
    else:
        text_gen = pipeline(
            task="text-generation",
            model=model,
            tokenizer=tokenizer,
            do_sample=True,
            temperature=temp,
            max_new_tokens=completion_tokens,
            min_p=0.1
        )

    output = text_gen(prompt)
    out_str = output[0]['generated_text']

    # 去除提示词部分
    if type(out_str) == str:
        trimmed_output = out_str[len(prompt):].strip()
    else:
        trimmed_output = out_str[-1]['content'].strip()

    if STOPPING_CRITERIA:
        for stop_str in STOPPING_CRITERIA:
            if stop_str in trimmed_output:
                trimmed_output = trimmed_output.split(stop_str)[0]

    return trimmed_output


def run_chat_template_query(prompt, completion_tokens, model, tokenizer, temp):
    """使用聊天模板进行推理"""
    chat = [
        {"role": "user", "content": prompt},
    ]
    prompt = tokenizer.apply_chat_template(chat, tokenize=False, add_generation_prompt=True)
    inputs = tokenizer.encode(prompt, add_special_tokens=True, return_tensors="pt")
    outputs = model.generate(
        input_ids=inputs.to(model.device),
        max_new_tokens=completion_tokens,
        temperature=temp,
        do_sample=True,
        min_p=0.1
    )
    output = tokenizer.decode(outputs[0], skip_special_tokens=True)
    # 去除提示词
    trimmed_output = output[len(prompt):].strip()
    return trimmed_output


def run_openai_query(prompt, history, completion_tokens, temp, model, openai_client):
    """
    使用 OpenAI API 进行推理

    Args:
        prompt: 输入提示词
        history: 对话历史
        completion_tokens: 最大生成 token 数
        temp: 温度参数
        model: 模型名称
        openai_client: OpenAI 客户端

    Returns:
        str: 模型生成的文本
    """
    response = None
    try:
        messages = history + [{"role": "user", "content": prompt}]

        # 判断是补全模型还是聊天模型
        if model in OPENAI_COMPLETION_MODELS and openai_client.base_url == 'https://api.openai.com/v1/':
            response = openai_client.completions.create(
                model=model,
                temperature=temp,
                max_tokens=completion_tokens,
                prompt=prompt,
            )
            content = response.choices[0].text
        else:  # 假设是聊天模型
            response = openai_client.chat.completions.create(
                model=model,
                temperature=temp,
                max_tokens=completion_tokens,
                messages=messages,
            )
            content = response.choices[0].message.content

        if content:
            return content.strip()
        else:
            print(response)
            print('Error: message is empty')

    except Exception as e:
        print(response)
        print("Request failed.")
        print(e)

    return None


def run_ooba_query(prompt, history, prompt_format, completion_tokens, temp,
                   ooba_instance, launch_ooba, ooba_request_timeout):
    """
    使用 Oobabooga 服务器进行推理

    Args:
        prompt: 输入提示词
        history: 对话历史
        prompt_format: 提示词格式
        completion_tokens: 最大生成 token 数
        temp: 温度参数
        ooba_instance: Oobabooga 实例
        launch_ooba: 是否自动启动 ooba
        ooba_request_timeout: 请求超时时间

    Returns:
        str: 模型生成的文本
    """
    if launch_ooba and (not ooba_instance or not ooba_instance.url):
        raise Exception("Error: Ooba api not initialised")

    if launch_ooba:
        ooba_url = ooba_instance.url
    else:
        ooba_url = "http://127.0.0.1:5000"

    try:
        messages = history + [{"role": "user", "content": prompt}]
        data = {
            "mode": "instruct",
            "messages": messages,
            "instruction_template": prompt_format,
            "max_tokens": completion_tokens,
            "temperature": temp,
            "min_p": 0.1,
            "user_bio": "",  # workaround for ooba bug
        }

        headers = {
            "Content-Type": "application/json"
        }

        try:
            response = requests.post(
                ooba_url + '/v1/chat/completions',
                headers=headers,
                json=data,
                verify=False,
                timeout=ooba_request_timeout
            )
            response = response.json()
        except Exception as e:
            print(e)
            # 如果 ooba api 停止响应，尝试重启
            if launch_ooba:
                print('! Request failed to Oobabooga api. Attempting to reload Ooba & model...')
                ooba_instance.restart()

        content = response['choices'][0]['message']['content']
        if content:
            return content.strip()
        else:
            print('Error: message is empty')
    except KeyboardInterrupt:
        print("Operation cancelled by user.")
        raise
    except Exception as e:
        print("Request failed.")
        print(e)

    return None


def parse_yaml(template_path):
    """解析 YAML 格式的提示词模板"""
    try:
        with open(template_path, 'r') as file:
            data = yaml.safe_load(file)
            # 如果数据是字符串，替换 \\n 为 \n
            if isinstance(data, str):
                data = data.replace('\\n', '\n')
            # 如果数据是字典，替换所有字符串值中的 \\n
            elif isinstance(data, dict):
                for key, value in data.items():
                    if isinstance(value, str):
                        data[key] = value.replace('\\n', '\n')
            return data
    except FileNotFoundError:
        raise FileNotFoundError(f"Template file not found: {template_path}")


def generate_prompt_from_template(prompt, prompt_type):
    """
    从模板生成格式化的提示词

    Args:
        prompt: 原始提示词内容
        prompt_type: 提示词模板类型（对应 instruction-templates/ 目录下的文件名）

    Returns:
        str: 格式化后的提示词
    """
    if not prompt_type:
        return prompt

    template_path = f"instruction-templates/{prompt_type}.yaml"
    template = parse_yaml(template_path)
    default_system_message = ""

    context = template["context"]
    if '<|system-message|>' in template['context']:
        if "system_message" in template and template["system_message"].strip():
            context = context.replace("<|system-message|>", template["system_message"])
        else:
            context = context.replace("<|system-message|>", default_system_message)

    turn_template = template["turn_template"].replace("<|user|>", template["user"]).replace("<|bot|>", template["bot"])
    formatted_prompt = context + turn_template
    formatted_prompt = formatted_prompt.split("<|bot-message|>")[0]
    return formatted_prompt.replace("<|user-message|>", prompt)


def run_query(model_path, prompt_format, prompt, history, completion_tokens,
              model, tokenizer, temp, inference_engine, ooba_instance,
              launch_ooba, ooba_request_timeout, openai_client, api_key=None):
    """
    统一的推理接口，根据指定的引擎调用相应的推理函数

    Args:
        model_path: 模型路径或名称
        prompt_format: 提示词格式
        prompt: 输入提示词
        history: 对话历史
        completion_tokens: 最大生成 token 数
        model: 加载的模型对象
        tokenizer: 分词器
        temp: 温度参数
        inference_engine: 推理引擎类型
        ooba_instance: Oobabooga 实例
        launch_ooba: 是否自动启动 ooba
        ooba_request_timeout: ooba 请求超时时间
        openai_client: OpenAI 客户端
        api_key: API 密钥

    Returns:
        str: 模型生成的文本
    """
    # 根据推理引擎类型调用相应的函数
    if inference_engine == 'openai':
        return run_openai_query(prompt, history, completion_tokens, temp, model_path, openai_client)
    elif inference_engine == 'ooba':
        return run_ooba_query(prompt, history, prompt_format, completion_tokens, temp,
                             ooba_instance, launch_ooba, ooba_request_timeout)
    else:  # transformers
        # 确定正确的推理方法
        inference_fn = run_pipeline_query  # 默认使用 pipeline

        if inference_fn in [run_chat_template_query]:
            formatted_prompt = prompt
        else:
            if prompt_format:
                formatted_prompt = generate_prompt_from_template(prompt, prompt_format)
            elif inference_fn == run_pipeline_query:
                # 如果没有指定提示词格式且使用 pipeline，使用消息字典格式
                # 这样 pipeline 会应用模型的编码聊天模板
                formatted_prompt = [
                    {"role": "user", "content": prompt},
                ]
            else:
                formatted_prompt = prompt

        return inference_fn(formatted_prompt, completion_tokens, model, tokenizer, temp)


# OpenAI 补全模型列表
OPENAI_COMPLETION_MODELS = [
    'text-davinci-003',
    'text-davinci-002',
    'text-davinci-001',
    'text-curie-001',
    'text-babbage-001',
    'text-ada-001',
    'davinci-instruct-beta',
    'davinci',
    'curie-instruct-beta',
    'curie',
    'babbage',
    'ada',
    'gpt-3.5-turbo-instruct-0914',
    'gpt-3.5-turbo-instruct',
    'babbage-002',
    'davinci-002'
]
