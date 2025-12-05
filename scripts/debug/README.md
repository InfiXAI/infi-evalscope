## Debug scripts guide

These scripts help reproduce EvalScope jobs interactively without waiting for Slurm queues.

0. On the login node, start a `tmux` session so that your debug shell keeps running if the SSH session drops.

1. Request an interactive compute node and enter the required env:
```
bash scripts/debug/start_evalscope_env.sh
```
   - The script wraps `srun` with CPU-only defaults (4 cores, short wall time) because this step just prepares the environment and sends requests; no GPU is allocated.
   - If you actually need to co-locate an inference server for debugging, add `--gpus` or other accelerator flags directly in the script before submitting.
   - It also exports `EVAL_WORK_DIR` and other paths so that log files land in `/tmp` by default; override them before running the script if needed.

2. Launch the sample EvalScope workflow once you are on the allocated node:
```
bash scripts/debug/run_aime24_dsv3.1.sh
```
   - This script runs the AIME24 benchmark against the `dsv3.1` config and streams logs to the console for quick inspection.
   - Update the dataset/model arguments inside the script when you want to test different combos.
