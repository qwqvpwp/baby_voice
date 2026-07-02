# -*- coding: utf-8 -*-
"""
音频工具函数 - 处理音频文件相关操作
"""
import os
import tempfile
import base64

from pydub import AudioSegment

# 支持的输入格式 → 目标格式映射
SUPPORTED_CONVERSIONS = {
    "m4a":  ["wav"],
    "mp3":  ["wav"],
    "wav":  ["wav"],
    "ogg":  ["wav"],
    "flac": ["wav"],
    "aac":  ["wav"],
    "wma":  ["wav"],
    "opus": ["wav"],
    "webm": ["wav"],
}


def get_supported_formats():
    """返回当前支持的格式列表"""
    return {
        "input_formats": list(SUPPORTED_CONVERSIONS.keys()),
        "output_formats": ["wav"],
        "conversions": SUPPORTED_CONVERSIONS,
    }


def convert_audio(input_path, target_format="wav"):
    """
    将音频文件转换为目标格式。
    返回转换后的临时文件路径，调用方负责清理。
    """
    ext = os.path.splitext(input_path)[1].lower().lstrip(".")
    if ext not in SUPPORTED_CONVERSIONS:
        raise ValueError(
            f"不支持的输入格式: .{ext}，支持的格式: {list(SUPPORTED_CONVERSIONS.keys())}"
        )
    if target_format not in SUPPORTED_CONVERSIONS.get(ext, []):
        raise ValueError(f"不支持将 .{ext} 转换为 .{target_format}")

    audio = AudioSegment.from_file(input_path, format=ext if ext != "m4a" else "mp4")
    out_path = tempfile.NamedTemporaryFile(
        suffix=f".{target_format}", delete=False
    ).name
    audio.export(out_path, format=target_format)
    return out_path


def save_audio_file(audio_file):
    filename = audio_file.filename or "audio.wav"
    _, ext = os.path.splitext(filename)
    if not ext:
        ext = ".wav"
    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
        audio_file.save(tmp.name)
        return tmp.name


def save_base64_audio(audio_b64, suffix=".wav"):
    audio_bytes = base64.b64decode(audio_b64)
    if not suffix.startswith("."):
        suffix = f".{suffix}"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(audio_bytes)
        return tmp.name


def cleanup_temp_file(file_path):
    if os.path.exists(file_path):
        os.remove(file_path)