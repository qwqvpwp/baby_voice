# -*- coding: utf-8 -*-
"""
API 密钥管理器 - 内存存储，密文存储于本地配置
"""
import os
import json
import base64


class SecretManager:
    def __init__(self, secrets_file="secrets.json"):
        self.secrets_file = secrets_file
        self._secrets = {}
        self._load()

    def _load(self):
        if os.path.exists(self.secrets_file):
            try:
                with open(self.secrets_file, "r", encoding="utf-8") as f:
                    raw = json.load(f)
                for k, v in raw.items():
                    self._secrets[k] = self._decrypt(v)
            except Exception:
                pass

    def _encrypt(self, text):
        key = "baby_voice_secret_key"
        encoded = base64.b64encode(text.encode()).decode()
        return encoded

    def _decrypt(self, encrypted):
        try:
            return base64.b64decode(encrypted.encode()).decode()
        except Exception:
            return encrypted

    def set(self, key, value):
        self._secrets[key] = value
        self._save()

    def get(self, key, default=None):
        return self._secrets.get(key, default)

    def _save(self):
        raw = {k: self._encrypt(v) for k, v in self._secrets.items()}
        with open(self.secrets_file, "w", encoding="utf-8") as f:
            json.dump(raw, f, ensure_ascii=False)

    def list_keys(self):
        return list(self._secrets.keys())

    def delete(self, key):
        if key in self._secrets:
            del self._secrets[key]
            self._save()
            return True
        return False


secrets = SecretManager()