# -*- coding: utf-8 -*-
"""
转换控制器 - 提供音频格式转换接口
"""
import base64
import os
import traceback

from flask import request, jsonify, send_file

from utils.audio_utils import (
    convert_audio,
    get_supported_formats,
    save_audio_file,
    save_base64_audio,
    cleanup_temp_file,
)


def formats():
    """查询支持的音频格式转换列表"""
    return jsonify(get_supported_formats())


def convert():
    """上传音频文件，转换为目标格式并返回。

    form 参数:
        audio: 音频文件 (multipart/form-data)
        target_format: 目标格式，默认 "wav"
    """
    if "audio" not in request.files:
        return jsonify({"error": "请上传音频文件", "code": 400}), 400

    audio_file = request.files["audio"]
    target_format = request.form.get("target_format", "wav")

    tmp_path = save_audio_file(audio_file)
    converted_path = None

    try:
        converted_path = convert_audio(tmp_path, target_format)
        original_name = os.path.splitext(audio_file.filename or "audio")[0]
        download_name = f"{original_name}.{target_format}"

        return send_file(
            converted_path,
            mimetype=f"audio/{'x-wav' if target_format == 'wav' else target_format}",
            as_attachment=True,
            download_name=download_name,
        )
    except Exception as e:
        return jsonify({
            "error": str(e),
            "traceback": traceback.format_exc(),
            "code": 500,
        }), 500
    finally:
        cleanup_temp_file(tmp_path)
        if converted_path:
            cleanup_temp_file(converted_path)


def convert_base64():
    """接收 base64 编码的音频，转换为目标格式后返回 base64。

    JSON body:
        audio: base64 编码的音频字符串
        target_format: 目标格式，默认 "wav"
        input_format: 输入音频格式后缀（如 "m4a", "mp3"），用于解码
    """
    body = request.get_json()
    if not body or "audio" not in body:
        return jsonify({"error": "缺少 audio 字段", "code": 400}), 400

    audio_b64 = body["audio"]
    target_format = body.get("target_format", "wav")
    input_format = body.get("input_format", "wav")

    tmp_path = save_base64_audio(audio_b64, suffix=input_format)
    converted_path = None

    try:
        converted_path = convert_audio(tmp_path, target_format)
        with open(converted_path, "rb") as f:
            converted_b64 = base64.b64encode(f.read()).decode("utf-8")

        return jsonify({
            "code": 200,
            "audio": converted_b64,
            "format": target_format,
        })
    except Exception as e:
        return jsonify({
            "error": str(e),
            "traceback": traceback.format_exc(),
            "code": 500,
        }), 500
    finally:
        cleanup_temp_file(tmp_path)
        if converted_path:
            cleanup_temp_file(converted_path)