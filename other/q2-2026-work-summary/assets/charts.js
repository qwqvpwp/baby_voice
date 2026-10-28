// assets/charts.js
// All chart logic for the Q2 2026 work summary report.
// Wrapped in IIFE to avoid polluting the global scope.
(function () {
  var style = getComputedStyle(document.documentElement);
  var accent = style.getPropertyValue('--accent').trim();   // #3b5bff
  var accent2 = style.getPropertyValue('--accent2').trim(); // #16b3a8
  var ink = style.getPropertyValue('--ink').trim();         // #0f1b2d
  var muted = style.getPropertyValue('--muted').trim();     // #5a6b85
  var rule = style.getPropertyValue('--rule').trim();       // rgba(...)
  var bg2 = style.getPropertyValue('--bg2').trim();         // rgba(255,255,255,0.72)

  // --- Chart: monthly message distribution ---
  var monthlyEl = document.getElementById('chart-monthly');
  if (monthlyEl) {
    var chartMonthly = echarts.init(monthlyEl, null, { renderer: 'svg' });
    var months = ['2026-04', '2026-05', '2026-06', '2026-07'];
    var monthlyCounts = [1, 1, 1, 1];

    chartMonthly.setOption({
      animation: false,
      tooltip: {
        trigger: 'axis',
        appendToBody: true,
        backgroundColor: '#ffffff',
        borderColor: rule,
        borderWidth: 1,
        textStyle: { color: ink, fontSize: 13 },
        formatter: function (params) {
          var p = params[0];
          return p.axisValue + '<br/>消息数: <b>' + p.value + '</b> 条';
        }
      },
      grid: { top: 30, right: 24, bottom: 40, left: 48 },
      xAxis: {
        type: 'category',
        data: months,
        axisLine: { lineStyle: { color: rule } },
        axisTick: { show: false },
        axisLabel: {
          color: muted,
          fontSize: 12,
          fontFamily: 'DMMono, monospace'
        }
      },
      yAxis: {
        type: 'value',
        min: 0,
        max: 3,
        interval: 1,
        axisLine: { show: false },
        axisTick: { show: false },
        splitLine: { lineStyle: { color: rule, type: 'dashed' } },
        axisLabel: {
          color: muted,
          fontSize: 12,
          fontFamily: 'DMMono, monospace'
        }
      },
      series: [
        {
          name: '消息数',
          type: 'bar',
          data: monthlyCounts,
          barWidth: 42,
          itemStyle: {
            borderRadius: [8, 8, 0, 0],
            color: {
              type: 'linear',
              x: 0, y: 0, x2: 0, y2: 1,
              colorStops: [
                { offset: 0, color: accent },
                { offset: 1, color: accent2 }
              ]
            }
          },
          label: {
            show: true,
            position: 'top',
            color: ink,
            fontWeight: 700,
            fontSize: 13,
            formatter: '{c}'
          }
        }
      ]
    });
    window.addEventListener('resize', function () { chartMonthly.resize(); });
  }
})();
