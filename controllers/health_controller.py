# -*- coding: utf-8 -*-
"""
健康检查控制器 - 提供服务状态检查接口
"""
from flask import jsonify


def home():
    return jsonify({
        "service": "baby-voice-classifier",
        "version": "1.0",
        "endpoints": {
            "/api/health": "GET - 健康检查",
            "/api/info": "GET - 模型信息",
            "/api/predict": "POST - 音频预测 (multipart/form-data)",
            "/api/predict/base64": "POST - Base64 音频预测",
            "/api/secrets": "POST - 设置 API 密钥"
        }
    })


def health():
    return jsonify({"status": "ok", "service": "baby-voice-classifier"})