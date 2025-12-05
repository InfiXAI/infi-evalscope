#!/bin/bash

#SBATCH --job-name=evalscope-sglang-all-in-one
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --mem=256GB
#SBATCH --gpus-per-node=8
#SBATCH --cpus-per-task=64
#SBATCH --output=logs/%j-evalscope-sglang-all-in-one.out
#SBATCH --error=logs/%j-evalscope-sglang-all-in-one.err

echo "Starting all in one..."
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

MODEL="/lustre/projects/polyullm/models/Qwen3/Qwen3-4B"
MODEL_NAME="Qwen3-4B"
PORT=31000
TP=2

sglang_scripts="
set -x
MODEL=${MODEL}
PORT=${PORT}
MODEL_NAME=${MODEL_NAME}
TP=${TP}

python3 -m sglang.launch_server \
  --model ${MODEL} \
  --served-model-name ${MODEL_NAME} \
  --host 0.0.0.0 \
  --port ${PORT} \
  --trust-remote-code \
  --tensor-parallel-size ${TP} \
  --warmups 3 \
  --max-running-requests 16 \
  --chunked-prefill-size 4096
"

echo sglang_scripts: ${sglang_scripts}
# Start sglang service in background
srun --container-image=${sglang_image} \
  --container-mounts=${container_mounts} \
  --container-workdir=${container_workdir} \
  --container-remap-root \
  --container-writable \
  bash -c "${sglang_scripts}" &

SGLANG_PID=$!

# Wait for sglang service to be ready
echo "Waiting for sglang service to start..."
SERVICE_URL="http://${head_node_ip}:${PORT}/v1/models"
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

#==============EvalScope==============
echo "Starting EvalScope..."
API_URL="http://${head_node_ip}:${PORT}/v1/chat/completions"
SERVED_NAME="${MODEL_NAME}"
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

