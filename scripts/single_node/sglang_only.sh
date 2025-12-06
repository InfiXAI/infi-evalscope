#!/bin/bash

#SBATCH --job-name=evalscope-sglang
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --mem=256GB
#SBATCH --gpus-per-node=8
#SBATCH --cpus-per-task=64
#SBATCH --output=logs/%j-evalscope-sglang.out
#SBATCH --error=logs/%j-evalscope-sglang.err

echo "Starting sglang only..."
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
DP=4

sglang_scripts="
set -x
MODEL=${MODEL}
PORT=${PORT}
MODEL_NAME=${MODEL_NAME}
TP=${TP}
DP=${DP}

python3 -m sglang.launch_server \
  --model ${MODEL} \
  --served-model-name ${MODEL_NAME} \
  --host 0.0.0.0 \
  --port ${PORT} \
  --trust-remote-code \
  --tensor-parallel-size ${TP} \
  --data-parallel-size ${DP}
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

wait $SGLANG_PID


cleanup() {
  echo "Cleaning up..."
  kill $SGLANG_PID 2>/dev/null
  exit 0
}

trap cleanup SIGINT SIGTERM

