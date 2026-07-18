# -*- coding: utf-8 -*-
"""
认证中间件 - API Key 校验
"""
import functools
from flask import request, jsonify
from config import API_KEYS, REQUIRE_AUTH

PUBLIC_ENDPOINTS = {"/", "/api/health"}


def require_api_key(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        if not REQUIRE_AUTH:
            return func(*args, **kwargs)

        if request.path in PUBLIC_ENDPOINTS:
            return func(*args, **kwargs)

        api_key = request.headers.get("X-API-Key")

        if not api_key:
            return jsonify({"error": "缺少 API Key", "code": 401}), 401

        if api_key not in API_KEYS:
            return jsonify({"error": "无效的 API Key", "code": 403}), 403

        return func(*args, **kwargs)

    return wrapper