/**
 * 主页面 - 录音识别逻辑
 */
const app = getApp();
const api = require('../../utils/api');
const storage = require('../../utils/storage');

Page({
  data: {
    isRecording: false,
    hasRecorded: false,
    isAnalyzing: false,
    recordingTime: 0,
    recordTimer: null,
    recordFilePath: '',
    result: null,
    resultEmotion: '',
    resultEmoji: '',
    resultConfidence: 0,
    suggestion: '',
    modelLabel: '',
    errorMsg: ''
  },

  onShow() {
    // 更新模型标签
    const model = app.getModel();
    const modelLabels = {
      'cnn_lstm': 'CNN-LSTM 模型',
      'transformer': 'Transformer 模型',
      'api': '外部API'
    };
    this.setData({ modelLabel: modelLabels[model] || model });
  },

  // 切换录音状态
  toggleRecord() {
    if (this.data.isRecording) {
      this.stopRecord();
    } else {
      this.startRecord();
    }
  },

  // 开始录音
  startRecord() {
    const that = this;
    this.setData({ isRecording: true, recordingTime: 0, errorMsg: '', result: null });

    // 开始计时
    const timer = setInterval(() => {
      if (that.data.recordingTime >= 10) {
        that.stopRecord();
        return;
      }
      that.setData({ recordingTime: that.data.recordingTime + 1 });
    }, 1000);
    this.data.recordTimer = timer;

    // 启动录音
    wx.startRecord({
      success(res) {
        that.setData({
          recordFilePath: res.tempFilePath,
          hasRecorded: true
        });
        // 录音成功后自动分析
        that.analyze();
      },
      fail(err) {
        clearInterval(that.data.recordTimer);
        that.setData({
          isRecording: false,
          errorMsg: '录音失败：' + (err.errMsg || '请授权麦克风权限')
        });
      }
    });
  },

  // 停止录音
  stopRecord() {
    if (this.data.recordTimer) {
      clearInterval(this.data.recordTimer);
      this.data.recordTimer = null;
    }
    this.setData({ isRecording: false });
    wx.stopRecord();
  },

  // 重新录制
  reRecord() {
    this.setData({
      result: null,
      hasRecorded: false,
      recordFilePath: '',
      recordingTime: 0,
      errorMsg: ''
    });
  },

  // 分析录音
  analyze() {
    if (!this.data.recordFilePath) return;

    const that = this;
    this.setData({ isAnalyzing: true, errorMsg: '' });

    const model = app.getModel();

    api.predict(this.data.recordFilePath, model, {
      source: model === 'api' ? 'api' : 'local'
    }).then(res => {
      const resultEmotion = that.getLabelCN(res.emotion);
      const resultEmoji = app.getEmoji(res.emotion);
      const resultConfidence = (res.confidence * 100).toFixed(1);
      const suggestion = app.getSuggestion(res.emotion);

      // 处理概率列表 - 添加中文名、是否为最高概率、进度条颜色
      const maxProb = Math.max(...(res.probabilities || []).map(p => p.probability));
      const probabilities = (res.probabilities || []).map(p => {
        const isMax = p.probability === maxProb && maxProb > 0;
        return {
          ...p,
          cn: app.getLabelCN(p.class),
          isMax: isMax,
          barWidth: (p.probability * 100).toFixed(1),
          barColor: isMax ? 'linear-gradient(90deg, #FF6B81, #FF8E9E)' : '#E0E0E0',
          probPercent: (p.probability * 100).toFixed(1)
        };
      });

      const modelLabels = {
        'cnn_lstm': 'CNN-LSTM 模型',
        'transformer': 'Transformer 模型',
        'api': '外部API'
      };

      const resultData = {
        emotion: res.emotion,
        emo_cn: resultEmotion,
        emoji: resultEmoji,
        confidence: res.confidence,
        probabilities: probabilities,
        model_used: res.model_used || model
      };

      that.setData({
        result: resultData,
        resultEmotion: resultEmotion,
        resultEmoji: resultEmoji,
        resultConfidence: resultConfidence,
        suggestion: suggestion,
        modelLabel: modelLabels[res.model_used || model] || res.model_used,
        isAnalyzing: false
      });

      // 保存到历史记录
      storage.addRecord({
        emotion: res.emotion,
        emo_cn: resultEmotion,
        emoji: resultEmoji,
        confidence: res.confidence,
        probabilities: probabilities.slice(0, 3),
        model_used: res.model_used || model
      });
    }).catch(err => {
      that.setData({
        errorMsg: err.message || '识别失败',
        isAnalyzing: false
      });

      // 后端不通时的本地模拟数据（用于演示）
      if (err.message.includes('连接失败')) {
        that.mockAnalyze();
      }
    });
  },

  // 本地模拟分析（后端不可用时使用）
  mockAnalyze() {
    const that = this;
    const emotions = ['hug', 'hungry', 'sleepy', 'awake', 'diaper', 'uncomfortable', 'silence'];
    const randomIdx = Math.floor(Math.random() * emotions.length);
    const emotion = emotions[randomIdx];

    const probabilities = emotions.map((e, i) => {
      const isMain = i === randomIdx;
      return {
        class: e,
        cn: app.getLabelCN(e),
        probability: isMain ? 0.45 + Math.random() * 0.3 : Math.random() * 0.2
      };
    });
    // 归一化
    const sum = probabilities.reduce((s, p) => s + p.probability, 0);
    probabilities.forEach(p => p.probability = p.probability / sum);
    probabilities.sort((a, b) => b.probability - a.probability);

    // 添加预计算字段
    const maxProb = probabilities[0].probability;
    probabilities.forEach(p => {
      p.cn = app.getLabelCN(p.class);
      p.isMax = p.probability === maxProb && maxProb > 0;
      p.barWidth = (p.probability * 100).toFixed(1);
      p.barColor = p.isMax ? 'linear-gradient(90deg, #FF6B81, #FF8E9E)' : '#E0E0E0';
      p.probPercent = (p.probability * 100).toFixed(1);
    });

    const result = {
      emotion: emotion,
      emo_cn: app.getLabelCN(emotion),
      emoji: app.getEmoji(emotion),
      confidence: probabilities[0].probability,
      probabilities: probabilities,
      model_used: app.getModel()
    };

    that.setData({
      result: result,
      resultEmotion: result.emo_cn,
      resultEmoji: result.emoji,
      resultConfidence: (result.confidence * 100).toFixed(1),
      suggestion: app.getSuggestion(emotion),
      modelLabel: '本地模拟',
      isAnalyzing: false,
      errorMsg: ''
    });

    storage.addRecord(result);
  },

  getLabelCN(en) {
    return app.getLabelCN(en);
  }
});