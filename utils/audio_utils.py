# -*- coding: utf-8 -*-
"""
音频工具函数 - 处理音频文件相关操作
"""
import os
import tempfile
import base64


def save_audio_file(audio_file):
    filename = audio_file.filename or "audio.wav"
    _, ext = os.path.splitext(filename)
    if not ext:
        ext = ".wav"
    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
        audio_file.save(tmp.name)
        return tmp.name


def save_base64_audio(audio_b64):
    audio_bytes = base64.b64decode(audio_b64)
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp.write(audio_bytes)
        return tmp.name


def cleanup_temp_file(file_path):
    if os.path.exists(file_path):
        os.remove(file_path)