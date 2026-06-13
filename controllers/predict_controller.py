# -*- coding: utf-8 -*-
"""
预测控制器 - 提供音频情感识别接口
"""
from flask import request, jsonify
from services.predictor import predictor_service
from services.secret_manager import secrets
from services.external_api import call_external_api
from utils.audio_utils import save_audio_file, save_base64_audio, cleanup_temp_file


def predict():
    if "audio" not in request.files:
        return jsonify({"error": "请上传音频文件", "code": 400}), 400

    audio_file = request.files["audio"]
    model_name = request.form.get("model", "cnn_lstm")
    source = request.form.get("source", "local")

    tmp_path = save_audio_file(audio_file)

    try:
        if source == "api":
            api_url = request.form.get("api_url", "")
            api_key = secrets.get("default_api_key", "")
            result = call_external_api(tmp_path, api_url, api_key)
        else:
            result = predictor_service.predict(tmp_path, model_name)

        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e), "code": 500}), 500
    finally:
        cleanup_temp_file(tmp_path)


def predict_base64():
    body = request.get_json()
    if not body or "audio" not in body:
        return jsonify({"error": "缺少 audio 字段", "code": 400}), 400

    audio_b64 = body["audio"]
    model_name = body.get("model", "cnn_lstm")

    tmp_path = save_base64_audio(audio_b64)

    try:
        result = predictor_service.predict(tmp_path, model_name)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e), "code": 500}), 500
    finally:
        cleanup_temp_file(tmp_path)


def info():
    return jsonify({
        "models": predictor_service.get_available_models(),
        "labels": predictor_service.get_label_info(),
        "secrets": secrets.list_keys()
    })