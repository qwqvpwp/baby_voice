/**
 * 历史记录页面
 */
const storage = require('../../utils/storage');
const i18n = require('../../utils/i18n');

Page({
  data: {
    history: [],
    // 多语言文案
    t: {},
    locale: 'zh'
  },

  onShow() {
    // 同步导航栏标题
    i18n.applyNavTitle();
    // 注入多语言字典（语言可能在设置页被切换）
    i18n.tPage(this);
    this.loadHistory();
  },

  loadHistory() {
    const history = storage.getHistory();
    // 预计算 WXML 无法处理的表达式；同时按当前语言翻译情绪标签
    history.forEach(item => {
      item.confPercent = ((item.confidence || 0) * 100).toFixed(1);
      // 情绪标签按当前语言重新翻译（基于 emotion 字段）
      if (item.emotion) {
        item.emo_cn = i18n.tEmotion(item.emotion);
      }
      // 预格式化时间字符串（含本地化）
      item.timeText = this.formatTime(item.timestamp);
    });
    this.setData({ history });
  },

  // 格式化时间（按当前语言）
  formatTime(ts) {
    if (!ts) return '';
    const d = new Date(ts);
    const now = new Date();
    const diff = now - d;

    if (diff < 60000) return i18n.t('time_just_now');
    if (diff < 3600000) return Math.floor(diff / 60000) + i18n.t('time_min_ago');
    if (diff < 86400000) return Math.floor(diff / 3600000) + i18n.t('time_hour_ago');

    const month = (d.getMonth() + 1).toString().padStart(2, '0');
    const day = d.getDate().toString().padStart(2, '0');
    const h = d.getHours().toString().padStart(2, '0');
    const m = d.getMinutes().toString().padStart(2, '0');
    return `${month}-${day} ${h}:${m}`;
  },

  // 删除单条
  deleteOne(e) {
    const id = e.currentTarget.dataset.id;
    wx.showModal({
      title: i18n.t('dlg_confirm_delete'),
      content: i18n.t('dlg_delete_msg'),
      success: (res) => {
        if (res.confirm) {
          storage.deleteRecord(id);
          this.loadHistory();
          wx.showToast({ title: i18n.t('dlg_deleted'), icon: 'success', duration: 1000 });
        }
      }
    });
  },

  // 清空全部
  clearAll() {
    wx.showModal({
      title: i18n.t('dlg_confirm_clear'),
      content: i18n.t('dlg_clear_msg'),
      success: (res) => {
        if (res.confirm) {
          storage.clearHistory();
          this.loadHistory();
          wx.showToast({ title: i18n.t('dlg_cleared'), icon: 'success', duration: 1000 });
        }
      }
    });
  }
});
