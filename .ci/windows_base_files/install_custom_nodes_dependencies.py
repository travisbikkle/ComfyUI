#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import yaml
import subprocess
from pathlib import Path
import logging
import re

def load_yaml_config(yaml_path):
    """加载 YAML 配置文件"""
    if not os.path.exists(yaml_path):
        return {}
    try:
        with open(yaml_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or {}
    except Exception as e:
        logging.warning(f"[WARN] Failed to load {yaml_path}: {e}")
        return {}

def get_paths(portable_path):
    """获取 base_path 和 custom_nodes 路径 (仅便携版)"""
    default_base_path = os.path.join(portable_path, "ComfyUI")
    default_custom_nodes = os.path.join(portable_path, "ComfyUI", "custom_nodes")
    yaml_path = os.path.join(portable_path, "ComfyUI", "extra_model_paths.yaml")
    config = load_yaml_config(yaml_path)
    
    comfyui_block = config.get("comfyui", {}) if isinstance(config, dict) else {}
    base_path = comfyui_block.get('base_path', default_base_path)
    custom_nodes_path = comfyui_block.get('custom_nodes', default_custom_nodes)

    if not os.path.isabs(base_path):
        base_path = os.path.abspath(base_path)
    if not os.path.isabs(custom_nodes_path):
        custom_nodes_path = os.path.join(base_path, custom_nodes_path)
    
    return base_path, custom_nodes_path

def replace_git_urls(content, github_mirror_prefix):
    # 替换所有 git+https://github.com/ 为 git+https://ghproxy.com/https://github.com/
    return re.sub(r'git\+https://github\.com/', f'git+{github_mirror_prefix}https://github.com/', content)

def install_requirements(python_exec, req_file, github_mirror_prefix, pip_mirror_url):
    """安装单个 requirements.txt 文件"""
    logging.info(f"Processing requirements: {req_file}")
    
    if not os.path.exists(req_file):
        logging.info(f"  [INFO] {req_file} does not exist, skipping.")
        return
    
    file_size = os.path.getsize(req_file)
    if file_size == 0:
        logging.info(f"  [INFO] {req_file} is empty, skipping.")
        return
    
    try:
        with open(req_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        modified_content = replace_git_urls(content, github_mirror_prefix)
        
        temp_file = req_file + ".mirrored"
        with open(temp_file, 'w', encoding='utf-8') as f:
            f.write(modified_content)
        
        try:
            print(f" =============={req_file}====================\n{modified_content}\n===============================");
            subprocess.run([python_exec, "-m", "pip", "install", "-r", temp_file, "--index-url", pip_mirror_url], 
                         check=True)
        finally:
            if os.path.exists(temp_file):
                pass
                # os.remove(temp_file)
                
    except Exception as e:
        logging.error(f"  [ERROR] Failed to process {req_file}: {e}")

def main():
    """主函数 (仅支持便携版，默认当前路径，直接用python_embeded)"""
    github_mirror_prefix = "https://ghproxy.com/"
    pip_mirror_url = "https://pypi.tuna.tsinghua.edu.cn/simple"
    
    try:
        portable_path = os.getcwd()
        base_path, custom_nodes_path = get_paths(portable_path)
        logging.info(f"Using base_path: {base_path}")
        logging.info(f"Using custom_nodes directory: {custom_nodes_path}")

        # 直接用 python_embeded 下的 python 解释器
        if os.name == 'nt':
            python_exec = os.path.join(portable_path, "python_embeded", "python.exe")
        else:
            python_exec = os.path.join(portable_path, "python_embeded", "bin", "python")

        if not os.path.exists(python_exec):
            logging.error(f"[ERROR] Python executable not found: {python_exec}")
            return 1

        logging.info(f"Using Python: {python_exec}")
        logging.info("Upgrading pip ...")

        subprocess.run([python_exec, "-m", "pip", "install", "cython", "--index-url", pip_mirror_url], 
                    check=True, capture_output=True)

        subprocess.run([python_exec, "-m", "pip", "install", "--upgrade", "pip", "--index-url", pip_mirror_url], 
                     check=True, capture_output=True)
        
        if not os.path.exists(custom_nodes_path):
            logging.error(f"[ERROR] Directory {custom_nodes_path} does not exist!")
            return 1
        
        custom_nodes_dir = Path(custom_nodes_path)
        for subdir in custom_nodes_dir.iterdir():
            if subdir.is_dir():
                req_file = subdir / "requirements.txt"
                if req_file.exists():
                    install_requirements(str(python_exec), str(req_file), github_mirror_prefix, pip_mirror_url)
        
        logging.info("Installation completed successfully!")
        return 0
        
    except Exception as e:
        logging.error(f"[ERROR] {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
