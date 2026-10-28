// 微信小程序 - 婴儿情绪识别
// 全局应用逻辑
const i18n = require('./utils/i18n');

App({
  globalData: {
    // 微信云托管配置
    cloudEnv: 'prod-d9g27kn89d2786475',
    cloudService: 'flask-tgsf',
    // API Key（与服务器配置一致）
    apiKey: 'your-secret-key',
    // 当前选择的模型
    currentModel: 'cnn_lstm'
  },

  onLaunch() {
    // 初始化多语言（从本地存储恢复）
    i18n.init();

    // 初始化微信云托管
    wx.cloud.init({
      env: this.globalData.cloudEnv
    });

    // 从本地存储恢复设置
    const savedModel = wx.getStorageSync('currentModel');
    if (savedModel) this.globalData.currentModel = savedModel;

    // 应用语言到 tabBar
    i18n.applyTabBarText();
  },

  // 获取情绪标签文案（按当前语言）
  getLabelCN(en) {
    return i18n.tEmotion(en);
  },

  // 获取建议文案（按当前语言）
  getSuggestion(en) {
    return i18n.tSuggestion(en);
  },

  // 获取表情（emoji 与语言无关，保持原映射）
  getEmoji(en) {
    const emojiMap = {
      "hug": "🤗",
      "hungry": "🍼",
      "sleepy": "😴",
      "awake": "👀",
      "diaper": "🧷",
      "uncomfortable": "😣",
      "silence": "😊"
    };
    return emojiMap[en] || '❓';
  },

  // 切换模型
  setModel(model) {
    this.globalData.currentModel = model;
    wx.setStorageSync('currentModel', model);
  },

  // 获取当前模型
  getModel() {
    return this.globalData.currentModel;
  },

  // 切换语言
  setLocale(locale) {
    const changed = i18n.setLocale(locale, true);
    return changed;
  },

  // 获取当前语言
  getLocale() {
    return i18n.getLocale();
  },

  // 暴露 i18n 模块给页面直接使用
  i18n
});
