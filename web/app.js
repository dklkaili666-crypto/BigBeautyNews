/**
 * BigBeautyNews 前端逻辑
 *
 * 数据来源：
 * - web/data.json（当天数据，由 GitHub Actions 每次运行后更新）
 * - data/archive/YYYY-MM-DD.json（历史数据，用于翻看）
 *
 * 注：如果直接打开 index.html（file:// 协议），fetch JSON 可能被浏览器拦截。
 * 本地开发时建议用 `python -m http.server 8080` 或 `npx serve web/`。
 */
(function () {
  'use strict';

  const datePicker = document.getElementById('datePicker');
  const btnToday = document.getElementById('btnToday');
  const btnPrev = document.getElementById('btnPrev');
  const btnNext = document.getElementById('btnNext');
  const content = document.getElementById('content');

  let currentDate = new Date();

  // 格式化日期
  function fmtDate(d) {
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    return `${y}-${m}-${day}`;
  }

  // 加载某一天的数据
  async function loadDate(dateStr) {
    content.innerHTML = '<div class="loading">加载中...</div>';
    datePicker.value = dateStr;

    try {
      const today = fmtDate(new Date());
      const path = dateStr === today
        ? 'data.json'
        : `../data/archive/${dateStr}.json`;
      const resp = await fetch(path);
      if (!resp.ok) throw new Error('Not found');
      const data = await resp.json();
      render(dateStr, data);
    } catch {
      content.innerHTML = `<div class="empty">
        <div class="icon">📭</div>
        <p>${dateStr} 暂无数据</p>
      </div>`;
    }
  }

  // 渲染
  function render(dateStr, data) {
    const items = data.items || [];
    const theme = data.dailyTheme || '';
    const geopoliticsItems = data.geopoliticsItems || [];
    const geopoliticsTheme = data.geopoliticsTheme || '';

    let html = '';
    if (items.length === 0 && geopoliticsItems.length === 0) {
      content.innerHTML = '<div class="empty"><div class="icon">📭</div><p>暂无数据</p></div>';
      return;
    }
    if (geopoliticsItems.length > 0) {
      html += renderSection('一、AI 重要消息', theme, items, 'ai');
      html += renderSection(
        '二、全球地缘与政经',
        geopoliticsTheme,
        geopoliticsItems,
        'geopolitics'
      );
    } else {
      html += renderSection('', theme, items, 'ai');
    }
    content.innerHTML = html;
  }

  function renderSection(title, theme, items, sectionClass) {
    let html = `<section class="news-section ${sectionClass}">`;
    if (title) {
      html += `<h2 class="section-title">${escapeHtml(title)}</h2>`;
    }
    if (theme) {
      html += `<div class="daily-theme">📊 ${escapeHtml(theme)}</div>`;
    }
    items.forEach((item, i) => {
      const rank = item.rank || (i + 1);
      const tags = (item.tags || []).map(t => `<span class="tag">${escapeHtml(t)}</span>`).join('');

      const url = safeHttpUrl(item.url);
      html += `
        <div class="article-card rank-${rank}">
          <div class="article-header">
            <span class="rank-badge">${rank}</span>
            <span class="article-title">${escapeHtml(item.title)}</span>
          </div>
          <div class="article-meta">
            <span class="source-tag">${escapeHtml(item.source)}</span>
            ${tags}
          </div>
          <div class="article-summary">${escapeHtml(item.summary)}</div>
          ${url ? `<a class="article-link" href="${escapeHtml(url)}" target="_blank" rel="noopener noreferrer">🔗 阅读原文 →</a>` : ''}
        </div>
      `;
    });
    return `${html}</section>`;
  }

  function escapeHtml(str) {
    if (!str) return '';
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }

  function safeHttpUrl(value) {
    try {
      const url = new URL(value);
      return ['http:', 'https:'].includes(url.protocol) ? url.href : '';
    } catch {
      return '';
    }
  }

  // 更新日期并加载
  function goDate(d) {
    currentDate = d;
    loadDate(fmtDate(d));
  }

  // 事件
  btnToday.addEventListener('click', () => goDate(new Date()));
  btnPrev.addEventListener('click', () => {
    currentDate.setDate(currentDate.getDate() - 1);
    goDate(new Date(currentDate));
  });
  btnNext.addEventListener('click', () => {
    currentDate.setDate(currentDate.getDate() + 1);
    goDate(new Date(currentDate));
  });
  datePicker.addEventListener('change', () => {
    if (datePicker.value) {
      goDate(new Date(datePicker.value + 'T00:00:00'));
    }
  });

  // 初始加载
  datePicker.value = fmtDate(currentDate);
  loadDate(fmtDate(currentDate));
})();
