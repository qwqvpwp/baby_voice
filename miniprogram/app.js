// 微信小程序 - 婴儿情绪识别
// 全局应用逻辑

App({
  globalData: {
    // 服务器地址（开发时填写局域网IP）
    serverUrl: 'http://10.133.18.154:5000',
    // 当前选择的模型
    currentModel: 'cnn_lstm',
    // 标签映射
    labels: {
      "awake": "醒了",
      "diaper": "换尿布",
      "hug": "要抱抱",
      "hungry": "饿了",
      "silence": "安静",
      "sleepy": "困了",
      "uncomfortable": "不舒服"
    },
    // 情绪对应的建议
    suggestions: {
      "hug": "宝宝可能需要安抚，可以抱一抱、轻拍背部",
      "hungry": "宝宝可能饿了，建议喂奶或辅食",
      "sleepy": "宝宝困了，可以哄睡、播放摇篮曲",
      "awake": "宝宝醒了，可以陪宝宝玩耍",
      "diaper": "宝宝可能需要换尿布了",
      "uncomfortable": "宝宝可能不舒服，检查衣物是否合适",
      "silence": "宝宝很安静，一切正常"
    },
    // 情绪对应的图标
    emoji: {
      "hug": "🤗",
      "hungry": "🍼",
      "sleepy": "😴",
      "awake": "👀",
      "diaper": "🧷",
      "uncomfortable": "😣",
      "silence": "😊"
    }
  },

  onLaunch() {
    // 从本地存储恢复设置
    const savedModel = wx.getStorageSync('currentModel');
    if (savedModel) this.globalData.currentModel = savedModel;

    const savedUrl = wx.getStorageSync('serverUrl');
    if (savedUrl) this.globalData.serverUrl = savedUrl;
  },

  // 获取标签中文名
  getLabelCN(en) {
    return this.globalData.labels[en] || en;
  },

  // 获取建议
  getSuggestion(en) {
    return this.globalData.suggestions[en] || '';
  },

  // 获取表情
  getEmoji(en) {
    return this.globalData.emoji[en] || '❓';
  },

  // 切换模型
  setModel(model) {
    this.globalData.currentModel = model;
    wx.setStorageSync('currentModel', model);
  },

  // 获取当前模型
  getModel() {
    return this.globalData.currentModel;
  }
});