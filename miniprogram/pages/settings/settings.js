/**
 * 设置页面
 */
const app = getApp();
const crypto = require('../../utils/crypto');

Page({
  data: {
    currentModel: 'cnn_lstm',
    apiUrl: '',
    apiKey: '',
    serverUrl: ''
  },

  onShow() {
    this.loadSettings();
  },

  loadSettings() {
    const model = app.getModel();
    const serverUrl = app.globalData.serverUrl || 'http://localhost:5000';
    const apiKey = crypto.getApiKey('default');

    this.setData({
      currentModel: model,
      serverUrl: serverUrl,
      apiKey: apiKey
    });
  },

  // 切换模型
  switchModel(e) {
    const model = e.currentTarget.dataset.model;
    app.setModel(model);
    this.setData({ currentModel: model });
    wx.showToast({ title: '已切换', icon: 'success', duration: 1000 });
  },

  // API Key 输入
  onApiKeyChange(e) {
    this.setData({ apiKey: e.detail.value });
  },

  // API 地址输入
  onApiUrlChange(e) {
    this.setData({ apiUrl: e.detail.value });
  },

  // 服务器地址输入
  onServerUrlChange(e) {
    this.setData({ serverUrl: e.detail.value });
  },

  // 保存 API Key
  saveApiKey() {
    const apiKey = this.data.apiKey.trim();
    if (!apiKey) {
      wx.showToast({ title: '请输入 API Key', icon: 'none' });
      return;
    }
    crypto.saveApiKey('default', apiKey);
    wx.showToast({ title: 'API Key 已保存', icon: 'success', duration: 1500 });
  },

  // 保存服务器地址
  saveServerUrl() {
    const url = this.data.serverUrl.trim();
    if (!url) {
      wx.showToast({ title: '请输入服务器地址', icon: 'none' });
      return;
    }
    app.globalData.serverUrl = url;
    wx.setStorageSync('serverUrl', url);
    wx.showToast({ title: '服务器地址已保存', icon: 'success', duration: 1500 });
  }
});