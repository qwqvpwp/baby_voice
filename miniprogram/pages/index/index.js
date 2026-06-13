/**
 * 主页面 - 录音识别逻辑
 */
const app = getApp();
const api = require('../../utils/api');
const storage = require('../../utils/storage');

// 录音管理器
const recorderManager = wx.getRecorderManager();

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

  onLoad() {
    // 监听录音结束
    recorderManager.onStop((res) => {
      this.setData({
        recordFilePath: res.tempFilePath,
        hasRecorded: true,
        isRecording: false
      });
      if (this.data.recordTimer) {
        clearInterval(this.data.recordTimer);
        this.data.recordTimer = null;
      }
      // 录音成功后自动分析
      this.analyze();
    });

    recorderManager.onError((err) => {
      if (this.data.recordTimer) {
        clearInterval(this.data.recordTimer);
        this.data.recordTimer = null;
      }
      this.setData({
        isRecording: false,
        errorMsg: '录音失败：' + (err.errMsg || '请授权麦克风权限')
      });
    });
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
    recorderManager.start({
      format: 'wav',
      sampleRate: 16000,
      numberOfChannels: 1,
      encodeBitRate: 96000,
      duration: 10000
    });
  },

  // 停止录音
  stopRecord() {
    if (this.data.recordTimer) {
      clearInterval(this.data.recordTimer);
      this.data.recordTimer = null;
    }
    this.setData({ isRecording: false });
    recorderManager.stop();
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

  // 从微信聊天选择音频文件
  chooseFromChat() {
    const that = this;
    wx.chooseMessageFile({
      count: 1,
      type: 'file',
      extension: ['wav', 'mp3', 'm4a', 'aac', 'ogg', 'flac', 'silk'],
      success(res) {
        const file = res.tempFiles[0];
        that.setData({
          recordFilePath: file.path,
          hasRecorded: true,
          errorMsg: '',
          result: null
        });
        that.analyze();
      },
      fail(err) {
        if (err.errMsg && err.errMsg.indexOf('cancel') === -1) {
          that.setData({ errorMsg: '选择文件失败' });
        }
      }
    });
  },

  // 从本地选择音频文件
  chooseFromFile() {
    const that = this;
    wx.chooseMedia({
      count: 1,
      mediaType: ['video'],
      sourceType: ['album'],
      maxDuration: 30,
      success(res) {
        const file = res.tempFiles[0];
        that.setData({
          recordFilePath: file.tempFilePath,
          hasRecorded: true,
          errorMsg: '',
          result: null
        });
        that.analyze();
      },
      fail(err) {
        // chooseMedia 不支持纯音频，回退到 chooseMessageFile
        that.chooseFromChat();
      }
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
    });
  },

  getLabelCN(en) {
    return app.getLabelCN(en);
  }
});