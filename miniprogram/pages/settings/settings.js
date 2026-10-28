/**
 * 设置页面
 */
const app = getApp();
const crypto = require('../../utils/crypto');
const i18n = require('../../utils/i18n');

Page({
  data: {
    currentModel: 'cnn_lstm',
    apiUrl: '',
    apiKey: '',
    // 多语言文案
    t: {},
    locale: 'zh'
  },

  onShow() {
    // 同步导航栏标题
    i18n.applyNavTitle();
    // 注入多语言字典（语言可能在其他页面被切换——虽然只有此页能切，但保持一致性）
    i18n.tPage(this);
    this.loadSettings();
  },

  loadSettings() {
    const model = app.getModel();
    const apiKey = crypto.getApiKey('default');

    this.setData({
      currentModel: model,
      apiKey: apiKey
    });
  },

  // 切换模型
  switchModel(e) {
    const model = e.currentTarget.dataset.model;
    app.setModel(model);
    this.setData({ currentModel: model });
    wx.showToast({ title: i18n.t('toast_switched'), icon: 'success', duration: 1000 });
  },

  // 切换语言
  switchLanguage(e) {
    const locale = e.currentTarget.dataset.locale;
    const changed = app.setLocale(locale);
    if (changed) {
      // 重新注入字典
      i18n.tPage(this);
      // 提示（用新语言）
      wx.showToast({ title: i18n.t('language_switched'), icon: 'success', duration: 1000 });
    }
  },

  // API Key 输入
  onApiKeyChange(e) {
    this.setData({ apiKey: e.detail.value });
  },

  // API 地址输入
  onApiUrlChange(e) {
    this.setData({ apiUrl: e.detail.value });
  },

  // 保存 API Key
  saveApiKey() {
    const apiKey = this.data.apiKey.trim();
    if (!apiKey) {
      wx.showToast({ title: i18n.t('toast_enter_api_key'), icon: 'none' });
      return;
    }
    crypto.saveApiKey('default', apiKey);
    wx.showToast({ title: i18n.t('toast_api_key_saved'), icon: 'success', duration: 1500 });
  }
});
