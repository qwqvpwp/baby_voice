# -*- coding: utf-8 -*-
"""
外部 API 代理服务 - 调用外部语音情感识别 API
"""
import requests


def call_external_api(audio_path, api_url, api_key):
    headers = {"Authorization": f"Bearer {api_key}"}
    with open(audio_path, "rb") as f:
        files = {"audio": f}
        data = {"model": "emotion_classifier"}
        response = requests.post(
            api_url, headers=headers, files=files, data=data, timeout=30
        )

    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"API 调用失败: {response.status_code} - {response.text}")