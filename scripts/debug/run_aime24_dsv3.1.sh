#!/bin/bash

set -x

API_URL="http://kb3-a1-nv-dgx05:30001/v1/chat/completions"
SERVED_NAME="/work/projects/polyullm/models/DeepSeek-V3.1-Terminus"
EVAL_WORK_DIR="/work/projects/polyullm/reallm.xyz/evalscope_dev"
DATASET_LOCAL="/work/projects/polyullm/llm-eval/datasets/aime_2024"
EVAL_DATASET="aime24"
MAX_NEW_TOKENS=8192
GENERATED_NUM=1
EVAL_TIMEOUT=1800000
EVAL_BATCH=1

read -r -d '' GENERATION_CONFIG_JSON <<EOF
{
  "do_sample": true,
  "temperature": 0.6,
  "top_p": 0.95,
  "max_tokens": ${MAX_NEW_TOKENS},
  "n": ${GENERATED_NUM}
}
EOF
GEN_CONFIG=$(echo "$GENERATION_CONFIG_JSON" | tr -d '\n')

read -r -d '' DATASET_ARGS_JSON <<EOF
{
  "aime24": {
    "local_path": "${DATASET_LOCAL}",
    "filters": {"remove_until": "</think>"},
    "prompt_template": "<|user|>{question}<|assistant|></think>",
    "system_prompt": "<|begin_of_sentence|>Please reason step by step, and put your final answer within \\\\boxed{}."
  }
}
EOF
DATASET_ARGS=$(echo "$DATASET_ARGS_JSON" | tr -d '\n')

evalscope eval \
  --model "${SERVED_NAME}" \
  --generation-config "${GEN_CONFIG}" \
  --api-url "${API_URL}" \
  --api-key EMPTY \
  --eval-type openai_api \
  --work-dir "${EVAL_WORK_DIR}" \
  --datasets "${EVAL_DATASET}" \
  --dataset-args "${DATASET_ARGS}" \
  --eval-batch-size "${EVAL_BATCH}" \
  --timeout "${EVAL_TIMEOUT}"