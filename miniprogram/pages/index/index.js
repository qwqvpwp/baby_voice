/**
 * 主页面 - 录音识别逻辑
 */
const app = getApp();
const api = require('../../utils/api');
const storage = require('../../utils/storage');
const i18n = require('../../utils/i18n');

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
    errorMsg: '',
    // 多语言文案
    t: {},
    locale: 'zh'
  },

  onLoad() {
    // 注入多语言字典
    i18n.tPage(this);

    // 监听录音结束
    recorderManager.onStop((res) => {
      this.setData({
        hasRecorded: true,
        isRecording: false
      });
      if (this.data.recordTimer) {
        clearInterval(this.data.recordTimer);
        this.data.recordTimer = null;
      }

      // 验证录音
      if (!res.tempFilePath) {
        this.setData({ errorMsg: i18n.t('err_invalid_file') });
        return;
      }
      if (res.duration < 500) {
        this.setData({ errorMsg: i18n.t('err_too_short') });
        return;
      }

      // 读取录音文件为 base64（避免 wx.uploadFile 对录音临时文件兼容问题）
      const that = this;
      const fs = wx.getFileSystemManager();
      fs.readFile({
        filePath: res.tempFilePath,
        encoding: 'base64',
        success(fileRes) {
          that.analyzeRecording(fileRes.data);
        },
        fail(err) {
          that.setData({ errorMsg: i18n.t('err_read_file') + ': ' + (err.errMsg || '') });
        }
      });
    });

    recorderManager.onError((err) => {
      if (this.data.recordTimer) {
        clearInterval(this.data.recordTimer);
        this.data.recordTimer = null;
      }
      this.setData({
        isRecording: false,
        errorMsg: i18n.t('err_record_failed') + '：' + (err.errMsg || i18n.t('err_mic_permission'))
      });
    });
  },

  onShow() {
    // 同步导航栏标题
    i18n.applyNavTitle();
    // 同步语言字典（语言可能在设置页被切换）
    i18n.tPage(this);
    // 更新模型标签
    const model = app.getModel();
    this.setData({ modelLabel: i18n.tModel(model) });
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
      extension: ['wav'],
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
          that.setData({ errorMsg: i18n.t('err_choose_file') });
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

  // 分析录音（base64 方式）
  analyzeRecording(audioBase64) {
    const that = this;
    this.setData({ isAnalyzing: true, errorMsg: '' });

    const model = app.getModel();

    api.predictBase64(audioBase64, model).then(res => {
      that.processResult(res, model);
    }).catch(err => {
      that.setData({
        errorMsg: err.message || i18n.t('err_predict_failed'),
        isAnalyzing: false
      });
    });
  },

  // 分析文件上传
  analyze() {
    if (!this.data.recordFilePath) return;

    const that = this;
    this.setData({ isAnalyzing: true, errorMsg: '' });

    const model = app.getModel();

    api.predict(this.data.recordFilePath, model, {
      source: model === 'api' ? 'api' : 'local'
    }).then(res => {
      that.processResult(res, model);
    }).catch(err => {
      that.setData({
        errorMsg: err.message || i18n.t('err_predict_failed'),
        isAnalyzing: false
      });
    });
  },

  // 处理预测结果（recording 和 file upload 共用）
  processResult(res, model) {
    const resultEmotion = app.getLabelCN(res.emotion);
    const resultEmoji = app.getEmoji(res.emotion);
    const resultConfidence = (res.confidence * 100).toFixed(1);
    const suggestion = app.getSuggestion(res.emotion);

    // 处理概率列表 - 添加本地化名、是否为最高概率、进度条颜色
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

    const resultData = {
      emotion: res.emotion,
      emo_cn: resultEmotion,
      emoji: resultEmoji,
      confidence: res.confidence,
      probabilities: probabilities,
      model_used: res.model_used || model
    };

    this.setData({
      result: resultData,
      resultEmotion: resultEmotion,
      resultEmoji: resultEmoji,
      resultConfidence: resultConfidence,
      suggestion: suggestion,
      modelLabel: i18n.tModel(res.model_used || model),
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
  },

  getLabelCN(en) {
    return app.getLabelCN(en);
  }
});
