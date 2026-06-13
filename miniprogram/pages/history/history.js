/**
 * 历史记录页面
 */
const storage = require('../../utils/storage');

Page({
  data: {
    history: []
  },

  onShow() {
    this.loadHistory();
  },

  loadHistory() {
    const history = storage.getHistory();
    // 预计算 WXML 无法处理的表达式
    history.forEach(item => {
      item.confPercent = ((item.confidence || 0) * 100).toFixed(1);
    });
    this.setData({ history });
  },

  // 格式化时间
  formatTime(ts) {
    if (!ts) return '';
    const d = new Date(ts);
    const now = new Date();
    const diff = now - d;

    if (diff < 60000) return '刚刚';
    if (diff < 3600000) return Math.floor(diff / 60000) + '分钟前';
    if (diff < 86400000) return Math.floor(diff / 3600000) + '小时前';

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
      title: '确认删除',
      content: '确定要删除这条记录吗？',
      success: (res) => {
        if (res.confirm) {
          storage.deleteRecord(id);
          this.loadHistory();
          wx.showToast({ title: '已删除', icon: 'success', duration: 1000 });
        }
      }
    });
  },

  // 清空全部
  clearAll() {
    wx.showModal({
      title: '确认清空',
      content: '确定要清空所有历史记录吗？',
      success: (res) => {
        if (res.confirm) {
          storage.clearHistory();
          this.loadHistory();
          wx.showToast({ title: '已清空', icon: 'success', duration: 1000 });
        }
      }
    });
  }
});