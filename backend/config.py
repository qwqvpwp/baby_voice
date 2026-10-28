# -*- coding: utf-8 -*-
"""
安全配置文件
"""
import os

SECRET_KEY = os.environ.get("APP_SECRET_KEY", "")

API_KEYS = set(os.environ.get("API_KEYS", "").split(",") if os.environ.get("API_KEYS") else [])

ALLOWED_ORIGINS = os.environ.get("ALLOWED_ORIGINS", "*").split(",")

REQUIRE_AUTH = os.environ.get("REQUIRE_AUTH", "false").lower() == "true"

LABEL_CONFIG_URL = os.environ.get("LABEL_CONFIG_URL", "")

MODEL_CNN_LSTM_URL = os.environ.get("MODEL_CNN_LSTM_URL", "")

MODEL_TRANSFORMER_URL = os.environ.get("MODEL_TRANSFORMER_URL", "")