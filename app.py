# -*- coding: utf-8 -*-
"""
Flask API 服务 - 微信小程序后端
提供语音情感识别接口，支持模型切换和外部 API 代理
"""
import os
from flask import Flask
from flask_cors import CORS

from controllers.health_controller import home, health
from controllers.predict_controller import predict, predict_base64, info
from controllers.secret_controller import set_secret, delete_secret

app = Flask(__name__)
CORS(app)

app.add_url_rule("/", view_func=home, methods=["GET"])
app.add_url_rule("/api/health", view_func=health, methods=["GET"])
app.add_url_rule("/api/info", view_func=info, methods=["GET"])
app.add_url_rule("/api/predict", view_func=predict, methods=["POST"])
app.add_url_rule("/api/predict/base64", view_func=predict_base64, methods=["POST"])
app.add_url_rule("/api/secrets", view_func=set_secret, methods=["POST"])
app.add_url_rule("/api/secrets/<key>", view_func=delete_secret, methods=["DELETE"])

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"启动服务: http://127.0.0.1:{port}")
    app.run(host="127.0.0.1", port=port, debug=False)