/**
 * API 通信模块
 * 通过微信云托管 callContainer 与后端 Flask 服务通信（内网安全访问）
 */

const app = getApp();

/**
 * 调用云托管容器
 * @param {string} path - 请求路径
 * @param {string} method - 请求方法
 * @param {object} data - 请求数据
 */
function callContainer(path, method, data) {
  return new Promise((resolve, reject) => {
    wx.cloud.callContainer({
      config: {
        env: app.globalData.cloudEnv
      },
      path: path,
      method: method,
      header: {
        'X-WX-SERVICE': app.globalData.cloudService,
        'content-type': 'application/json',
        'X-API-Key': app.globalData.apiKey
      },
      data: data || '',
      success(res) {
        if (res.statusCode === 200) {
          const data = res.data;
          if (data && data.error) {
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
        reject(new Error('云托管请求失败: ' + (err.errMsg || '未知错误')));
      }
    });
  });
}

/**
 * 上传音频文件到云存储，获取临时下载链接
 * @param {string} filePath - 本地音频文件路径
 * @returns {Promise<string>} 临时下载 URL
 */
function uploadToCloudStorage(filePath) {
  return new Promise((resolve, reject) => {
    const cloudPath = 'audio/' + Date.now() + '_' + Math.random().toString(36).substr(2, 8) + '.wav';
    wx.cloud.uploadFile({
      cloudPath: cloudPath,
      filePath: filePath,
      success(res) {
        // 获取临时下载链接
        wx.cloud.getTempFileURL({
          fileList: [res.fileID],
          success(urlRes) {
            if (urlRes.fileList && urlRes.fileList.length > 0) {
              resolve(urlRes.fileList[0].tempFileURL);
            } else {
              reject(new Error('获取文件下载链接失败'));
            }
          },
          fail(err) {
            reject(new Error('获取文件链接失败: ' + (err.errMsg || '未知错误')));
          }
        });
      },
      fail(err) {
        reject(new Error('上传云存储失败: ' + (err.errMsg || '未知错误')));
      }
    });
  });
}

/**
 * 上传音频文件并获取预测结果（文件路径方式）
 * 流程：上传到云存储 → 获取临时URL → 调用容器接口
 * @param {string} filePath - 音频文件路径
 * @param {string} model - 模型名称 (cnn_lstm / transformer / api)
 * @param {object} extra - 额外参数
 */
function predict(filePath, model, extra = {}) {
  return uploadToCloudStorage(filePath).then(function(fileUrl) {
    return callContainer('/api/predict/url', 'POST', {
      audio_url: fileUrl,
      model: model || 'cnn_lstm',
      source: extra.source || 'local',
      api_url: extra.api_url || ''
    });
  });
}

/**
 * 通过 base64 上传音频并获取预测结果（用于录音文件）
 * 如果 base64 数据超过 80KB，自动改用云存储中转
 * @param {string} audioBase64 - base64 编码的音频数据
 * @param {string} model - 模型名称
 */
function predictBase64(audioBase64, model) {
  // base64 数据超过 80KB 时，走云存储中转避免超过 callContainer 100K 限制
  if (audioBase64.length > 80 * 1024) {
    return base64ToCloudStorage(audioBase64).then(function(fileUrl) {
      return callContainer('/api/predict/url', 'POST', {
        audio_url: fileUrl,
        model: model || 'cnn_lstm'
      });
    });
  }

  // 小数据量直接通过 callContainer 发送
  return callContainer('/api/predict/base64', 'POST', {
    audio: audioBase64,
    model: model || 'cnn_lstm'
  });
}

/**
 * 将 base64 音频数据上传到云存储
 * @param {string} audioBase64 - base64 编码的音频数据
 * @returns {Promise<string>} 临时下载 URL
 */
function base64ToCloudStorage(audioBase64) {
  return new Promise(function(resolve, reject) {
    var fs = wx.getFileSystemManager();
    var tmpPath = wx.env.USER_DATA_PATH + '/audio_' + Date.now() + '.wav';

    try {
      // base64 转为临时文件
      fs.writeFileSync(tmpPath, audioBase64, 'base64');

      // 上传到云存储
      var cloudPath = 'audio/' + Date.now() + '_' + Math.random().toString(36).substr(2, 8) + '.wav';
      wx.cloud.uploadFile({
        cloudPath: cloudPath,
        filePath: tmpPath,
        success: function(res) {
          // 清理临时文件
          try { fs.unlinkSync(tmpPath); } catch (e) {}

          // 获取临时下载链接
          wx.cloud.getTempFileURL({
            fileList: [res.fileID],
            success: function(urlRes) {
              if (urlRes.fileList && urlRes.fileList.length > 0) {
                resolve(urlRes.fileList[0].tempFileURL);
              } else {
                reject(new Error('获取文件下载链接失败'));
              }
            },
            fail: function(err) {
              reject(new Error('获取文件链接失败: ' + (err.errMsg || '未知错误')));
            }
          });
        },
        fail: function(err) {
          try { fs.unlinkSync(tmpPath); } catch (e) {}
          reject(new Error('上传云存储失败: ' + (err.errMsg || '未知错误')));
        }
      });
    } catch (e) {
      reject(new Error('写入临时文件失败: ' + e.message));
    }
  });
}

/**
 * 获取模型信息
 */
function getModelInfo() {
  return callContainer('/api/info', 'GET', '').catch(function() {
    // 容器调用失败时返回默认信息
    return {
      models: ['cnn_lstm', 'transformer'],
      labels: {
        classes: ['awake', 'diaper', 'hug', 'hungry', 'silence', 'sleepy', 'uncomfortable'],
        cn_mapping: app.globalData.labels,
        num_classes: 7
      }
    };
  });
}

module.exports = {
  predict,
  predictBase64,
  getModelInfo,
  callContainer
};
