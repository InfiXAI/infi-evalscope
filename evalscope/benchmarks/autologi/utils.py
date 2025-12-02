#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import logging
import os
import re
import sys
import ast
from collections import defaultdict
from pathlib import Path
from typing import List
from copy import deepcopy
import dataclasses
import argparse
from tqdm import tqdm
import subprocess
import time
from subprocess import PIPE

INVALID_VALUE = -9999999

verify_fuction_code = """def verify_function(inputs, inputs_check, constraint_list):
    # 首先检查inputs是否有效
    if not inputs_check(inputs):  # 如果输入格式不满足
            return False
    
    # 遍历constraint_list，对每个约束函数进行检查
    for constraint in constraint_list:
        if not constraint(inputs):  # 如果约束不满足
            return False
            
    # 所有约束都已检查且满足
    return True"""

@dataclasses.dataclass
class InputExample:
    idx: int
    prompt: str
    Inputs_Check_code: str
    Constraint_List_code: str
    Traverse_code: str
    gen: str 


def get_prompt_list(prediction, task_state):
    inp = InputExample(
        idx = task_state.metadata['idx'],
        prompt = "",
        Inputs_Check_code = task_state.metadata['Inputs_Check_code'],
        Constraint_List_code = task_state.metadata['Constraint_List_code'],
        Traverse_code = task_state.metadata['Traverse_code'],
        gen = prediction
    )
    return inp

def extract_code(text: str) -> str:
        code_block_pattern = re.compile(r"```(?:\s*[\w]+)?\s*\n(.*?)```", re.DOTALL)
        code_blocks = code_block_pattern.findall(text)
        
        if code_blocks:
            return code_blocks[-1]
        else:
            return None

def extract_last_dict(content):
    stack = []  
    start_idx = None  
    last_dict = None 

    for i, char in enumerate(content):
        if char == '{':
            if not stack:
                start_idx = i
            stack.append('{')
        elif char == '}':
            if stack:
                stack.pop()
                if not stack:
                    last_dict = content[start_idx:i + 1]
    return last_dict

def extract_last_list(content):
    matches = re.findall(r"\[.*?\]", content, re.DOTALL)
    if matches:
        return matches[-1]
    else:
        return None
    
def compute_coding_pass1(inp):
    result = {}
    content = inp.gen
    func_args = None
    result["extraction_failed"] = 0
    result["error"] = None
    func_args  = None if content == "" else content
    if func_args is None:
        last_dict = extract_last_dict(content)
        last_list = extract_last_list(content)
        if last_dict is not None:
            func_args = last_dict
        else:
            if last_list is not None:
                func_args = last_list
            else:
                return {"acc": 0, "error": "extraction_failed", "extraction_failed": 1}
    try:
        func_args = re.sub(r'//.*?\n', '', func_args)
        params = ast.literal_eval(func_args.replace("true","True").replace("false","False"))
    except (SyntaxError, ValueError, TypeError) as e:
        if "=" in func_args:
            try:
                params_str = func_args.split("=", 1)[1].strip()
                params = ast.literal_eval(params_str)
            except (SyntaxError, ValueError, TypeError) as e:
                return {"acc": 0, "error": "extraction_failed", "extraction_failed": 1 }
        else:
            try:
                params = json.loads(func_args)
            except:
                return {"acc": 0, "error": "extraction_failed", "extraction_failed": 1}
        
    # predictions = inp.Inputs_Check_code +"\n" + inp.Constraint_List_code + "\n" + verify_fuction_code+ "\n" + f"res = verify_function({params}, inputs_check, constraint_list)" + "\nassert res == True"
    test_program = inp.Inputs_Check_code +"\n" + inp.Constraint_List_code + "\n" + verify_fuction_code+ "\n" + f"res = verify_function({params}, inputs_check, constraint_list)" +"\nprint(res)"+ "\nassert res == True"
    
    timeout = 20
    output, error = run_code(test_program, timeout)

    return {"acc": 1 if output and output.strip() in ["True","true"] else 0, "error": error, "extraction_failed": 0}

def run_code(code, timeout=20):
    with open('./temp_code.py', 'w', encoding='utf-8') as f:
        f.write(code)
    try:
        process = subprocess.Popen(['python', 'temp_code.py'], 
                                 stdout=PIPE, 
                                 stderr=PIPE)
        start_time = time.time()
        while process.poll() is None:
            if time.time() - start_time > timeout:
                process.kill()
                return None, "TimeoutError: Code execution exceeded {} seconds".format(timeout)
            time.sleep(0.1)
        stdout, stderr = process.communicate()
        if stderr:
            return None, stderr.decode('utf-8')
        return stdout.decode('utf-8'), None
    except Exception as e:
        return None, str(e)
