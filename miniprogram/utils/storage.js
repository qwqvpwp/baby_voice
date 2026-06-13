/**
 * 本地存储模块
 * 管理识别历史记录
 */

const HISTORY_KEY = 'emotion_history';
const MAX_HISTORY = 200; // 最多保存 200 条

/**
 * 保存一条识别记录
 * @param {object} record - { emotion, emo_cn, confidence, probabilities, model_used, timestamp }
 */
function addRecord(record) {
  const history = getHistory();

  // 添加时间戳
  record.timestamp = record.timestamp || new Date().toISOString();
  record.id = Date.now().toString(36) + Math.random().toString(36).substr(2, 5);

  history.unshift(record);

  // 限制最大条数
  if (history.length > MAX_HISTORY) {
    history.length = MAX_HISTORY;
  }

  wx.setStorageSync(HISTORY_KEY, history);
  return record;
}

/**
 * 获取所有历史记录
 */
function getHistory() {
  return wx.getStorageSync(HISTORY_KEY) || [];
}

/**
 * 删除指定记录
 * @param {string} id
 */
function deleteRecord(id) {
  const history = getHistory().filter(item => item.id !== id);
  wx.setStorageSync(HISTORY_KEY, history);
}

/**
 * 清空所有历史
 */
function clearHistory() {
  wx.setStorageSync(HISTORY_KEY, []);
}

/**
 * 获取历史记录条数
 */
function getHistoryCount() {
  return getHistory().length;
}

module.exports = {
  addRecord,
  getHistory,
  deleteRecord,
  clearHistory,
  getHistoryCount
};