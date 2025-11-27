# EQ-Bench 评测核心代码

这个目录包含从 EQ-Bench 项目中提取的核心推理和答案校验逻辑代码。

## 文件说明

### 1. inference_logic.py
**推理逻辑代码**

包含所有模型推理相关的函数，支持多种推理引擎：

- **Transformers 推理**
  - `run_pipeline_query()`: 使用 HuggingFace pipeline 进行推理（默认方法）
  - `run_chat_template_query()`: 使用聊天模板进行推理
  - 支持自定义停止条件 `MyStoppingCriteria`

- **API 推理**
  - `run_openai_query()`: OpenAI API 推理（支持补全和聊天模型）
  - `run_ooba_query()`: Oobabooga 服务器推理

- **提示词处理**
  - `parse_yaml()`: 解析 YAML 格式的提示词模板
  - `generate_prompt_from_template()`: 从模板生成格式化提示词
  - 支持自定义 instruction templates（位于 `instruction-templates/` 目录）

- **统一接口**
  - `run_query()`: 统一的推理接口，根据指定引擎自动调用相应函数

### 2. answer_validation.py
**答案校验和评分逻辑代码**

包含答案解析、验证和评分的所有函数：

- **答案解析**
  - `parse_answers()`: 解析英文输出的情感评分
  - `parse_answers_de()`: 解析德语输出的情感评分
  - 使用正则表达式提取 `emotion: score` 格式的数据

- **评分系统**
  - `calculate_score_fullscale()`: v2 全尺度评分（推荐）
    - 直接比较绝对情感强度（0-10）
    - 使用 S 形缩放函数处理小差异
    - 调整常数使随机回答得分为 0
  - `calculate_score()`: v1 归一化评分（遗留）
    - 归一化后只比较相对情感强度
    - v1 和 v2 得分不可直接比较

- **验证辅助**
  - `validate_answer_format()`: 验证答案格式是否正确
  - 检查情感数量、类型匹配和分数范围

### 3. question_processing.py
**问题处理流程代码**

包含处理单个问题的完整流程：

- **主函数**
  - `process_question()`: 处理单个 EQ-Bench 问题
    - 准备提示词
    - 调用推理
    - 解析输出
    - 计算得分
    - 存储结果
    - 处理重试

- **重试机制**
  - 初始温度：0.01（保证一致性）
  - 每次重试增加 0.15
  - 最多重试 n_question_attempts 次
  - 保存部分成功结果作为后备

- **辅助函数**
  - `remove_revision_instructions()`: 移除修订指令
  - `safe_dump()`: 安全保存 JSON 文件

## 核心工作流程

```
1. 加载问题数据
   ↓
2. 准备提示词（可选：应用 instruction template）
   ↓
3. 推理循环（最多 n 次尝试）
   ├─ 调用 run_query() 进行推理
   ├─ 解析输出 parse_answers()
   ├─ 计算得分 calculate_score_fullscale()
   └─ 成功 → 存储结果 / 失败 → 增加温度重试
   ↓
4. 保存结果到 raw_results.json
```

## v2 评分系统详解

### S 形缩放函数

对于预测值与参考值之间的差异 d：

- **d = 0**: scaled_difference = 0（完美匹配）
- **0 < d ≤ 5**: 使用 S 形函数
  ```
  scaled_difference = 6.5 / (1 + e^(-1.2*(d-4)))
  ```
- **d > 5**: scaled_difference = d（线性）

### 最终得分计算

```python
difference_tally = sum(scaled_difference for all 4 emotions)
final_score = 10 - (difference_tally * 0.7477)
```

调整常数 0.7477 确保随机回答得分为 0。

## 重要参数

### 推理参数
- `temp`: 温度参数（默认 0.01，重试时递增）
- `completion_tokens`: 最大生成 token 数
  - 不带修订：60
  - 带修订：600
- `min_p`: 0.1（用于 nucleus sampling）

### 评分参数
- `adjust_const`: 0.7477（v2 评分调整常数）
- `n_question_attempts`: 每个问题的最大尝试次数（默认 3）

## 答案格式要求

### 英文格式
```
Emotion1: 7
Emotion2: 3
Emotion3: 5
Emotion4: 8
```

### 带修订格式
```
First pass scores:
Emotion1: 7
Emotion2: 3
Emotion3: 5
Emotion4: 8

Revised scores:
Emotion1: 6
Emotion2: 4
Emotion3: 5
Emotion4: 9
```

## 使用示例

### 基本推理
```python
from inference_logic import run_query

# 使用 transformers
output = run_query(
    model_path="model_name",
    prompt_format="Alpaca",
    prompt="Your prompt here",
    history=[],
    completion_tokens=60,
    model=loaded_model,
    tokenizer=loaded_tokenizer,
    temp=0.01,
    inference_engine="transformers",
    ooba_instance=None,
    launch_ooba=False,
    ooba_request_timeout=300,
    openai_client=None
)
```

### 答案解析和评分
```python
from answer_validation import parse_answers, calculate_score_fullscale

# 解析答案
first_pass, revised = parse_answers(model_output, REVISE=False)

# 计算得分
score = calculate_score_fullscale(reference_answer, first_pass)
```

### 完整问题处理
```python
from question_processing import process_question

# 处理单个问题
results = process_question(
    question_id="q_001",
    q=question_data,
    model_path="model_name",
    prompt_type="Alpaca",
    model=loaded_model,
    tokenizer=loaded_tokenizer,
    results=results_dict,
    run_index="run_001",
    run_iter=1,
    verbose=True,
    n_question_attempts=3,
    inference_engine="transformers",
    ooba_instance=None,
    launch_ooba=False,
    ooba_request_timeout=300,
    openai_client=None,
    eqbench_version="v2",
    language="en",
    REVISE=False
)
```

## 依赖库

```python
# 核心依赖
import re                    # 正则表达式
import math                  # 数学函数（用于 S 形缩放）
import json                  # JSON 处理
import yaml                  # YAML 解析

# 推理引擎
from transformers import pipeline, StoppingCriteria
import requests             # HTTP 请求（API 调用）

# 可选依赖（根据使用的推理引擎）
import openai               # OpenAI API
import anthropic            # Claude API
import google.generativeai  # Gemini API
```

## 注意事项

1. **温度设置**：初始温度 0.01 很重要，保证结果一致性
2. **重试策略**：增加温度可能提高解析成功率，但会降低一致性
3. **评分版本**：v1 和 v2 得分不可直接比较
4. **语言支持**：目前支持英语（en）和德语（de）
5. **答案格式**：必须严格遵守 `emotion: score` 格式
6. **情感匹配**：必须返回与参考答案完全相同的 4 个情感类型

## 扩展性

### 添加新的推理引擎
在 `inference_logic.py` 的 `run_query()` 函数中添加新的分支：

```python
elif inference_engine == 'your_engine':
    return run_your_engine_query(...)
```

### 添加新的语言支持
在 `answer_validation.py` 中添加新的解析函数：

```python
def parse_answers_xx(text, REVISE):
    # 你的解析逻辑
    pass
```

然后在 `question_processing.py` 中添加语言判断：

```python
if language == "xx":
    first_pass_answers, revised_answers = parse_answers_xx(inference, REVISE)
```

## evalscope 集成指南

### Q1: 集成到 evalscope 时，是否需要参考 `inference_logic.py`？

**答：❌ 不需要**

**原因：**
- evalscope 应该有自己的统一模型推理接口
- 每个 benchmark 不应该各自实现推理逻辑
- 推理应该由 evalscope 的模型层统一处理

**结论：** 完全忽略 `inference_logic.py`，由 evalscope 负责调用模型

---

### Q2: 从 `answer_validation.py` 中需要提取哪些函数？

**必需函数（最小集合）：**
```python
from answer_validation import (
    parse_answers,              # 必需：解析英文模型输出
    calculate_score_fullscale   # 必需：v2 全尺度评分
)
```

**可选函数：**
- `parse_answers_de()` - 仅在支持德语时需要
- `calculate_score()` - 仅在支持 v1 评分时需要（不推荐）
- `validate_answer_format()` - evalscope 可能有自己的验证机制，可以不要

**建议：** 只提取最小集合的两个必需函数即可

---

### Q3: `question_processing.py` 中的重试和温度调整机制是否需要？

**答：❌ 不需要**

**原因：**
- evalscope 应该统一处理重试逻辑
- 温度参数应该由 evalscope 的配置控制，不在 benchmark 层调整
- benchmark 只负责评估结果，不负责控制推理参数

**可以参考的部分：**
```python
# 只参考核心评分流程（去掉推理和重试）
first_pass_answers, _ = parse_answers(model_output, REVISE=False)
score = calculate_score_fullscale(reference, first_pass_answers)
```

**建议：** 不要直接使用 `question_processing.py`，只参考其评分流程的核心逻辑

---

### Q4: 是否需要支持修订格式（REVISE）？

**答：❌ 不建议支持**

**修订格式的影响对比：**

| 特性 | 不带修订 (REVISE=False) | 带修订 (REVISE=True) |
|------|------------------------|---------------------|
| **completion_tokens** | 60 | 600 (10倍) |
| **输出格式** | 简单（4行） | 复杂（包含 critique） |
| **解析难度** | 低 | 高 |
| **推理成本** | 低 | 高（10倍） |
| **性能提升** | - | 仅 8% 问题有改善 |

**官方说明：**
> "After collecting a lot of data from v2, it's clear that the revision component has a mostly negative effect. Only 8% of the time does it improve the score, and on average the revised score is 2.95% lower than the first pass score."
>
> "Since v2.1, revision is off by default."

**建议：**
- ✅ **固定使用 `REVISE=False`**
- ✅ 这是官方推荐的默认方式
- ✅ 更简单、更快、成本更低
- ❌ 不需要在代码中支持修订格式

**代码实现：**
```python
# 在 evalscope 中固定使用 REVISE=False
def evaluate_single(self, model_output, reference):
    # 始终不使用修订格式
    first_pass, _ = parse_answers(model_output, REVISE=False)
    score = calculate_score_fullscale(reference, first_pass)
    return score
```

---

### Q5: v2 评分应该使用哪个参考答案字段？

**答：✅ 使用 `reference_answer_fullscale`**

**完整对应关系：**

| 评分版本 | 评分函数 | 参考答案字段 | 说明 |
|---------|---------|-------------|------|
| **v2 全尺度（推荐）** | `calculate_score_fullscale()` | `reference_answer_fullscale` | 绝对强度值（0-10） |
| v1 归一化（遗留） | `calculate_score()` | `reference_answer` | 归一化相对强度 |

**数据集中的两种参考答案示例：**

```json
{
    "1": {
        "prompt": "...",
        "reference_answer": {
            "emotion1": "Remorseful",
            "emotion1_score": 2,      // v1: 归一化值（总和=10）
            "emotion2_score": 3,
            "emotion3_score": 0,
            "emotion4_score": 5
        },
        "reference_answer_fullscale": {
            "emotion1": "Remorseful",
            "emotion1_score": 0,      // v2: 绝对强度值
            "emotion2_score": "6",    // 可以是字符串或数字
            "emotion3_score": 0,
            "emotion4_score": "7"
        }
    }
}
```

**关键区别：**
- `reference_answer`: 归一化后的相对强度，4个情感总和=10
- `reference_answer_fullscale`: 绝对强度值，总和可以是任意值

**正确的使用方式：**

```python
# ✅ v2 评分的完整流程
def evaluate_single(self, model_output, question_data):
    # 1. 获取 v2 参考答案
    reference = question_data['reference_answer_fullscale']

    # 2. 解析模型输出
    first_pass, _ = parse_answers(model_output, REVISE=False)

    # 3. 使用 v2 评分函数 + fullscale 参考答案
    score = calculate_score_fullscale(reference, first_pass)

    return score
```

**⚠️ 重要提醒：**
- v1 和 v2 的得分**不可直接比较**（来自不同的评分系统）
- evalscope 集成**只使用 v2**（官方推荐，排行榜使用）
- 不要混用评分函数和参考答案字段

**为什么 v2 更好：**
- 可以评估模型对绝对情感强度的判断能力
- 更好的区分度（使用 S 形缩放函数）
- 处理边界情况更准确
- 官方排行榜使用 v2 评分

---

### evalscope 集成最小代码示例

**需要提取的核心代码：**

```python
# scoring.py - 从 answer_validation.py 提取
import re
import math

def parse_answers(text, REVISE=False):
    """解析模型输出的情感评分"""
    first_pass_answers = {}
    text = text.replace('*', '').replace('#', '')

    if REVISE:
        # 通常不需要支持
        first_pass_match = re.search(r'First pass scores:(.*?)Revised scores:', text, re.DOTALL)
        if first_pass_match:
            first_pass_text = first_pass_match.group(1)
            first_pass_answers = dict(re.findall(r'(\w+):\s+(\d+)', first_pass_text))
    else:
        # 推荐：只支持不带修订的格式
        first_pass_answers = dict(re.findall(r'(\w+):\s+(\d+)', text))

    return first_pass_answers, {}

def calculate_score_fullscale(reference, user):
    """v2 全尺度评分"""
    if len(user.items()) != 4:
        return None

    emotions_dict = {}
    for emotion, user_emotion_score in user.items():
        for i in range(1, 5):
            if emotion.lower() == reference[f'emotion{i}'].lower():
                emotions_dict[emotion.lower()] = True

    if len(emotions_dict) != 4:
        return None

    difference_tally = 0
    for emotion, user_emotion_score in user.items():
        for i in range(1, 5):
            if emotion.lower() == reference[f'emotion{i}'].lower():
                d = abs(float(user_emotion_score) - float(reference[f'emotion{i}_score']))
                if d == 0:
                    scaled_difference = 0
                elif d <= 5:
                    scaled_difference = 6.5 * (1 / (1 + math.e ** (-1.2 * (d-4))))
                else:
                    scaled_difference = d
                difference_tally += scaled_difference

    adjust_const = 0.7477
    final_score = 10 - (difference_tally * adjust_const)
    return final_score
```

**evalscope 中的使用：**

```python
# eq_bench.py - 适配 evalscope 接口
import json
from .scoring import parse_answers, calculate_score_fullscale

class EQBench(Benchmark):
    def __init__(self, data_path):
        # 加载数据集
        with open(data_path, 'r', encoding='utf-8') as f:
            self.questions = json.load(f)

    def __len__(self):
        return len(self.questions)

    def __getitem__(self, idx):
        question_id = str(idx + 1)
        question = self.questions[question_id]
        return {
            'prompt': question['prompt'],
            'reference': question['reference_answer_fullscale']
        }

    def evaluate_single(self, model_output, reference):
        """评估单个样本"""
        # 解析模型输出（固定使用 REVISE=False）
        first_pass, _ = parse_answers(model_output, REVISE=False)

        # 计算得分
        score = calculate_score_fullscale(reference, first_pass)

        return {'score': score}

    def aggregate_results(self, results):
        """聚合结果"""
        scores = [r['score'] for r in results if r['score'] is not None]

        # EQ-Bench 最终得分 = 平均分 * 10（转换为 0-100 范围）
        avg_score = sum(scores) / len(scores)
        final_score = avg_score * 10

        return {
            'eq_bench_score': final_score,
            'num_valid': len(scores),
            'parseable_rate': len(scores) / len(results)
        }
```

---

### 集成检查清单

**必需文件：**
- ✅ 数据集：`data/eq_bench_v2_questions_171.json`
- ✅ 评分函数：`parse_answers()` 和 `calculate_score_fullscale()`
- ✅ 适配类：实现 evalscope 的 Benchmark 接口

**不需要的文件：**
- ❌ `inference_logic.py` - evalscope 负责推理
- ❌ `question_processing.py` - 不能直接使用

**关键配置：**
- ✅ `REVISE=False` - 固定不使用修订格式
- ✅ `completion_tokens=60` - 不带修订只需 60 tokens
- ✅ `temp=0.01` - 建议低温度保证一致性

---

## 参考资源

- [EQ-Bench 论文](https://arxiv.org/abs/2312.06281)
- [EQ-Bench 排行榜](https://eqbench.com)
- [项目 GitHub](https://github.com/EQ-bench/EQ-Bench)
