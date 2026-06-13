# -*- coding: utf-8 -*-
"""
密钥管理控制器 - 提供 API 密钥管理接口
"""
from flask import request, jsonify
from services.secret_manager import secrets


def set_secret():
    body = request.get_json()
    if not body or "key" not in body or "value" not in body:
        return jsonify({"error": "缺少 key 或 value 字段", "code": 400}), 400

    secrets.set(body["key"], body["value"])
    return jsonify({"status": "ok", "key": body["key"]})


def delete_secret(key):
    if secrets.delete(key):
        return jsonify({"status": "ok"})
    return jsonify({"error": "密钥不存在", "code": 404}), 404