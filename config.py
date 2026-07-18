# -*- coding: utf-8 -*-
"""
安全配置文件
"""
import os

SECRET_KEY = os.environ.get("APP_SECRET_KEY", "")

API_KEYS = set(os.environ.get("API_KEYS", "").split(",") if os.environ.get("API_KEYS") else [])

ALLOWED_ORIGINS = os.environ.get("ALLOWED_ORIGINS", "*").split(",")

REQUIRE_AUTH = os.environ.get("REQUIRE_AUTH", "false").lower() == "true"