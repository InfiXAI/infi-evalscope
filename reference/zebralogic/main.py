import json
import os
import tqdm
from datasets import load_dataset
from templates.ZEBRA_GRID import ZEBRA_GRID


def map_to_conv(model_name):
    if model_name in HF_TEMPLATED_MODELS:
        print(f"Model {model_name} is using HF chat-template method.")
        conv = HF_Conversation(model_name)
    elif "gemma" in model_name.lower() and "-it" in model_name.lower():
        conv = get_conv_template("gemma")
    elif "tulu" in model_name.lower():
        conv = get_conv_template("tulu")
    elif "zephyr" in model_name.lower():
        conv = get_conv_template("zephyr")
    elif "llama-2" in model_name.lower() and "-chat-hf" in model_name.lower():
        conv = get_conv_template("llama-2")
        # conv.set_system_message("""You are a helpful, respectful and honest assistant. Always answer as helpfully as possible, while being safe.  Your answers should not include any harmful, unethical, racist, sexist, toxic, dangerous, or illegal content. Please ensure that your responses are socially unbiased and positive in nature.\n\nIf a question does not make any sense, or is not factually coherent, explain why instead of answering something not correct. If you don't know the answer to a question, please don't share false information.""")
    elif "llama-3" in model_name.lower() and "-instruct" in model_name.lower():
        # note that models like `Llama-3-Instruct-8B-SimPO` also matches this condition
        conv = get_conv_template("llama-3")
    elif "mixtral" in model_name.lower() or "mistral" in model_name.lower():
        conv = get_conv_template("mistral")
    elif "yi" in model_name.lower() and "chat" in model_name.lower():
        conv = get_conv_template("Yi-34b-chat")
    elif "vicuna" in model_name.lower():
        conv = get_conv_template("vicuna_v1.1")
    elif "qwen" in model_name.lower():
        conv = get_conv_template("qwen-7b-chat")
    elif "starling-lm" in model_name.lower():
        conv = get_conv_template("openchat_3.5")
    else:
        raise ValueError(f"Model {model_name} is not supported.")

    return conv


def apply_template(chat_history, model_name, args):
    model_inputs = []
    conv = None
    for chats in tqdm(chat_history, desc="Applying template", disable=True):
        if args.engine not in ["vllm", "hf"]:
            model_inputs.append("n/a")  # will be handled by another ways.
            continue
        else:
            if conv is None or isinstance(conv, HF_Conversation) == False:
                conv = map_to_conv(model_name)
            else:
                conv.clear()
        for chat_id, chat in enumerate(chats):
            conv.append_message(conv.roles[chat_id % 2], chat)
        conv.append_message(conv.roles[1], None)
        model_inputs.append(conv.get_prompt())
    return model_inputs


def prompt_generation(data_name, data_item, args):
    prompt_str = ZEBRA_GRID[:]
    prompt_str = prompt_str.replace("{puzzle}", data_item["puzzle"])
    num_houses = len(data_item["solution"]["rows"])
    columns = data_item["solution"]["header"]
    assert columns[0] == "House"
    json_template = {"reasoning": "___", "solution": {}}
    for i in range(num_houses):
        json_template["solution"][f'House {i + 1}'] = {columns[j]: "___" for j in range(1, len(columns))}
    json_str = json.dumps(json_template, indent=4)
    prompt = prompt_str.replace("{json_template}", json_str)

    return prompt


def load_eval_data(args, data_name=None, model_name=None):
    chat_history = []
    id_strs = []
    metadata = {}
    id_name = "id"
    dataset = load_dataset("allenai/ZebraLogicBench", "grid_mode", split="test")

    print(f"Loaded {len(dataset)} examples from {data_name}")

    for ind, item in enumerate(dataset):
        id_strs.append(item.get(id_name, f"{data_name}#{ind}"))
        prompt = prompt_generation(data_name, item, args)
        chat_history.append([prompt])
        for key in item:
            if key not in metadata:
                metadata[key] = []
            metadata[key].append(item[key])

    print("Start applying template")
    model_inputs = apply_template(chat_history, model_name, args)
    return id_strs, chat_history, model_inputs, metadata

id_strs, chat_history, model_inputs, metadata = load_eval_data(args)



# Decide the output filepath
if args.filepath == "auto":
    # Decide the output filepath
    if "/" in args.model_name and args.model_pretty_name is None:
        args.model_pretty_name = args.model_name.split("/")[-1]
    os.system(f"mkdir -p {args.output_folder}")
    if args.end_index == -1 and args.start_index == 0:
        filepath = f"{args.output_folder}/{args.model_pretty_name}.json"
    else:
        filepath = f"{args.output_folder}/{args.model_pretty_name}.{args.start_index}-{args.end_index}.json"
else:
    filepath = args.filepath
    output_folder = "/".join(filepath.split("/")[:-1])
    if not os.path.exists(output_folder):
        os.system(f"mkdir -p {output_folder}")

if args.end_index < 0 or args.end_index > len(model_inputs):
    args.end_index = len(model_inputs)
model_inputs = model_inputs[args.start_index:args.end_index]
id_strs = id_strs[args.start_index:args.end_index]
chat_history = chat_history[args.start_index:args.end_index]
metadata = {key: metadata[key][args.start_index:args.end_index] for key in metadata}

print("loading dataset ... done!")

# speical handling
stop_words = []
include_stop_str_in_output = False
stop_token_ids = []
# if "yi-" in args.model_name.lower() and "chat" in args.model_name.lower():
#     stop_token_ids = [7]
# elif "zephyr-7b-gemma-v0.1" in args.model_name.lower():
#     stop_token_ids = [107]

if args.model_name in IM_END_MODELS:
    hf_tokenizer = AutoTokenizer.from_pretrained(args.model_name, trust_remote_code=True)
    potential_end_tokens = ["<|im_end|>" , "<|eot_id|>"]
    for potential_end_token in potential_end_tokens:
        if potential_end_token in hf_tokenizer.get_vocab():
            stop_token_ids += [hf_tokenizer.get_vocab()[potential_end_token]]
if args.model_name in HF_TEMPLATED_MODELS:
    hf_tokenizer = AutoTokenizer.from_pretrained(args.model_name, trust_remote_code=True)
    stop_token_ids.append(hf_tokenizer.eos_token_id)


outputs = []
# Load the existing outputs
if os.path.exists(filepath) and not args.overwrite:
    with open(filepath) as f:
        formatted_outputs = json.load(f)
    for output_item in formatted_outputs:
        outputs.append([output_item["output"]] if type(output_item["output"]) == str else output_item["output"])
        if args.model_name.startswith("openai/o"):
            if "hidden_reasoning_token" not in metadata:
                metadata["hidden_reasoning_token"] = []
            metadata["hidden_reasoning_token"].append(output_item["hidden_reasoning_token"])
num_skipped = len(outputs)
print(f"We skipped the first {num_skipped} examples")