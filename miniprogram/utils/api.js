/**
 * API 通信模块
 * 负责与后端 Flask 服务通信
 */

const app = getApp();

/**
 * 获取服务器地址
 */
function getServerUrl() {
  return app.globalData.serverUrl || 'http://localhost:5000';
}

/**
 * 上传音频并获取预测结果
 * @param {string} filePath - 音频文件路径
 * @param {string} model - 模型名称 (cnn_lstm / transformer / api)
 * @param {object} extra - 额外参数 (如 api_url)
 */
function predict(filePath, model, extra = {}) {
  return new Promise((resolve, reject) => {
    wx.uploadFile({
      url: getServerUrl() + '/api/predict',
      filePath: filePath,
      name: 'audio',
      formData: {
        model: model || 'cnn_lstm',
        source: extra.source || 'local',
        api_url: extra.api_url || ''
      },
      success(res) {
        try {
          const data = JSON.parse(res.data);
          if (data.error) {
            reject(new Error(data.error));
          } else {
            resolve(data);
          }
        } catch (e) {
          reject(new Error('解析响应失败: ' + (res.data || '').substring(0, 100)));
        }
      },
      fail(err) {
        reject(new Error('上传失败: ' + (err.errMsg || '未知错误')));
      }
    });
  });
}

/**
 * 通过 base64 上传音频并获取预测结果（用于录音文件，避免 wx.uploadFile 兼容问题）
 * @param {string} audioBase64 - base64 编码的音频数据
 * @param {string} model - 模型名称
 */
function predictBase64(audioBase64, model) {
  return new Promise((resolve, reject) => {
    wx.request({
      url: getServerUrl() + '/api/predict/base64',
      method: 'POST',
      data: {
        audio: audioBase64,
        model: model || 'cnn_lstm'
      },
      success(res) {
        if (res.statusCode === 200) {
          const data = res.data;
          if (data.error) {
            reject(new Error(data.error));
          } else {
            resolve(data);
          }
        } else {
          var errMsg = '服务器错误 ' + res.statusCode;
          if (res.data && res.data.error) errMsg += ': ' + res.data.error;
          reject(new Error(errMsg));
        }
      },
      fail(err) {
        reject(new Error('网络请求失败: ' + (err.errMsg || '未知错误')));
      }
    });
  });
}

/**
 * 获取模型信息
 */
function getModelInfo() {
  return new Promise((resolve, reject) => {
    wx.request({
      url: getServerUrl() + '/api/info',
      method: 'GET',
      success(res) {
        if (res.statusCode === 200) {
          resolve(res.data);
        } else {
          reject(new Error('获取信息失败'));
        }
      },
      fail() {
        // 返回默认信息
        resolve({
          models: ['cnn_lstm', 'transformer'],
          labels: {
            classes: ['awake', 'diaper', 'hug', 'hungry', 'silence', 'sleepy', 'uncomfortable'],
            cn_mapping: app.globalData.labels,
            num_classes: 7
          }
        });
      }
    });
  });
}

module.exports = {
  predict,
  predictBase64,
  getModelInfo,
  getServerUrl
};