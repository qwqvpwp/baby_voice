# -*- coding: utf-8 -*-
"""
语音情感推理模块
供微信小程序后端 API 调用
支持：本地模型推理 / 外部 API 代理
"""
import os
import json
import numpy as np
import librosa
import tensorflow as tf

# 导入自定义层
from models import PositionalEncoding


# ============ 配置 ============
PROCESSED_DIR = "processed_data"
MODELS_DIR = "models_output"
SAMPLE_RATE = 16000
N_MFCC = 40
N_TIME_STEPS = 128


class EmotionPredictor:
    """语音情感预测器"""

    def __init__(self):
        # 加载标签配置
        config_path = os.path.join(PROCESSED_DIR, "label_config.json")
        with open(config_path, "r", encoding="utf-8") as f:
            self.label_config = json.load(f)

        self.classes = self.label_config["classes"]
        self.cn_mapping = self.label_config["mapping"]
        self.id_to_class = {int(k): v for k, v in self.label_config["id_to_class"].items()}
        self.num_classes = len(self.classes)

        # 加载模型
        self.models = {}
        self._load_models()

    def _load_models(self):
        """加载所有可用模型"""
        model_files = {
            "cnn_lstm": os.path.join(MODELS_DIR, "cnn_lstm_final.h5"),
            "transformer": os.path.join(MODELS_DIR, "transformer_final.h5"),
        }
        custom_objects = {"PositionalEncoding": PositionalEncoding}

        for name, path in model_files.items():
            if not os.path.exists(path):
                print(f"  模型未找到: {name} ({path})")
                continue
            try:
                self.models[name] = tf.keras.models.load_model(path, custom_objects=custom_objects)
                print(f"  已加载模型: {name}")
            except Exception as e:
                print(f"  直接加载失败 {name}: {e}")
                try:
                    # 从保存的配置重建模型结构，再加载权重
                    import h5py
                    with h5py.File(path, "r") as f:
                        config = json.loads(f.attrs["model_config"])
                    model = tf.keras.models.model_from_json(
                        json.dumps(config), custom_objects=custom_objects
                    )
                    model.load_weights(path)
                    self.models[name] = model
                    print(f"  已加载模型 (从配置重建): {name}")
                except Exception as e2:
                    print(f"  加载模型失败 {name}: {e2}")

    def extract_features(self, audio_data, sr=SAMPLE_RATE):
        """从音频数据提取 MFCC 特征"""
        # 标准化
        if np.std(audio_data) > 1e-6:
            audio_data = (audio_data - np.mean(audio_data)) / np.std(audio_data)

        # 提取 MFCC
        mfcc = librosa.feature.mfcc(y=audio_data, sr=sr, n_mfcc=N_MFCC)

        # 统一时间维度
        if mfcc.shape[1] < N_TIME_STEPS:
            pad_width = N_TIME_STEPS - mfcc.shape[1]
            mfcc = np.pad(mfcc, ((0, 0), (0, pad_width)), mode="constant")
        else:
            mfcc = mfcc[:, :N_TIME_STEPS]

        # 添加 batch 和 channel 维度
        mfcc = mfcc[np.newaxis, ..., np.newaxis]  # (1, 40, 128, 1)
        return mfcc.astype(np.float32)

    def predict_file(self, file_path, model_name="cnn_lstm"):
        """对音频文件进行预测"""
        audio, sr = librosa.load(file_path, sr=SAMPLE_RATE)
        return self.predict(audio, sr, model_name)

    def predict(self, audio_data, sr=SAMPLE_RATE, model_name="cnn_lstm"):
        """
        对音频数据进行预测
        参数:
            audio_data: numpy array, 音频波形数据
            sr: 采样率
            model_name: 模型名称 ("cnn_lstm" 或 "transformer")
        返回:
            dict: {"emotion": "...", "emo_cn": "...", "confidence": 0.xx,
                   "probabilities": [{"class": "...", "cn": "...", "prob": 0.xx}, ...]}
        """
        if model_name not in self.models:
            available = list(self.models.keys())
            if not available:
                raise RuntimeError("没有可用的模型")
            model_name = available[0]

        features = self.extract_features(audio_data, sr)
        model = self.models[model_name]
        probs = model.predict(features, verbose=0)[0]  # (num_classes,)

        # 构建结果
        pred_idx = int(np.argmax(probs))
        emotion_en = self.id_to_class[pred_idx]
        emotion_cn = self.cn_mapping.get(emotion_en, emotion_en)

        probabilities = []
        for i in np.argsort(probs)[::-1]:
            cls_en = self.id_to_class[int(i)]
            probabilities.append({
                "class": cls_en,
                "cn": self.cn_mapping.get(cls_en, cls_en),
                "probability": round(float(probs[i]), 4)
            })

        return {
            "emotion": emotion_en,
            "emo_cn": emotion_cn,
            "confidence": round(float(probs[pred_idx]), 4),
            "probabilities": probabilities,
            "model_used": model_name
        }

    def get_available_models(self):
        """获取可用模型列表"""
        return list(self.models.keys())

    def get_label_info(self):
        """获取标签信息（供小程序初始化）"""
        return {
            "classes": self.classes,
            "cn_mapping": self.cn_mapping,
            "num_classes": self.num_classes
        }


# ============ Flask API（供小程序调用） ============
def create_api_app():
    """创建 Flask API 应用"""
    try:
        from flask import Flask, request, jsonify
        from flask_cors import CORS
    except ImportError:
        print("请安装 Flask: pip install flask flask-cors")
        return None

    app = Flask(__name__)
    CORS(app)
    predictor = EmotionPredictor()

    @app.route("/api/models", methods=["GET"])
    def get_models():
        """获取可用模型列表"""
        return jsonify({
            "models": predictor.get_available_models(),
            "labels": predictor.get_label_info()
        })

    @app.route("/api/predict", methods=["POST"])
    def predict():
        """语音预测接口"""
        if "audio" not in request.files:
            return jsonify({"error": "请上传音频文件"}), 400

        audio_file = request.files["audio"]
        model_name = request.form.get("model", "cnn_lstm")

        # 保存临时文件
        temp_path = "temp_audio.wav"
        audio_file.save(temp_path)

        try:
            result = predictor.predict_file(temp_path, model_name)
            return jsonify(result)
        except Exception as e:
            return jsonify({"error": str(e)}), 500
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    @app.route("/api/labels", methods=["GET"])
    def get_labels():
        """获取标签信息"""
        return jsonify(predictor.get_label_info())

    return app


if __name__ == "__main__":
    # 命令行测试
    import sys

    predictor = EmotionPredictor()
    print(f"\n可用模型: {predictor.get_available_models()}")
    print(f"标签信息: {json.dumps(predictor.get_label_info(), ensure_ascii=False, indent=2)}")

    if len(sys.argv) > 1:
        file_path = sys.argv[1]
        for model_name in predictor.get_available_models():
            print(f"\n{'=' * 50}")
            print(f"模型: {model_name}")
            print(f"{'=' * 50}")
            result = predictor.predict_file(file_path, model_name)
            print(f"  预测情绪: {result['emo_cn']} ({result['emotion']})")
            print(f"  置信度: {result['confidence']}")
            print(f"  所有概率:")
            for p in result["probabilities"]:
                print(f"    {p['cn']:6s} ({p['class']:15s}): {p['probability']:.4f}")