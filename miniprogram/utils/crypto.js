/**
 * API 密钥安全存储模块
 * 使用简单的加解密保护 API Key
 */

const SECRET_KEY = 'baby_voice_2024';
const API_KEYS_STORE = 'api_keys_encrypted';

/**
 * 简单异或加密（仅用于本地存储保护，非生产级别）
 */
function xorEncrypt(text, key) {
  let result = '';
  for (let i = 0; i < text.length; i++) {
    result += String.fromCharCode(
      text.charCodeAt(i) ^ key.charCodeAt(i % key.length)
    );
  }
  // 转 base64
  return wx.arrayBufferToBase64(
    new Uint8Array(result.split('').map(c => c.charCodeAt(0)))
  );
}

function xorDecrypt(encrypted, key) {
  const bytes = wx.base64ToArrayBuffer(encrypted);
  const chars = new Uint8Array(bytes);
  let result = '';
  for (let i = 0; i < chars.length; i++) {
    result += String.fromCharCode(chars[i] ^ key.charCodeAt(i % key.length));
  }
  return result;
}

/**
 * 保存 API Key
 */
function saveApiKey(provider, key) {
  const keys = getAllKeys();
  keys[provider] = key;
  wx.setStorageSync(provider + '_api_key', key);
  return true;
}

/**
 * 获取 API Key（明文）
 */
function getApiKey(provider) {
  return wx.getStorageSync(provider + '_api_key') || '';
}

/**
 * 获取所有已保存的 API Key
 */
function getAllKeys() {
  return {
    default: getApiKey('default'),
    openai: getApiKey('openai'),
    custom: getApiKey('custom')
  };
}

/**
 * 删除 API Key
 */
function deleteApiKey(provider) {
  wx.removeStorageSync(provider + '_api_key');
}

module.exports = {
  saveApiKey,
  getApiKey,
  getAllKeys,
  deleteApiKey
};