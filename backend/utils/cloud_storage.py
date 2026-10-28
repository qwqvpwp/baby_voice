# -*- coding: utf-8 -*-
"""
云存储工具 - 从微信云托管对象存储下载文件
支持通过 HTTP URL 下载配置文件和模型文件
"""
import os
import json
import hashlib
import tempfile
import requests as http_requests


def download_file(url, dest_path, timeout=60, retries=3):
    """
    从 URL 下载文件到指定路径

    参数:
        url: 文件下载 URL
        dest_path: 本地保存路径
        timeout: 下载超时时间（秒）
        retries: 重试次数
    """
    dest_dir = os.path.dirname(dest_path)
    if dest_dir and not os.path.exists(dest_dir):
        os.makedirs(dest_dir, exist_ok=True)

    for attempt in range(retries):
        try:
            print(f"  下载文件 (尝试 {attempt + 1}/{retries}): {url}")
            resp = http_requests.get(url, timeout=timeout, stream=True)
            resp.raise_for_status()

            with open(dest_path, 'wb') as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)

            file_size = os.path.getsize(dest_path)
            print(f"  下载成功: {dest_path} ({file_size} bytes)")
            return True
        except http_requests.exceptions.RequestException as e:
            print(f"  下载失败 (尝试 {attempt + 1}/{retries}): {e}")
            if attempt < retries - 1:
                continue
            else:
                print(f"  下载最终失败: {url}")
                return False


def download_json_config(url, cache_dir=None):
    """
    从云存储下载 JSON 配置文件

    参数:
        url: JSON 文件的下载 URL
        cache_dir: 缓存目录，默认为系统临时目录
    返回:
        dict: 解析后的 JSON 数据
    """
    if cache_dir is None:
        cache_dir = os.path.join(tempfile.gettempdir(), 'baby_voice_config')

    os.makedirs(cache_dir, exist_ok=True)

    url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
    local_path = os.path.join(cache_dir, f'config_{url_hash}.json')

    if os.path.exists(local_path):
        print(f"  使用缓存的配置文件: {local_path}")
        with open(local_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    if download_file(url, local_path):
        with open(local_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    else:
        raise RuntimeError(f"无法下载配置文件: {url}")


def download_model_file(url, dest_dir, model_name, cache=True):
    """
    从云存储下载模型文件

    参数:
        url: 模型文件的下载 URL
        dest_dir: 本地保存目录
        model_name: 模型名称（用于生成文件名）
        cache: 是否缓存（避免重复下载）
    返回:
        str: 本地文件路径
    """
    os.makedirs(dest_dir, exist_ok=True)

    local_path = os.path.join(dest_dir, model_name)

    if cache and os.path.exists(local_path):
        file_size = os.path.getsize(local_path)
        if file_size > 1000:
            print(f"  使用缓存的模型文件: {local_path}")
            return local_path

    if download_file(url, local_path, timeout=300):
        return local_path
    else:
        raise RuntimeError(f"无法下载模型文件: {url}")
