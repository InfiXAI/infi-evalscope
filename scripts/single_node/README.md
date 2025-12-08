## Single-node scripts

Utility scripts for launching SGLang inference and EvalScope evaluation jobs on a single Slurm node.

### Notes
1. Set `EVAL_WORK_DIR` to a writable directory for evaluation outputs and logs.
2. Double-check the prompts you pass to the evaluator—different models often require different `system_prompt` and `user_prompt` templates.
3. For small models (≤7B), TP=8 is unnecessary—configure SGLang with data-parallel replicas (e.g., set `--data-parallel-size` to match your GPU count / TP) to keep all 8 GPUs busy and raise EvalScope's `--eval-batch-size` so the server stays “打满”.

### How to run

1. `sglang_only.sh` — launches only the SGLang inference service. Useful when you want to reuse the same service for multiple evaluations.
```
sbatch scripts/single_node/sglang_only.sh
```

2. `eval_only.sh` — runs only the EvalScope evaluation pipeline against an already running SGLang endpoint. Pass the full endpoint URL (e.g. `http://host:port`).
```
sbatch scripts/single_node/eval_only.sh http://sglang_host:sglang_port
```

   Key environment variables:
   - `EVAL_DATASET` — dataset or benchmark suite to run.
   - `MODEL_NAME` — model identifier passed to EvalScope for logging.

3. `all_in_one.sh` — starts both the SGLang service and EvalScope evaluation in the same Slurm job, ensuring the evaluator automatically targets the freshly launched endpoint.
```
sbatch scripts/single_node/all_in_one.sh
```

