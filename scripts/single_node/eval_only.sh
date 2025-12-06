#!/bin/bash

#SBATCH --job-name=evalscope
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --mem=16GB
#SBATCH --cpus-per-task=4
#SBATCH --output=logs/%j-evalscope.out
#SBATCH --error=logs/%j-evalscope.err

echo "Starting evalscope only..."
container_workdir=$(pwd)
evalscope_image="/lustre/projects/polyullm/container/evalscope_eval+1.0a.sqsh"
sglang_image="/lustre/projects/polyullm/container/slimerl+slime+latest+1202a.sqsh"
container_mounts="/lustre/projects/polyullm:/lustre/projects/polyullm,/work/projects/polyullm:/work/projects/polyullm"

# Getting the node names
nodes=$(scontrol show hostnames "$SLURM_JOB_NODELIST")
nodes_array=($nodes)

# Get the IP address of the head node
head_node=${nodes_array[0]}
head_node_ip=$(srun --nodes=1 --ntasks=1 -w "$head_node" hostname --ip-address)

SGLANG_SERVER=$1

echo "SGLANG_SERVER: ${SGLANG_SERVER}"

# Wait for sglang service to be ready
echo "Waiting for sglang service to start..."
SERVICE_URL="${SGLANG_SERVER}/v1/models"
MAX_RETRIES=20
RETRY_INTERVAL=10
RETRY_COUNT=0

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "${SERVICE_URL}" 2>/dev/null)
    if [ "$HTTP_CODE" = "200" ]; then
        echo "sglang service is ready!"
        break
    else
        RETRY_COUNT=$((RETRY_COUNT + 1))
        if [ $RETRY_COUNT -lt $MAX_RETRIES ]; then
            echo "Attempt ${RETRY_COUNT}/${MAX_RETRIES}: sglang service not ready yet (HTTP ${HTTP_CODE:-000}), waiting ${RETRY_INTERVAL}s..."
            sleep ${RETRY_INTERVAL}
        fi
    fi
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    echo "ERROR: sglang service failed to start after ${MAX_RETRIES} attempts"
    kill $SGLANG_PID 2>/dev/null
    exit 1
fi

# Get model name from /v1/models endpoint
echo "Fetching model name from sglang service..."
MODELS_RESPONSE=$(curl -s "${SERVICE_URL}" 2>/dev/null)
SERVED_NAME=$(echo "$MODELS_RESPONSE" | jq -r '.data[0].id' 2>/dev/null)
echo "SERVED_NAME: ${SERVED_NAME}"

#==============EvalScope==============
echo "Starting EvalScope..."
API_URL="${SGLANG_SERVER}/v1/chat/completions"
EVAL_WORK_DIR="/work/projects/polyullm/reallm.xyz/evalscope_dev"
DATASET_LOCAL="/work/projects/polyullm/llm-eval/datasets/aime_2024"
EVAL_DATASET="aime24"
MAX_NEW_TOKENS=8192
GENERATED_NUM=1
EVAL_TIMEOUT=1800000
EVAL_BATCH=64

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
    "prompt_template": "<|im_start|>user\\n{question}<|im_end|>\\n<|im_start|>assistant\\n<think>\\n",
    "system_prompt": "<|im_start|>system\\nPlease reason step by step, and put your final answer within \\\\boxed{{}}.<|im_end|>\\n"
  }
}
EOF
DATASET_ARGS=$(echo "$DATASET_ARGS_JSON" | tr -d '\n')

evalscope_scripts="
set -x
evalscope eval \
  --model \"${SERVED_NAME}\" \
  --generation-config '${GEN_CONFIG}' \
  --api-url \"${API_URL}\" \
  --api-key EMPTY \
  --eval-type openai_api \
  --work-dir \"${EVAL_WORK_DIR}\" \
  --datasets \"${EVAL_DATASET}\" \
  --dataset-args '${DATASET_ARGS}' \
  --eval-batch-size \"${EVAL_BATCH}\" \
  --timeout \"${EVAL_TIMEOUT}\"
"
echo evalscope_scripts: ${evalscope_scripts}

srun --overlap --container-image=${evalscope_image} \
  --container-mounts=${container_mounts} \
  --container-workdir=${container_workdir} \
  --container-remap-root \
  --container-writable \
  bash -c "${evalscope_scripts}"




cleanup() {
  echo "Cleaning up..."
  kill $SGLANG_PID 2>/dev/null
  exit 0
}

trap cleanup SIGINT SIGTERM

