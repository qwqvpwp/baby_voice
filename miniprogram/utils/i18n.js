/**
 * 多语言模块（简体中文 / 英语）
 *
 * 用法：
 *   const i18n = require('../../utils/i18n');
 *   i18n.t('key');                 // 翻译
 *   i18n.setLocale('en');          // 切换语言（自动持久化 + 自动刷新 tabBar）
 *   i18n.getLocale();
 *   i18n.tPage(pageInstance);      // 把 t 函数注入页面，便于 WXML 使用 {{t.xxx}}
 */

const LOCALE_KEY = 'app_locale';
const SUPPORTED = ['zh', 'en'];

// 翻译字典
const DICT = {
  zh: {
    // App 全局
    appTitle: '婴儿情绪识别',

    // tabBar
    tab_record: '识别',
    tab_history: '历史',
    tab_settings: '设置',

    // 首页
    title: '婴儿情绪识别',
    subtitle: '录制宝宝哭声，AI 帮您理解宝宝需求',
    tapToRecord: '点击开始录音（最长10秒）',
    recording: '录音中...',
    reRecord: '重新录制',
    or: '或',
    pickFromChat: '从聊天记录选择',
    pickFromFile: '从本地文件选择',
    analyzing: '正在分析中...',
    confidence: '置信度',
    allProbabilities: '所有情绪概率',

    // 首页错误
    err_invalid_file: '录音文件无效',
    err_too_short: '录音时间太短，请录制 1 秒以上',
    err_read_file: '读取录音失败',
    err_record_failed: '录音失败',
    err_mic_permission: '请授权麦克风权限',
    err_choose_file: '选择文件失败',
    err_predict_failed: '识别失败',

    // 模型名
    model_cnn_lstm: 'CNN-LSTM 模型',
    model_transformer: 'Transformer 模型',
    model_api: '外部API',

    // 历史页
    history_title: '识别历史',
    history_clear_all: '清空全部',
    history_empty: '暂无识别记录',
    history_empty_tip: '去首页录制宝宝声音吧',
    history_delete: '删除',
    time_just_now: '刚刚',
    time_min_ago: '分钟前',
    time_hour_ago: '小时前',

    // 历史 dialog
    dlg_confirm_delete: '确认删除',
    dlg_delete_msg: '确定要删除这条记录吗？',
    dlg_deleted: '已删除',
    dlg_confirm_clear: '确认清空',
    dlg_clear_msg: '确定要清空所有历史记录吗？',
    dlg_cleared: '已清空',

    // 设置页
    settings_model: '模型选择',
    settings_model_desc: '选择用于语音识别的模型',
    settings_model_cnn_lstm: 'CNN-LSTM 混合模型',
    settings_model_cnn_lstm_desc: '卷积 + 时序网络，适合实时推理',
    settings_model_transformer: 'Transformer 模型',
    settings_model_transformer_desc: '自注意力机制，精度更高',
    settings_model_api: '外部 API',
    settings_model_api_desc: '调用第三方语音识别服务',

    settings_api_config: 'API 配置',
    settings_api_url: 'API 地址',
    settings_api_key: 'API Key',
    settings_api_key_placeholder: '输入 API Key',
    settings_save: '保存',
    settings_api_url_placeholder: 'https://api.example.com/predict',
    settings_api_key_hint: 'API Key 加密存储于本地，仅本小程序可用',

    settings_server: '服务器设置',
    settings_server_connection: '连接方式：微信云托管（内网安全访问）',
    settings_server_note: '无需配置服务器地址，自动内网通信',

    settings_about: '关于',
    about_version: '版本：1.0.0',
    about_purpose: '用途：婴儿哭声情绪识别',
    about_categories: '类别：醒了 / 换尿布 / 要抱抱 / 饿了 / 安静 / 困了 / 不舒服',
    about_models: '模型：CNN-LSTM / Transformer',

    settings_language: '语言',
    settings_language_desc: '选择界面显示语言',
    language_zh: '简体中文',
    language_en: 'English',
    language_switched: '语言已切换',

    // 提示
    toast_switched: '已切换',
    toast_enter_api_key: '请输入 API Key',
    toast_api_key_saved: 'API Key 已保存',

    // 情绪标签
    emo_awake: '醒了',
    emo_diaper: '换尿布',
    emo_hug: '要抱抱',
    emo_hungry: '饿了',
    emo_silence: '安静',
    emo_sleepy: '困了',
    emo_uncomfortable: '不舒服',

    // 情绪建议
    sug_hug: '宝宝可能需要安抚，可以抱一抱、轻拍背部',
    sug_hungry: '宝宝可能饿了，建议喂奶或辅食',
    sug_sleepy: '宝宝困了，可以哄睡、播放摇篮曲',
    sug_awake: '宝宝醒了，可以陪宝宝玩耍',
    sug_diaper: '宝宝可能需要换尿布了',
    sug_uncomfortable: '宝宝可能不舒服，检查衣物是否合适',
    sug_silence: '宝宝很安静，一切正常'
  },

  en: {
    appTitle: 'Baby Emotion Recognition',

    tab_record: 'Recognize',
    tab_history: 'History',
    tab_settings: 'Settings',

    title: 'Baby Emotion Recognition',
    subtitle: "Record your baby's cry, AI helps you understand",
    tapToRecord: 'Tap to start recording (max 10s)',
    recording: 'Recording...',
    reRecord: 'Re-record',
    or: 'or',
    pickFromChat: 'Pick from chat',
    pickFromFile: 'Pick from file',
    analyzing: 'Analyzing...',
    confidence: 'Confidence',
    allProbabilities: 'All emotion probabilities',

    err_invalid_file: 'Invalid recording file',
    err_too_short: 'Recording too short, please record at least 1s',
    err_read_file: 'Failed to read recording',
    err_record_failed: 'Recording failed',
    err_mic_permission: 'Please authorize microphone permission',
    err_choose_file: 'Failed to select file',
    err_predict_failed: 'Recognition failed',

    model_cnn_lstm: 'CNN-LSTM Model',
    model_transformer: 'Transformer Model',
    model_api: 'External API',

    history_title: 'Recognition History',
    history_clear_all: 'Clear All',
    history_empty: 'No records yet',
    history_empty_tip: "Record your baby's voice on the home page",
    history_delete: 'Delete',
    time_just_now: 'just now',
    time_min_ago: ' min ago',
    time_hour_ago: ' hours ago',

    dlg_confirm_delete: 'Confirm Delete',
    dlg_delete_msg: 'Delete this record?',
    dlg_deleted: 'Deleted',
    dlg_confirm_clear: 'Confirm Clear',
    dlg_clear_msg: 'Clear all history records?',
    dlg_cleared: 'Cleared',

    settings_model: 'Model Selection',
    settings_model_desc: 'Choose a model for voice recognition',
    settings_model_cnn_lstm: 'CNN-LSTM Hybrid Model',
    settings_model_cnn_lstm_desc: 'Convolution + temporal network, suitable for real-time inference',
    settings_model_transformer: 'Transformer Model',
    settings_model_transformer_desc: 'Self-attention mechanism, higher accuracy',
    settings_model_api: 'External API',
    settings_model_api_desc: 'Third-party voice recognition service',

    settings_api_config: 'API Configuration',
    settings_api_url: 'API URL',
    settings_api_key: 'API Key',
    settings_api_key_placeholder: 'Enter API Key',
    settings_save: 'Save',
    settings_api_url_placeholder: 'https://api.example.com/predict',
    settings_api_key_hint: 'API Key is encrypted locally, only accessible by this mini program',

    settings_server: 'Server Settings',
    settings_server_connection: 'Connection: WeChat Cloud Container (intranet secure access)',
    settings_server_note: 'No server URL needed, automatic intranet communication',

    settings_about: 'About',
    about_version: 'Version: 1.0.0',
    about_purpose: 'Purpose: Baby cry emotion recognition',
    about_categories: 'Categories: Awake / Diaper / Hug / Hungry / Silence / Sleepy / Uncomfortable',
    about_models: 'Models: CNN-LSTM / Transformer',

    settings_language: 'Language',
    settings_language_desc: 'Choose interface display language',
    language_zh: '简体中文',
    language_en: 'English',
    language_switched: 'Language switched',

    toast_switched: 'Switched',
    toast_enter_api_key: 'Please enter API Key',
    toast_api_key_saved: 'API Key saved',

    emo_awake: 'Awake',
    emo_diaper: 'Diaper',
    emo_hug: 'Need hug',
    emo_hungry: 'Hungry',
    emo_silence: 'Silence',
    emo_sleepy: 'Sleepy',
    emo_uncomfortable: 'Uncomfortable',

    sug_hug: 'Baby may need soothing, try holding and gentle back patting',
    sug_hungry: 'Baby may be hungry, feed milk or solid food',
    sug_sleepy: 'Baby is sleepy, try lulling to sleep or play a lullaby',
    sug_awake: 'Baby is awake, play together',
    sug_diaper: 'Baby may need a diaper change',
    sug_uncomfortable: 'Baby may be uncomfortable, check clothing',
    sug_silence: 'Baby is quiet, all is well'
  }
};

// 情绪英文 key -> i18n key 映射
const EMO_KEY_MAP = {
  awake: 'emo_awake',
  diaper: 'emo_diaper',
  hug: 'emo_hug',
  hungry: 'emo_hungry',
  silence: 'emo_silence',
  sleepy: 'emo_sleepy',
  uncomfortable: 'emo_uncomfortable'
};

// 情绪 -> 建议的 i18n key 映射
const SUG_KEY_MAP = {
  awake: 'sug_awake',
  diaper: 'sug_diaper',
  hug: 'sug_hug',
  hungry: 'sug_hungry',
  silence: 'sug_silence',
  sleepy: 'sug_sleepy',
  uncomfortable: 'sug_uncomfortable'
};

// 模型 key -> i18n key 映射
const MODEL_KEY_MAP = {
  cnn_lstm: 'model_cnn_lstm',
  transformer: 'model_transformer',
  api: 'model_api'
};

// tabBar 顺序（与 app.json 一致）
const TAB_KEYS = ['tab_record', 'tab_history', 'tab_settings'];

let currentLocale = 'zh';

/**
 * 初始化（从本地存储恢复，需在 app.onLaunch 中调用）
 */
function init() {
  const saved = wx.getStorageSync(LOCALE_KEY);
  if (saved && SUPPORTED.indexOf(saved) !== -1) {
    currentLocale = saved;
  } else {
    // 简体中文为默认
    currentLocale = 'zh';
  }
}

/**
 * 获取当前语言
 */
function getLocale() {
  return currentLocale;
}

/**
 * 是否简体中文
 */
function isZh() {
  return currentLocale === 'zh';
}

/**
 * 切换语言
 * @param {string} locale 'zh' | 'en'
 * @param {boolean} applyTabBar 是否同步刷新 tabBar 文案
 */
function setLocale(locale, applyTabBar = true) {
  if (SUPPORTED.indexOf(locale) === -1) return false;
  if (locale === currentLocale) return false;

  currentLocale = locale;
  wx.setStorageSync(LOCALE_KEY, locale);

  if (applyTabBar) {
    applyTabBarText();
  }
  return true;
}

/**
 * 翻译
 * @param {string} key
 * @param {string} [locale] 指定语言，不传则用当前语言
 */
function t(key, locale) {
  const lang = locale || currentLocale;
  const dict = DICT[lang] || DICT.zh;
  return dict[key] !== undefined ? dict[key] : (DICT.zh[key] !== undefined ? DICT.zh[key] : key);
}

/**
 * 获取情绪标签文案
 */
function tEmotion(en) {
  const i18nKey = EMO_KEY_MAP[en];
  return i18nKey ? t(i18nKey) : en;
}

/**
 * 获取情绪建议文案
 */
function tSuggestion(en) {
  const i18nKey = SUG_KEY_MAP[en];
  return i18nKey ? t(i18nKey) : '';
}

/**
 * 获取模型显示名
 */
function tModel(modelKey) {
  const i18nKey = MODEL_KEY_MAP[modelKey];
  return i18nKey ? t(i18nKey) : modelKey;
}

/**
 * 把 t 函数注入页面 data，便于 WXML 使用 {{t.xxx}}
 * @param {Page} pageInstance
 */
function tPage(pageInstance) {
  // 注入当前语言的全部字典（前端按 key 读取）
  pageInstance.setData({ t: DICT[currentLocale], locale: currentLocale });
}

/**
 * 应用当前语言到 tabBar 文案
 */
function applyTabBarText() {
  if (!wx.setTabBarItem) return;
  TAB_KEYS.forEach((key, index) => {
    wx.setTabBarItem({
      index: index,
      text: t(key)
    });
  });
}

/**
 * 同步当前语言到导航栏标题（每个页面 onShow 可调用）
 */
function applyNavTitle() {
  wx.setNavigationBarTitle({ title: t('appTitle') });
}

module.exports = {
  init,
  getLocale,
  isZh,
  setLocale,
  t,
  tEmotion,
  tSuggestion,
  tModel,
  tPage,
  applyTabBarText,
  applyNavTitle,
  EMO_KEY_MAP,
  SUG_KEY_MAP,
  MODEL_KEY_MAP,
  DICT
};
