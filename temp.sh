evalscope eval  --model Qwen2.5-Coder-3B-Instruct  --api-url http://192.168.1.250:8001/v1   --api-key EMPTY --eval-type openai_api   --limit 10   --datasets tau_bench  --dataset-args '{"tau_bench": {"extra_params": {"api_key": "sk-SnVl9tUWyPfyCTVWr9Mayw", "api_base": "https://proxy.infix-ai.xyz", "user_model": "gpt-4o"}}}'


  --extra_params.api_base https://proxy.infix-ai.xyz

evalscope eval  --model gpt-5-mini  --api-url https://proxy.infix-ai.xyz/v1  --api-key sk-SnVl9tUWyPfyCTVWr9Mayw  --eval-type openai_api   --limit 10   --datasets bfcl_v3   

--generation-config '{"temperature": 1}' --dataset-args '{"ace_bench": {
      "local_path": "new_data/ACEBench/data_all/general_fc_en",
      "subset_list": ["data_normal_single_turn_single_function"]
  }}'



evalscope eval  --model Qwen2.5-Coder-3B-Instruct  --api-url http://192.168.1.250:8001/v1  --api-key EMPTY  --eval-type openai_api   --limit 10   --datasets ace_bench  




curl http://192.168.1.250:8001/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "Qwen2.5-Coder-3B-Instruct",
    "messages": [
      {"role": "user", "content": "你好！"}
    ]
  }'



export DASHSCOPE_API_KEY="sk-42a57c2c141340ea97d8de960b75fdb9"

sk-SnVl9tUWyPfyCTVWr9Mayw

['a_okvqa', 'aa_lcr', 'ai2d', 'aime24', 'aime25', 'alpaca_eval', 'amc', 'arc', 'arena_hard', 'bbh', 'bfcl_v3', 'bfcl_v4', 'biomix_qa', 'blink', 'broad_twitter_corpus', 'cc_bench', 'ceval', 'chartqa', 'chinese_simpleqa', 'cmmlu', 'cmmu', 'coin_flip', 'commonsense_qa', 'competition_math', 'conll2003', 'copious', 'cross_ner', 'data_collection', 'docmath', 'docvqa', 'drivel_binary', 'drivel_multilabel', 'drivel_selection', 'drivel_writing', 'drop', 'evalmuse', 'frames', 'gedit', 'genai_bench', 'general_arena', 'general_fc', 'general_mcq', 'general_qa', 'general_t2i', 'genia_ner', 'gpqa_diamond', 'gsm8k', 'hallusion_bench', 'halueval', 'harvey_ner', 'health_bench', 'hellaswag', 'hle', 'hpdv2', 'humaneval', 'ifeval', 'infovqa', 'iquiz', 'live_code_bench', 'logi_qa', 'maritime_bench', 'math_500', 'math_qa', 'math_verse', 'math_vision', 'math_vista', 'med_mcqa', 'minerva_math', 'mit_movie_trivia', 'mit_restaurant', 'mm_bench', 'mm_star', 'mmlu', 'mmlu_pro', 'mmlu_redux', 'mmmu', 'mmmu_pro', 'mri_mcqa', 'multi_if', 'music_trivia', 'musr', 'needle_haystack', 'ocr_bench', 'ocr_bench_v2', 'olympiad_bench', 'omni_bench', 'omni_doc_bench', 'ontonotes5', 'openai_mrcr', 'piqa', 'poly_math', 'pope', 'process_bench', 'pubmedqa', 'qasc', 'race', 'real_world_qa', 'science_qa', 'sciq', 'seed_bench_2_plus', 'simple_qa', 'simple_vqa', 'siqa', 'super_gpqa', 'swe_bench_lite', 'swe_bench_verified', 'swe_bench_verified_mini', 'tau2_bench', 'tau_bench', 'tifa160', 'tool_bench', 'trivia_qa', 'truthful_qa', 'visulogic', 'vstar_bench', 'winogrande', 'wmt24pp', 'wnut2017', 'zerobench']