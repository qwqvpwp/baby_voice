# -*- coding: utf-8 -*-
"""
预测器服务 - 本地模型推理封装
"""
from predict import EmotionPredictor


class PredictorService:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(PredictorService, cls).__new__(cls)
            cls._instance._predictor = None
        return cls._instance

    def _get_predictor(self):
        if self._predictor is None:
            self._predictor = EmotionPredictor()
        return self._predictor

    def predict(self, audio_path, model_name="cnn_lstm"):
        predictor = self._get_predictor()
        return predictor.predict_file(audio_path, model_name)

    def get_available_models(self):
        predictor = self._get_predictor()
        return predictor.get_available_models()

    def get_label_info(self):
        predictor = self._get_predictor()
        return predictor.get_label_info()


predictor_service = PredictorService()