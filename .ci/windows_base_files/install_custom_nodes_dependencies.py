#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import yaml
import subprocess
from pathlib import Path

def get_user_choice():
    """获取用户选择的 ComfyUI 版本和路径"""
    print("=== ComfyUI Custom Nodes Dependencies Installer ===")
    print()
    print("请选择 ComfyUI 版本类型：")
    print("1. 便携版 (Portable)")
    print("2. 桌面版 (Desktop)")
    print()
    
    while True:
        try:
            choice = input("请输入选择 (1 或 2): ").strip()
            if choice == "1":
                return "portable"
            elif choice == "2":
                return "desktop"
            else:
                print("无效选择，请输入 1 或 2")
        except KeyboardInterrupt:
            print("\n用户取消操作")
            sys.exit(1)

def get_portable_path():
    """获取便携版路径"""
    print()
    print("=== 便携版配置 ===")
    print("请输入 ComfyUI 便携版的根目录路径")
    print("例如: D:\\ComfyUI_windows_portable")
    print()
    
    while True:
        try:
            path = input("ComfyUI 便携版路径: ").strip().strip('"')
            if not path:
                print("路径不能为空")
                continue
            
            # 检查路径是否存在
            if not os.path.exists(path):
                print(f"路径不存在: {path}")
                continue
            
            # 检查是否有 python_embeded 目录
            python_embeded_path = os.path.join(path, "python_embeded")
            if not os.path.exists(python_embeded_path):
                print(f"未找到 python_embeded 目录: {python_embeded_path}")
                print("请确认这是正确的 ComfyUI 便携版目录")
                continue
            
            return path
        except KeyboardInterrupt:
            print("\n用户取消操作")
            sys.exit(1)

def get_desktop_config_path():
    """获取桌面版配置文件路径"""
    import platform
    if platform.system() == "Windows":
        user_dir = os.path.expanduser("~")
        return os.path.join(user_dir, "AppData", "Roaming", "ComfyUI", "extra_models_config.yaml")
    else:
        # Linux/Mac 支持
        user_dir = os.path.expanduser("~")
        return os.path.join(user_dir, ".config", "ComfyUI", "extra_models_config.yaml")

def load_yaml_config(yaml_path):
    """加载 YAML 配置文件"""
    if not os.path.exists(yaml_path):
        return {}
    try:
        with open(yaml_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or {}
    except Exception as e:
        print(f"[WARN] Failed to load {yaml_path}: {e}")
        return {}

def get_paths(version_type, portable_path=None):
    """获取 base_path 和 custom_nodes 路径"""
    if version_type == "portable":
        print("使用便携版配置...")
        # 便携版：从指定目录的 extra_model_paths.yaml 读取
        if portable_path is None:
            raise ValueError("portable_path cannot be None for portable version")
        default_base_path = os.path.join(portable_path, "ComfyUI")
        default_custom_nodes = os.path.join(portable_path, "ComfyUI", "custom_nodes")
        yaml_path = os.path.join(portable_path, "ComfyUI", "extra_model_paths.yaml")
        config = load_yaml_config(yaml_path)
        
        # 优先查找 comfyui 块
        comfyui_block = config.get("comfyui", {}) if isinstance(config, dict) else {}
        base_path = comfyui_block.get('base_path', default_base_path)
        custom_nodes_path = comfyui_block.get('custom_nodes', default_custom_nodes)
    else:
        print("使用桌面版配置...")
        # 桌面版：从用户目录的 extra_models_config.yaml 读取
        yaml_path = get_desktop_config_path()
        config = load_yaml_config(yaml_path)
        
        # 查找 comfyui_desktop 块
        comfyui_desktop_block = config.get("comfyui_desktop", {}) if isinstance(config, dict) else {}
        base_path = comfyui_desktop_block.get('base_path', "ComfyUI")
        custom_nodes_path = comfyui_desktop_block.get('custom_nodes', "custom_nodes/")
        
        # 桌面版的 custom_nodes 是相对路径，需要和 base_path 拼接
        if not os.path.isabs(custom_nodes_path):
            custom_nodes_path = os.path.join(base_path, custom_nodes_path)
    
    # 兼容绝对/相对路径
    if not os.path.isabs(base_path):
        base_path = os.path.abspath(base_path)
    if not os.path.isabs(custom_nodes_path):
        custom_nodes_path = os.path.abspath(custom_nodes_path)
    
    return base_path, custom_nodes_path

def get_venv_python(base_path):
    """获取虚拟环境 Python 路径"""
    if os.name == 'nt':  # Windows
        venv_python = os.path.join(base_path, ".venv", "Scripts", "python.exe")
    else:  # Linux/Mac
        venv_python = os.path.join(base_path, ".venv", "bin", "python")
    
    if not os.path.exists(venv_python):
        raise FileNotFoundError(f"Python venv not found: {venv_python}")
    
    return venv_python

def replace_git_urls(content, github_mirror_prefix):
    """替换 requirements.txt 中的 GitHub URLs"""
    return content.replace('@git+https://github.com/', f'@{github_mirror_prefix}git+https://github.com/')

def install_requirements(venv_python, req_file, github_mirror_prefix, pip_mirror_url):
    """安装单个 requirements.txt 文件"""
    print(f"Processing requirements: {req_file}")
    
    # 检查文件是否存在且非空
    if not os.path.exists(req_file):
        print(f"  [INFO] {req_file} does not exist, skipping.")
        return
    
    file_size = os.path.getsize(req_file)
    if file_size == 0:
        print(f"  [INFO] {req_file} is empty, skipping.")
        return
    
    # 读取并替换 GitHub URLs
    try:
        with open(req_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 替换 GitHub URLs
        modified_content = replace_git_urls(content, github_mirror_prefix)
        
        # 创建临时文件
        temp_file = req_file + ".mirrored"
        with open(temp_file, 'w', encoding='utf-8') as f:
            f.write(modified_content)
        
        try:
            # 安装依赖
            subprocess.run([venv_python, "-m", "pip", "install", "-r", temp_file, "--index-url", pip_mirror_url], 
                         check=True)
            
        finally:
            # 清理临时文件
            if os.path.exists(temp_file):
                os.remove(temp_file)
                
    except Exception as e:
        print(f"  [ERROR] Failed to process {req_file}: {e}")

def main():
    """主函数"""
    # 镜像前缀配置
    github_mirror_prefix = "https://ghproxy.com/"
    pip_mirror_url = "https://pypi.tuna.tsinghua.edu.cn/simple"
    
    try:
        # 获取用户选择
        version_type = get_user_choice()
        
        # 如果是便携版，获取路径
        portable_path = None
        if version_type == "portable":
            portable_path = get_portable_path()
        
        # 获取路径
        base_path, custom_nodes_path = get_paths(version_type, portable_path)
        print(f"Using base_path: {base_path}")
        print(f"Using custom_nodes directory: {custom_nodes_path}")
        
        # 获取虚拟环境 Python
        venv_python = get_venv_python(base_path)
        print(f"Using Python: {venv_python}")
        
        # 只升级一次 pip
        print("Upgrading pip in venv ...")
        subprocess.run([venv_python, "-m", "pip", "install", "--upgrade", "pip", "--index-url", pip_mirror_url], 
                     check=True, capture_output=True)
        
        # 检查 custom_nodes 目录是否存在
        if not os.path.exists(custom_nodes_path):
            print(f"[ERROR] Directory {custom_nodes_path} does not exist!")
            return 1
        
        # 遍历一级子目录
        custom_nodes_dir = Path(custom_nodes_path)
        for subdir in custom_nodes_dir.iterdir():
            if subdir.is_dir():
                req_file = subdir / "requirements.txt"
                if req_file.exists():
                    install_requirements(str(venv_python), str(req_file), github_mirror_prefix, pip_mirror_url)
        
        print("Installation completed successfully!")
        return 0
        
    except Exception as e:
        print(f"[ERROR] {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
