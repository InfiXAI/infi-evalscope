# 👍 Contribute Benchmark

EvalScope, as the official evaluation tool of [ModelScope](https://modelscope.cn), is continuously optimizing its benchmark evaluation features! We invite you to refer to this tutorial to easily add your own benchmark and share your contributions with the community. Let's work together to enhance EvalScope and make our tool even better!

Below, we will introduce how to add two types of benchmark evaluations: **General Text Reasoning** and **Multiple Choice**, which mainly include three steps: uploading the dataset, registering the dataset, and writing the evaluation task.

## Basic Concepts

```{tip}
You can skip this section and start directly from [Preparing Benchmark Evaluation Dataset](#1-preparing-benchmark-evaluation-dataset). Refer back to the specific implementation when encountering code you don't understand.
```

The evaluation process of EvalScope mainly includes the following steps:
1. **Data Preparation**: Load and preprocess the dataset through `DataAdapter`.
2. **Task Definition**: Define the configuration of the evaluation task through `TaskConfig`, including models, datasets, evaluation metrics, etc.
3. **Evaluation Execution**: Execute the evaluation task through the `run_task` function and output the evaluation results.

Among them, `DataAdapter` is the core component of benchmark evaluation that we need to focus on.

### DataAdapter Architecture and Call Flow

DataAdapter adopts a Pipeline architecture, supporting custom behavior through hook methods. Taking `DefaultDataAdapter` as an example, the complete evaluation process is as follows:

```
1. Data Loading Phase
   load_dataset() 
   ├── load() 
   │   ├── load_from_remote() / load_from_disk()
   │   │   ├── load_subsets()
   │   │   │   └── load_subset() / load_fewshot_subset()
   │   │   │       └── record_to_sample() [User Implementation]
   │   │   └── _post_process_samples()
   │   │       └── process_sample_input()
   │   │           ├── sample_to_fewshot() [User Implementation]
   │   │           ├── format_fewshot_template() [Optional User Implementation]
   │   │           └── format_prompt_template() [Optional User Implementation]
   │   └── Returns DatasetDict

2. Model Inference Phase (Per Sample)
   run_inference()
   ├── _on_inference_start() [Hook Method]
   ├── _on_inference() [Hook Method]
   └── _on_inference_end() [Hook Method]
       └── Returns TaskState

3. Metric Calculation Phase (Per Sample)
   calculate_metrics()
   ├── filter_prediction()
   │   └── extract_answer() [Optional User Implementation]
   ├── match_score() / llm_match_score()
   └── Returns SampleScore

4. Result Aggregation Phase
   aggregate_scores()
   └── Returns List[AggScore]

5. Report Generation Phase
   generate_report()
   ├── _on_generate_report() [Hook Method]
   └── _on_generate_report_end() [Hook Method]
       └── Returns Report
```

### Core Data Structures

#### 1. Sample Object
Represents a single evaluation sample, including input, target answer, and metadata:

```python
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional, Union
from evalscope.api.messages import ChatMessage
from evalscope.api.tool import ToolInfo

class Sample(BaseModel):
    """Sample for an evaluation task."""
    
    input: Union[str, List[ChatMessage]]
    """The input to be submitted to the model."""
    
    target: Union[str, List[str]] = ''
    """Ideal target output. May be a literal value or narrative text."""
    
    choices: Optional[List[str]] = None
    """List of available answer choices (used only for multiple-choice evals)."""
    
    id: Optional[int] = None
    """Unique identifier for sample."""
    
    group_id: Optional[int] = None
    """Identifier for the group this sample belongs to."""
    
    subset_key: Optional[str] = None
    """Key for the subset this sample belongs to, used for generating subsets."""
    
    metadata: Dict[str, Any] = Field(default_factory=dict)
    """Arbitrary metadata associated with the sample."""
    
    tools: Optional[List[ToolInfo]] = None
    """List of tools available to the model during inference."""
    
    sandbox: Optional[str] = None
    """Sandbox environment type and optional config file."""
    
    files: Optional[Dict[str, str]] = None
    """Files that go along with the sample (copied to SandboxEnvironment)."""
    
    setup: Optional[str] = None
    """Setup script to run for sample (run within default SandboxEnvironment)."""
```

**Note**: `Sample` uses Pydantic `BaseModel`, not Python's `@dataclass`. This provides better validation and serialization capabilities.

#### 2. TaskState Object
Represents the complete state of a single inference task:

```python
class TaskState:
    """The internal state of the Task being run for a single Sample."""
    
    def __init__(
        self,
        model: str,
        sample: Sample,
        messages: List[ChatMessage] = [],
        output: Optional[ModelOutput] = None,
        completed: bool = False,
    ):
        # Properties are accessed via @property decorators
        pass
    
    # Properties (accessed via dot notation)
    model: str                    # Model name
    sample: Sample               # Input sample
    messages: List[ChatMessage]  # Chat message history
    output: ModelOutput          # Model raw output
    completed: bool              # Whether the task is completed
    sample_id: int                # Sample ID (property, not Optional)
    group_id: int                 # Group ID (property, not Optional)
    metadata: Dict[str, Any]      # Task metadata (from sample.metadata)
    target: str                    # The scoring target for this Sample
    choices: Choices               # Choices for the sample, if applicable
```

**Note**: `TaskState` is a regular class with properties, not a dataclass. Access fields using dot notation (e.g., `task_state.model`, `task_state.sample_id`).

#### 3. ModelOutput Object
Represents the raw output of the model:

```python
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any

class ModelOutput(BaseModel):
    """Output from model generation."""
    
    model: str = Field(default_factory=str)
    """Model used for generation."""
    
    choices: List[ChatCompletionChoice] = Field(default=[])
    """Completion choices."""
    
    usage: Optional[ModelUsage] = Field(default=None)
    """Model token usage."""
    
    time: Optional[float] = Field(default=None)
    """Time elapsed (in seconds) for call to generate."""
    
    metadata: Optional[Dict[str, Any]] = Field(default=None)
    """Additional metadata associated with model output."""
    
    error: Optional[str] = Field(default=None)
    """Error message in the case of content moderation refusals."""
    
    # Properties (not fields)
    @property
    def completion(self) -> str:
        """Text of first message choice text."""
        ...
    
    @property
    def message(self) -> ChatMessageAssistant:
        """First message choice."""
        ...
```

**Note**: `ModelOutput` uses Pydantic `BaseModel`. `completion` and `message` are properties, not direct fields.

#### 4. Score Object
Represents the scoring result of a single sample:

```python
from pydantic import BaseModel, Field
from typing import Dict, Optional, Union

Value = Dict[str, Union[int, float, bool]]

class Score(BaseModel):
    """Score generated by a scorer."""
    
    value: Value = Field(default_factory=dict)
    """Score value as a dictionary. Key is the score name, value is the score value."""
    
    extracted_prediction: Optional[str] = Field(default=None)
    """Answer extracted from model output (optional)."""
    
    prediction: Optional[str] = Field(default=None)
    """Original prediction text from the model (optional)."""
    
    explanation: Optional[str] = Field(default=None)
    """Explanation of score (optional)."""
    
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)
    """Additional metadata related to the score."""
    
    main_score_name: Optional[str] = Field(default=None)
    """Main score name, if applicable."""
```

**Note**: `Score` uses Pydantic `BaseModel`. All fields except `value` are optional. The `value` dictionary can contain `int`, `float`, or `bool` types.

#### 5. SampleScore Object
Encapsulates the complete scoring information of a single sample:

```python
from pydantic import BaseModel, Field
from typing import Dict, Optional, Union

class SampleScore(BaseModel):
    """Score for a Sample."""
    
    score: Score
    """A score."""
    
    sample_id: Optional[Union[str, int]] = Field(default=None)
    """A sample id."""
    
    group_id: Optional[Union[str, int]] = Field(default=None)
    """A group id for the sample, used for grouping k repeated samples."""
    
    sample_metadata: Optional[Dict[str, Any]] = Field(default=None)
    """Metadata from the sample."""
```

**Note**: `SampleScore` uses Pydantic `BaseModel`. `sample_id` and `group_id` can be either `str` or `int`.

#### 6. AggScore Object
Represents aggregated scoring statistics:

```python
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Union

class AggScore(BaseModel):
    """Output of an aggregation operation."""
    
    score: float = Field(default=0.0)
    """Aggregated value as a float."""
    
    metric_name: str = Field(default='')
    """Name of the metric being aggregated."""
    
    aggregation_name: str = Field(default='')
    """Name of the aggregation methods."""
    
    num: int = Field(default=0)
    """Number of samples used in the aggregation."""
    
    ids: Optional[List[Union[str, int]]] = Field(default=None)
    """List of sample IDs used in the aggregation, if applicable."""
    
    metadata: Optional[Dict[str, Any]] = Field(default=None)
    """Additional metadata related to the aggregation."""
```

**Note**: `AggScore` uses Pydantic `BaseModel`. Field names differ from what might be expected: use `metric_name` (not `metric`), `score` (not `value`), `aggregation_name` (not `agg_method`), and `num` (not `num_samples`). There is no `subset` field.

#### 7. DatasetDict Object
Manages multiple dataset subsets:

```python
class DatasetDict(dict):
    """Dataset dictionary, keys are subset names, values are Dataset objects"""
    
    @classmethod
    def from_dataset(cls, dataset, subset_list=None, limit=None, repeats=1):
        """Create a multi-subset dataset dictionary from a single dataset"""
        pass
```

### Core Methods of DataAdapter

Based on the above call flow, here are the key methods that need to be implemented by the user or can be optionally overridden:

#### Methods That Must Be Implemented

1. **`record_to_sample(record: Dict[str, Any]) -> Union[Sample, List[Sample]]`**
   - **Purpose**: Convert raw data records into standard Sample objects
   - **Input**: Raw record dictionary from the dataset
   - **Output**: Standardized Sample object or a list of Sample objects (for cases where one record maps to multiple samples)
   - **Example**:
   ```python
   def record_to_sample(self, record: Dict[str, Any]) -> Sample:
       return Sample(
           input=record['question'],
           target=record['answer'],
           metadata={'reasoning': record.get('explanation', '')}
       )
   ```
   
   **Note**: The method can return either a single `Sample` or a `List[Sample]` to handle cases where one data record corresponds to multiple evaluation samples.

#### Methods That Can Be Optionally Implemented

2. **`sample_to_fewshot(sample: Sample) -> str`**
   - **Purpose**: Convert sample into a few-shot example string
   - **Input**: Sample object
   - **Output**: Formatted few-shot example text
   - **Call Timing**: When constructing few-shot prompts

3. **`extract_answer(prediction: str, task_state: TaskState) -> str`**
   - **Purpose**: Extract the final answer from the model's raw output
   - **Input**: Model prediction text and task state
   - **Output**: Extracted answer string
   - **Call Timing**: Before calculating metrics for answer cleaning

4. **`format_prompt_template(sample: Sample) -> str`**
   - **Purpose**: Format the basic prompt template
   - **Input**: Sample object
   - **Output**: Formatted prompt text
   - **Default Implementation**: Uses `prompt_template.format(question=sample.input)`

5. **`format_fewshot_template(fewshot: str, sample: Sample) -> str`**
   - **Purpose**: Format the prompt template containing few-shot examples
   - **Input**: Few-shot example string and Sample object
   - **Output**: Complete few-shot prompt
   - **Default Implementation**: Uses `few_shot_prompt_template.format()`

6. **`sample_filter(sample: Sample) -> bool`**
   - **Purpose**: Filter dataset samples
   - **Input**: Sample object
   - **Output**: Whether to retain the sample
   - **Default Implementation**: Returns True (retains all samples)

### Hook Method System

DataAdapter provides a hook method system, supporting custom logic insertion at key points:

#### Inference Phase Hooks
- **`_on_inference_start(model, sample)`**: Before inference starts
- **`_on_inference(model, sample)`**: Execute inference
- **`_on_inference_end(model, sample, model_output, output_dir)`**: After inference ends

#### Report Generation Hooks
- **`_on_generate_report(scores, model_name)`**: Generate report
- **`_on_generate_report_end(report, output_dir)`**: After report generation

### Adapter Types

EvalScope provides two main adapter base classes:

1. **`DefaultDataAdapter`**: Basic adapter for general text reasoning tasks
   - Suitable for open-ended question answering, mathematical reasoning, code generation, etc.
   - Requires custom answer extraction logic

2. **`MultiChoiceAdapter`**: Specialized adapter for multiple choice tasks
   - Inherits from `DefaultDataAdapter`
   - Built-in choice formatting and answer extraction logic
   - Supports single-choice and multiple-choice modes

Principles for choosing adapter types:
- If the task involves selecting answers from fixed options → Use `MultiChoiceAdapter`
- If the task requires generating open-ended answers → Use `DefaultDataAdapter`

## 1. Preparing Benchmark Evaluation Dataset

You have two ways to prepare the benchmark evaluation dataset:

1. **Upload to ModelScope (Recommended)**: Upload the dataset to the ModelScope platform, so other users can easily load your dataset, making it more convenient to use and benefiting more users from your contribution. If you need to upload to ModelScope, refer to the [Dataset Upload Tutorial](https://www.modelscope.cn/docs/datasets/create).

2. **Local Use**: You can also directly use the local dataset for evaluation, suitable for datasets that are still in development or contain sensitive information.

Regardless of the method chosen, ensure that the data format is correct and can be loaded. If using a local dataset, you can test with the following code:

```python
from modelscope import MsDataset

dataset = MsDataset.load("/path/to/your/dataset")  # Replace with your dataset
```

## 2. Creating File Structure

First, [Fork EvalScope](https://github.com/modelscope/evalscope/fork) repository, i.e., create your own EvalScope repository copy, and clone it locally.

```bash
git clone https://github.com/your_username/evalscope.git
cd evalscope
```

Then, add benchmark evaluation in the `evalscope/benchmarks/` directory, with the structure as follows:

```text
evalscope/benchmarks/
├── benchmark_name
│   ├── __init__.py
│   ├── benchmark_name_adapter.py
│   └── ...
```
Specifically for `GSM8K` and `MMLU-Pro`, the structure is as follows:

```text
evalscope/benchmarks/
├── gsm8k
│   ├── __init__.py
│   ├── gsm8k_adapter.py
├── mmlu_pro
│   ├── __init__.py
│   ├── mmlu_pro_adapter.py
│   └── ...
```

## 3. Writing Evaluation Logic

Below, we will take **GSM8K** and **MMLU-Pro** as examples to introduce two types of evaluation tasks: **General Text Reasoning** and **Multiple Choice**.

### General Text Reasoning

General text reasoning tasks usually require the model to analyze and reason about the given problem and then generate an answer. Taking GSM8K (mathematical reasoning) as an example:

We need to register `Benchmark` and implement the `GSM8KAdapter` class in `gsm8k_adapter.py`:

```python
from typing import Any, Dict
from evalscope.api.benchmark import BenchmarkMeta, DefaultDataAdapter
from evalscope.api.dataset import Sample
from evalscope.api.evaluator import TaskState
from evalscope.api.registry import register_benchmark
from evalscope.constants import Tags

# Define prompt template
PROMPT_TEMPLATE = """
Solve the following math problem step by step. The last line of your response should display the answer enclosed within \\boxed{{\\text{{$ANSWER}}}}.

Example:

Let's solve the problem step by step.

Problem: Eliza's rate per hour for the first 40 hours she works each week is $10. She also receives an overtime pay of 1.2 times her regular hourly rate. If Eliza worked for 45 hours this week, how much are her earnings for this week?

Step 1: Calculate Eliza's earnings for the first 40 hours. Eliza's hourly rate is $10, so her earnings for the first 40 hours are $10/hour x 40 hours = $400.
Step 2: Calculate Eliza's overtime pay rate. Eliza's overtime pay rate is 1.2 times her regular hourly rate, so her overtime pay rate is $10/hour x 1.2 = $12/hour.
Step 3: Calculate Eliza's earnings for the overtime hours. Eliza worked for 45 hours, so her overtime hours are 45 hours - 40 hours = 5 hours. Her earnings for the overtime hours are $12/hour x 5 hours = $60.
Step 4: Calculate Eliza's total earnings for the week. Eliza's total earnings for the week are her earnings for the first 40 hours plus her earnings for the overtime hours, which is $400 + $60 = $460.

Answer:
\\boxed{{\\text{{460}}}}

question:
{question}

Remember to put your answer on its own line at the end in the form "\\boxed{{\\text{{$ANSWER}}}}" (without quotes), where $ANSWER is replaced by the actual answer to the problem.
""".lstrip()

FEWSHOT_TEMPLATE = """
Here are some examples of how to solve similar problems:

{fewshot}

""".lstrip() + PROMPT_TEMPLATE

# Register benchmark evaluation
@register_benchmark(
    BenchmarkMeta(
        name='gsm8k',                          # Benchmark test name
        pretty_name='GSM8K',                   # Readable name
        dataset_id='AI-ModelScope/gsm8k',      # Dataset ID or local path
        tags=[Tags.MATH, Tags.REASONING],      # Tags
        description='GSM8K (Grade School Math 8K) is a dataset of grade school math problems, designed to evaluate the mathematical reasoning abilities of AI models.',
        subset_list=['main'],                  # Subset list
        few_shot_num=4,                       # Few-shot example number
        train_split='train',                  # Training set split name
        eval_split='test',                    # Evaluation set split name
        metric_list=[{
            'acc': {
                'numeric': True
            }
        }],                                   # Evaluation metrics
        prompt_template=PROMPT_TEMPLATE,      # Prompt template
        few_shot_prompt_template=FEWSHOT_TEMPLATE,  # Few-shot prompt template
    )
)
class GSM8KAdapter(DefaultDataAdapter):
    
    def record_to_sample(self, record: Dict[str, Any]) -> Sample:
        """Convert raw data records into Sample objects"""
        DELIM = '####'
        question = record['question']
        answer = record['answer'].split(DELIM)
        target = answer.pop().strip()  # Extract final answer
        reasoning = DELIM.join(answer)  # Extract reasoning process
        
        return Sample(
            input=question,
            target=target,
            metadata={'reasoning': reasoning.strip()}
        )
    
    def sample_to_fewshot(self, sample: Sample) -> str:
        """Convert sample into few-shot example"""
        if sample.metadata:
            return (
                f'{sample.input}\n\nReasoning:\n' + 
                f"{sample.metadata['reasoning']}\n\n" + 
                f'ANSWER: {sample.target}'
            )
        else:
            return ''
    
    def extract_answer(self, prediction: str, task_state: TaskState):
        """Extract answer from model prediction"""
        from evalscope.metrics.math_parser import extract_answer
        
        return extract_answer(prediction)
```

### Multiple Choice

Multiple choice tasks require the model to select the correct answer from given options. Taking MMLU-Pro as an example, we need to inherit `MultiChoiceAdapter`:

```python
from typing import Any, Dict
from evalscope.api.benchmark import BenchmarkMeta, MultiChoiceAdapter
from evalscope.api.dataset import Sample
from evalscope.api.registry import register_benchmark
from evalscope.constants import Tags

# Define prompt template
USER_PROMPT_TEMPLATE = """Answer the following multiple choice question. The last line of your response should be of the following format: 'ANSWER: $LETTER' (without quotes) where LETTER is one of {letters}. Think step by step before answering.

Question:
{question}
Options:
{choices}
""".lstrip()

SUBSET_LIST = [
    'computer science', 'math', 'chemistry', 'engineering', 'law', 'biology', 
    'health', 'physics', 'business', 'philosophy', 'economics', 'other', 
    'psychology', 'history'
]

@register_benchmark(
    BenchmarkMeta(
        name='mmlu_pro',
        pretty_name='MMLU-Pro',
        tags=[Tags.MULTIPLE_CHOICE, Tags.KNOWLEDGE],
        description='MMLU-Pro is a benchmark for evaluating language models on multiple-choice questions across various subjects.',
        dataset_id='modelscope/MMLU-Pro',
        subset_list=SUBSET_LIST,
        metric_list=['acc'],
        few_shot_num=5,
        train_split='validation',
        eval_split='test',
        prompt_template=USER_PROMPT_TEMPLATE,
    )
)
class MMLUProAdapter(MultiChoiceAdapter):
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.reformat_subset = True  # Enable subset division
    
    def record_to_sample(self, record: Dict[str, Any]) -> Sample:
        """Convert raw data records into Sample objects"""
        return Sample(
            input=record['question'],
            choices=record['options'],      # Choice list
            target=record['answer'],        # Correct answer (e.g., 'A')
            subset_key=record['category'].lower(),  # Key for subset division
            metadata={
                'cot_content': record['cot_content'],
                'subject': record['category'].lower(),
                'question_id': record['question_id'],
            },
        )
    
    def sample_to_fewshot(self, sample: Sample) -> str:
        """Convert sample into few-shot example"""
        q_str = f"""Question:\n{str(sample.input)}"""
        options = sample.choices if sample.choices is not None else []
        
        # Format choices
        opt_str_list = []
        for i, opt in enumerate(options):
            opt_str_list.append(f"""{chr(65 + i)} {opt}""")
        opt_str = f"""Options:\n{'\n'.join(opt_str_list)}"""
        
        # Handle answer and reasoning process
        ans_str = sample.metadata['cot_content'] if sample.metadata is not None else ''
        ans_str = ans_str.replace('The answer is', 'ANSWER:')
        ans_opt = ans_str.split('ANSWER:')[-1].split('.')[0].strip().strip('(').strip(')')
        ans_str = ans_str.replace(f'ANSWER: ({ans_opt})', f'ANSWER: {ans_opt}')
        
        final_str = '\n'.join([q_str, opt_str, ans_str])
        return final_str
```

### Key Differences Explanation

**General Text Reasoning** vs **Multiple Choice**:

1. **Inherited Base Class**:
   - General Text Reasoning: Inherits `DefaultDataAdapter`
   - Multiple Choice: Inherits `MultiChoiceAdapter`

2. **Sample Object Structure**:
   - General Text Reasoning: Mainly includes `input` and `target`
   - Multiple Choice: Additionally includes `choices` (choice list)

3. **Answer Extraction Method**:
   - General Text Reasoning: Requires custom `extract_answer()` method
   - Multiple Choice: `MultiChoiceAdapter` provides standard answer extraction logic

4. **Prompt Template**:
   - General Text Reasoning: Focuses more on guiding the reasoning process
   - Multiple Choice: Focuses on displaying choices and answer format

## 4. Running Evaluation

Debug the code to see if it can run normally.

**GSM8K Example**:
```python
from evalscope import run_task, TaskConfig

task_cfg = TaskConfig(
    model='Qwen/Qwen2.5-0.5B-Instruct',
    datasets=['gsm8k'],
    limit=10,
    debug=True
)
run_task(task_cfg=task_cfg)
```

**MMLU-Pro Example**:
```python
from evalscope import run_task, TaskConfig

task_cfg = TaskConfig(
    model='Qwen/Qwen2.5-0.5B-Instruct',
    datasets=['mmlu_pro'],
    limit=10,
    dataset_args={'mmlu_pro': {'subset_list': ['computer science', 'math']}},
    debug=True
)
run_task(task_cfg=task_cfg)
```

Output Example:

```text
+-----------------------+-----------+-----------------+------------------+-------+---------+---------+
| Model                 | Dataset   | Metric          | Subset           |   Num |   Score | Cat.0   |
+=======================+===========+=================+==================+=======+=========+=========+
| Qwen2.5-0.5B-Instruct | gsm8k     | mean_acc        | main             |    10 |     0.3 | default |
+-----------------------+-----------+-----------------+------------------+-------+---------+---------+
| Qwen2.5-0.5B-Instruct | mmlu_pro  | mean_acc        | computer science |    10 |     0.1 | default |
+-----------------------+-----------+-----------------+------------------+-------+---------+---------+
| Qwen2.5-0.5B-Instruct | mmlu_pro  | mean_acc        | math             |    10 |     0.1 | default |
+-----------------------+-----------+-----------------+------------------+-------+---------+---------+
```

## 5. Benchmark Evaluation Document Generation

After completing the benchmark evaluation implementation, you can use the tools provided by EvalScope to generate standard documents. This will ensure that your benchmark evaluation has a consistent document format and can be easily understood and used by other users.

To generate Chinese and English documents, run the following command, which will generate documents based on registration information:

```bash
pip install -e '.[docs]'
make docs
```

## 6. Submitting PR
After completing the implementation of these methods and document generation, your benchmark evaluation is ready! You can submit a [PR](https://github.com/modelscope/evalscope/pulls). Before submitting, please run the following command, which will automatically format the code:
```bash
make lint
```
Ensure there are no formatting issues, and we will merge your contribution as soon as possible, allowing more users to use the benchmark evaluation you contributed. If you don't know how to submit a PR, you can check our [Guide](https://github.com/modelscope/evalscope/blob/main/CONTRIBUTING.md). Give it a try 🚀