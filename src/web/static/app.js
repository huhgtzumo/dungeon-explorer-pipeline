/* ── 探索者計劃 — 廢墟探索影片生成器 ── */

const STAGE_LABELS = {
  crawl: '探索素材搜尋',
  analyze: '素材分析',
  generate: '探索腳本生成',
  storyboard: '場景分鏡',
  'generate-images': '場景圖生成（Flux）',
  'generate-videos': '探索影片生成（Kling AI）',
  'kb-analyze-single': '知識庫分析（單部）',
  'kb-analyze-batch': '知識庫分析（批量）',
  'kb-generate': '知識庫生成',
  'analyze-preview': '預覽分析（審核）',
};

let pollingTimer = null;
let _pollInterval = 5000;
let _pollFailCount = 0;
let currentStep = 1;
let currentView = 'pipeline'; // 'pipeline' or 'knowledge'
let currentKBCategory = 'building_types';
let _currentCrawlId = null;
let _logExpanded = false;

// Cached data
let _crawls = [];
let _analyses = [];
let _scripts = [];
let _storyboards = [];
let _imageSets = [];
let _allVideos = []; // Step 2 all-videos cache

// Step 3: KB card selections — category -> single selected entry id (or null)
const _kbCardSelections = {};

// Step 3: generation mode — 'single' (default) or 'series'
let _genMode = 'single';
let _durationSec = 60;

const DURATION_HINTS = {
  60:  '建議選 3-4 個核心元素（建築 + 區域 + 遭遇/結局）',
  180: '建議選 4-6 個元素（核心 3-4 + 輔助 1-2）',
  300: '建議選 5-8 個元素（核心 3-4 + 輔助 2-4）',
};

function setDuration(sec) {
  _durationSec = sec;
  document.querySelectorAll('.dur-btn').forEach(b => b.classList.toggle('active', parseInt(b.dataset.dur) === sec));
  const hint = document.getElementById('dur-hint');
  if (hint) hint.textContent = DURATION_HINTS[sec] || '';
}

function setGenMode(mode) {
  _genMode = mode;
  document.getElementById('mode-single').classList.toggle('active', mode === 'single');
  document.getElementById('mode-series').classList.toggle('active', mode === 'series');
  document.getElementById('series-options').style.display = mode === 'series' ? '' : 'none';
}

// ══════════════════════════════════════════
// Busy / Loading State
// ══════════════════════════════════════════

function _setBusy(btn, busy) {
  if (!btn) return;
  btn.disabled = busy;
  if (busy) {
    btn.dataset.origHtml = btn.innerHTML;
    btn.textContent = '處理中...';
    btn.classList.add('btn-loading');
  } else {
    btn.innerHTML = btn.dataset.origHtml || btn.textContent;
    btn.classList.remove('btn-loading');
  }
}

// ══════════════════════════════════════════
// Navigation
// ══════════════════════════════════════════

function navTo(view) {
  currentView = view;
  document.getElementById('view-pipeline').style.display = view === 'pipeline' ? '' : 'none';
  document.getElementById('view-knowledge').style.display = view === 'knowledge' ? '' : 'none';
  const analysesView = document.getElementById('view-analyses');
  if (analysesView) analysesView.style.display = view === 'analyses' ? '' : 'none';
  const scriptsView = document.getElementById('view-scripts');
  if (scriptsView) scriptsView.style.display = view === 'scripts' ? '' : 'none';

  // Update sidebar active states
  document.querySelectorAll('.sidebar-item').forEach(item => {
    item.classList.remove('active');
    if (item.dataset.nav === view) item.classList.add('active');
  });

  if (view === 'knowledge') {
    refreshKB();
  }
  if (view === 'analyses') {
    loadAnalysesView();
  }
  if (view === 'scripts') {
    loadScriptsView();
  }
}

function goStep(step) {
  currentStep = step;

  // Switch to pipeline view if not already there
  if (currentView !== 'pipeline') {
    navTo('pipeline');
  }

  // Update step panels
  document.querySelectorAll('.step-panel').forEach(p => p.classList.remove('active'));
  const panel = document.getElementById('step' + step);
  if (panel) panel.classList.add('active');

  // Update stepper bar
  const steps = document.querySelectorAll('.stepper-bar .step');
  const connectors = document.querySelectorAll('.step-connector');

  steps.forEach((el, idx) => {
    const n = idx + 1;
    el.classList.remove('completed', 'active', 'pending');
    if (n < step) {
      el.classList.add('completed');
      el.querySelector('.step-indicator').innerHTML = '&#10003;';
    } else if (n === step) {
      el.classList.add('active');
      el.querySelector('.step-indicator').textContent = n;
    } else {
      el.classList.add('pending');
      el.querySelector('.step-indicator').textContent = n;
    }
  });

  connectors.forEach((c, idx) => {
    if (idx < step - 1) {
      c.classList.add('done');
    } else {
      c.classList.remove('done');
    }
  });

  // Load step-specific data
  if (step === 2) {
    loadStep2Videos();
  }
  if (step === 3) {
    loadStep3KBCards();
  }
}

// ══════════════════════════════════════════
// Init
// ══════════════════════════════════════════

document.addEventListener('DOMContentLoaded', () => {
  goStep(1);
  refreshAll();
  pollingTimer = setInterval(refreshAll, _pollInterval);
});

function _resetPolling(interval) {
  if (pollingTimer) clearInterval(pollingTimer);
  _pollInterval = interval;
  pollingTimer = setInterval(refreshAll, _pollInterval);
}

// ══════════════════════════════════════════
// Refresh All
// ══════════════════════════════════════════

async function refreshAll() {
  try {
    const [crawlsResp, analysesResp, scriptsResp, sbResp, imgResp, vidResp, tasksResp] = await Promise.all([
      fetch('/api/crawls'),
      fetch('/api/analyses'),
      fetch('/api/scripts'),
      fetch('/api/storyboards'),
      fetch('/api/image-sets'),
      fetch('/api/video-sets'),
      fetch('/api/tasks'),
    ]);
    _crawls = (await crawlsResp.json()).data || [];
    _analyses = (await analysesResp.json()).data || [];
    _scripts = (await scriptsResp.json()).data || [];
    _storyboards = (await sbResp.json()).data || [];
    _imageSets = (await imgResp.json()).data || [];
    _videoSets = (await vidResp.json()).data || [];
    const tasks = await tasksResp.json();

    // Update sidebar badges
    document.getElementById('badge-crawls').textContent = _crawls.length;
    document.getElementById('badge-analyses').textContent = _analyses.length;
    document.getElementById('badge-scripts').textContent = _scripts.length;
    document.getElementById('badge-storyboards').textContent = _storyboards.length;
    document.getElementById('badge-images').textContent = _imageSets.length;
    document.getElementById('badge-videos').textContent = _videoSets.length;

    // Step 1
    renderCrawlHistory(_crawls);

    // Step 2
    renderAnalysisHistory(_analyses);

    // Step 3
    renderScriptHistory(_scripts);

    // Step 4
    populateScriptSelect(_scripts);
    renderStoryboardHistory(_storyboards);

    // Step 5
    populateStoryboardSelect(_storyboards);
    renderImageHistory(_imageSets);

    // Step 6
    populateImageSelect(_imageSets);
    renderVideoHistory(_videoSets);

    // Tasks
    renderTasks(tasks);
    // Adaptive polling: fast when tasks running, slow when idle
    const hasRunning = tasks.some(t => t.status === 'running');
    const idealInterval = hasRunning ? 3000 : 10000;
    if (_pollFailCount > 0) {
      _pollFailCount = 0;
    }
    if (idealInterval !== _pollInterval) {
      _resetPolling(idealInterval);
    }
  } catch (e) {
    console.error('Refresh failed:', e);
    _pollFailCount++;
    // Exponential backoff: 10s, 20s, 30s max
    const newInterval = Math.min(5000 + _pollFailCount * 5000, 30000);
    if (newInterval !== _pollInterval) {
      _resetPolling(newInterval);
    }
  }
}

// ══════════════════════════════════════════
// Step 1: Crawl
// ══════════════════════════════════════════

async function doCrawl() {
  const btn = document.getElementById('btn-crawl');
  if (btn && btn.disabled) return;
  _setBusy(btn, true);

  const keyword = document.getElementById('crawl-keyword').value.trim();
  const tagsStr = document.getElementById('crawl-tags').value.trim();
  const tags = tagsStr ? tagsStr.split(',').map(t => t.trim()).filter(Boolean) : [];

  try {
    const resp = await fetch('/api/trigger/crawl', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ keyword, tags }),
    });
    const data = await resp.json();
    if (data.error) alert('Error: ' + data.error);
    refreshAll();
  } catch (e) {
    alert('Failed: ' + e.message);
  } finally {
    _setBusy(btn, false);
  }
}

function renderCrawlHistory(crawls) {
  const el = document.getElementById('crawl-history');
  if (!crawls.length) {
    el.innerHTML = '<div class="preview-empty" style="padding:12px 0;font-size:12px">尚無搜尋紀錄</div>';
    return;
  }
  el.innerHTML = crawls.slice().reverse().map(c => `
    <div class="history-item" onclick="showCrawlDetail('${esc(c.id)}')">
      <div class="hi-top">
        <div class="hi-main">
          <div class="hi-title">${esc(c.keyword || '預設搜尋')}</div>
          <div class="hi-meta">${c.count} 部 · ${esc(c.created_at)}</div>
        </div>
        <div class="hi-actions">
          <button class="trace-btn" onclick="event.stopPropagation();showTrace('crawls','${esc(c.id)}')">追溯</button>
        </div>
      </div>
      ${(c.tags || []).length ? '<div class="hi-tags">' + c.tags.map(t => '<span class="tag tag-sm">' + esc(t) + '</span>').join('') + '</div>' : ''}
    </div>
  `).join('');
}

async function showCrawlDetail(crawlId) {
  _currentCrawlId = crawlId;
  const el = document.getElementById('crawl-results');
  el.innerHTML = '<div class="preview-empty">載入中...</div>';

  try {
    const [videosResp, reviewsResp, subResp] = await Promise.all([
      fetch('/api/crawls/' + crawlId + '/videos'),
      fetch('/api/video-reviews'),
      fetch('/api/crawls/' + crawlId + '/subtitle-status'),
    ]);
    const data = (await videosResp.json()).data || [];
    const reviews = await reviewsResp.json();
    const subStatus = (await subResp.json()).data || {};

    if (!data.length) {
      el.innerHTML = '<div class="empty-state"><div class="empty-icon">&#128269;</div><p>無視頻資料</p></div>';
      document.getElementById('crawl-results-meta').textContent = '';
      return;
    }

    document.getElementById('crawl-results-meta').textContent = `共 ${data.length} 筆結果`;
    el.innerHTML = _renderCrawlVideoTable(data, reviews, crawlId, subStatus);
    _updateSelectionBar();
  } catch (e) {
    el.innerHTML = '<div class="empty-state"><div class="empty-icon">&#128683;</div><p>載入失敗</p></div>';
  }
}

function _renderCrawlVideoTable(videos, reviews, crawlId, subStatus) {
  subStatus = subStatus || {};
  // Check if any video needs subtitle extraction
  const needsSub = videos.some(r => {
    const ss = subStatus[r.video_id];
    return !ss || ss.status === 'none';
  });
  const allDone = videos.every(r => {
    const ss = subStatus[r.video_id];
    return ss && ss.status === 'done';
  });
  const extractingCount = videos.filter(r => { const ss = subStatus[r.video_id]; return ss && ss.status === 'extracting'; }).length;
  const extractBar = allDone ? `
    <div style="margin-bottom:10px;color:var(--text-success,#4ade80);font-size:12px;">✅ 所有視頻字幕已提取完畢</div>` :
    extractingCount > 0 ? `
    <div style="margin-bottom:10px;color:var(--text-accent,#a78bfa);font-size:12px;">⏳ 字幕提取中... (${extractingCount} 部)</div>` : '';

  return extractBar + `
    <table class="results-table">
      <thead>
        <tr>
          <th style="width:36px"><input type="checkbox" onchange="toggleAllVideoCb(this.checked)" /></th>
          <th>影片</th>
          <th>頻道</th>
          <th>觀看次數</th>
          <th>時長</th>
          <th>字幕</th>
          <th>狀態</th>
          <th>操作</th>
        </tr>
      </thead>
      <tbody>${videos.map((r, i) => {
        const vid = r.video_id || '';
        const status = _getVideoStatus(vid, reviews);
        const checked = status === 'confirmed' ? 'disabled' : '';
        const thumbClass = 'thumbnail t' + ((i % 5) + 1);
        const ss = subStatus[vid] || { status: 'none' };
        const subCell = _subtitleStatusCell(ss, crawlId, vid);
        return `
          <tr>
            <td><input type="checkbox" class="video-cb" value="${esc(vid)}" ${checked} onchange="_updateSelectionBar()" /></td>
            <td>
              <div class="result-row">
                <div class="${thumbClass}"></div>
                <div>
                  <div class="video-title">${esc(r.title)}</div>
                  <div class="video-channel">${esc(r.channel || '')}</div>
                </div>
              </div>
            </td>
            <td style="color:var(--text-secondary)">${esc(r.channel || '')}</td>
            <td class="views-count">${(r.views || 0).toLocaleString()}</td>
            <td><span class="duration-badge">${formatDuration(r.duration)}</span></td>
            <td>${subCell}</td>
            <td>${_statusBadge(status)}</td>
            <td class="video-actions">
              ${r.url ? '<a href="' + esc(r.url) + '" target="_blank" rel="noopener" class="video-link" style="margin-right:6px">YouTube &#8599;</a>' : ''}
              <button class="btn btn-sm btn-danger" onclick="event.stopPropagation();doDeleteVideo('${esc(crawlId)}','${esc(vid)}','${esc(r.title)}')">刪除</button>
            </td>
          </tr>`;
      }).join('')}
      </tbody>
    </table>`;
}

function _subtitleStatusCell(ss, crawlId, videoId) {
  if (ss.status === 'done') {
    const langLabel = ss.language ? ` [${ss.language}]` : '';
    return `<span class="sub-status sub-done sub-expandable" onclick="event.stopPropagation();toggleSubtitleText('${esc(crawlId)}','${esc(videoId)}',this)" title="點擊展開字幕">✅ ${ss.char_count.toLocaleString()} 字${langLabel} ▾</span>`;
  }
  if (ss.status === 'extracting') {
    return `<span class="sub-status sub-extracting">⏳ 轉錄中...</span>`;
  }
  if (ss.status === 'pending') {
    return `<span class="sub-status sub-pending">⏸ 待處理</span> <button class="btn-whisper" onclick="event.stopPropagation();doWhisperExtract('${esc(crawlId)}','${esc(videoId)}',this)" title="${esc(ss.note || '無內建字幕')}">🎤 Whisper</button>`;
  }
  if (ss.status === 'failed') {
    return `<span class="sub-status sub-failed" title="${esc(ss.error || '提取失敗')}">❌ 失敗</span> <button class="btn-whisper" onclick="event.stopPropagation();doWhisperExtract('${esc(crawlId)}','${esc(videoId)}',this)">🎤 重試</button>`;
  }
  return `<span class="sub-status sub-none">—</span>`;
}

async function toggleSubtitleText(crawlId, videoId, el) {
  const row = el.closest('tr');
  const existingRow = row.nextElementSibling;
  if (existingRow && existingRow.classList.contains('subtitle-text-row')) {
    existingRow.remove();
    el.innerHTML = el.innerHTML.replace('▴', '▾');
    return;
  }
  el.innerHTML = el.innerHTML.replace('▾', '▴');
  const tr = document.createElement('tr');
  tr.className = 'subtitle-text-row';
  tr.innerHTML = '<td colspan="8"><div class="subtitle-text-box" style="max-height:200px;overflow-y:auto;padding:8px 12px;background:var(--bg-tertiary,#1a1a2e);border-radius:6px;margin:4px 0;font-size:12px;line-height:1.6;color:var(--text-secondary,#aaa);white-space:pre-wrap;">載入中...</div></td>';
  row.after(tr);
  try {
    const resp = await fetch('/api/crawls/' + crawlId + '/subtitle-text/' + videoId);
    const data = await resp.json();
    tr.querySelector('.subtitle-text-box').textContent = data.text || '（無字幕內容）';
  } catch (e) {
    tr.querySelector('.subtitle-text-box').textContent = '載入失敗: ' + e.message;
  }
}

async function doWhisperExtract(crawlId, videoId, btn) {
  btn.disabled = true;
  btn.textContent = '⏳ 轉錄中...';
  try {
    const resp = await fetch('/api/trigger/whisper-extract', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ crawl_id: crawlId, video_id: videoId }),
    });
    const data = await resp.json();
    if (data.task_id) {
      // Poll subtitle status every 5 seconds until done
      const poll = setInterval(async () => {
        try {
          const sr = await fetch('/api/crawls/' + crawlId + '/subtitle-status');
          const sd = await sr.json();
          const vs = (sd.data || {})[videoId];
          if (vs && (vs.status === 'done' || vs.status === 'failed')) {
            clearInterval(poll);
            // Re-render the crawl detail to update subtitle status
            const detailEl = btn.closest('.crawl-detail-content');
            if (detailEl) {
              const crawlIdAttr = detailEl.dataset.crawlId || crawlId;
              showCrawlDetail(crawlIdAttr);
            }
          }
        } catch (e) { /* ignore poll errors */ }
      }, 5000);
    }
  } catch (e) {
    btn.textContent = '❌ 失敗';
    btn.disabled = false;
  }
}

async function doExtractSubtitles(crawlId) {
  const btn = event.target;
  _setBusy(btn, true);
  try {
    const resp = await fetch('/api/trigger/extract-subtitles', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ crawl_id: crawlId }),
    });
    const data = await resp.json();
    if (data.error) {
      alert('Error: ' + data.error);
      return;
    }
    // Poll for subtitle status updates
    _pollSubtitleExtract(data.task_id, crawlId);
  } catch (e) {
    alert('Failed: ' + e.message);
  } finally {
    _setBusy(btn, false);
  }
}

function _pollSubtitleExtract(taskId, crawlId) {
  const poll = async () => {
    try {
      const resp = await fetch('/api/task/' + taskId);
      const task = await resp.json();
      // Refresh the crawl detail to show updated subtitle status
      showCrawlDetail(crawlId);
      if (task.status === 'done' || task.status === 'error') {
        return;
      }
      setTimeout(poll, 5000);
    } catch (e) {
      setTimeout(poll, 5000);
    }
  };
  setTimeout(poll, 3000);
}

function _updateSelectionBar() {
  const count = _getSelectedVideoIds().length;
  const bar = document.getElementById('crawl-selection-bar');
  const countEl = document.getElementById('crawl-selected-count');
  if (bar && countEl) {
    if (count > 0) {
      bar.style.display = 'flex';
      countEl.textContent = count;
    } else {
      bar.style.display = 'none';
    }
  }
}

function _getVideoStatus(videoId, reviews) {
  const r = reviews[videoId];
  if (!r) return 'none';
  return r.status || 'none';
}

function _statusBadge(status) {
  const map = {
    none:           '<span class="video-status vs-none">待審核</span>',
    pending_review: '<span class="video-status vs-pending-review">待確認</span>',
    analyzing:      '<span class="video-status vs-analyzing">分析中</span>',
    confirmed:      '<span class="video-status vs-confirmed">已入庫</span>',
    rejected:       '<span class="video-status vs-rejected">已拒絕</span>',
  };
  return map[status] || map.none;
}

function toggleAllVideoCb(checked) {
  document.querySelectorAll('.video-cb:not(:disabled)').forEach(cb => cb.checked = checked);
  _updateSelectionBar();
}

function _getSelectedVideoIds() {
  return [...document.querySelectorAll('.video-cb:checked')].map(cb => cb.value);
}

async function doBatchAnalyzeSelected() {
  const btn = document.getElementById('btn-batch-analyze');
  const videoIds = _getSelectedVideoIds();
  if (!videoIds.length) {
    alert('請先勾選要分析的視頻');
    return;
  }
  if (!_currentCrawlId) {
    alert('請先選擇一個搜尋結果');
    return;
  }
  if (!confirm(`確認批量分析 ${videoIds.length} 部視頻並入庫？`)) return;

  _setBusy(btn, true);
  try {
    const resp = await fetch('/api/trigger/analyze-batch', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ source_crawl_ids: [_currentCrawlId], video_ids: videoIds }),
    });
    const data = await resp.json();
    if (!resp.ok || data.error) {
      alert(data.error || '觸發失敗');
      return;
    }
    alert('批量分析已啟動，系統會逐個分析並自動入庫。可在任務紀錄查看進度。');
    refreshAll();
  } catch (e) {
    alert('Failed: ' + e.message);
  } finally {
    _setBusy(btn, false);
  }
}

async function doDeleteVideo(crawlId, videoId, title) {
  if (!confirm(`確認刪除「${title}」？此操作不可恢復。`)) return;
  try {
    const resp = await fetch(`/api/crawls/${crawlId}/videos/${videoId}`, { method: 'DELETE' });
    const data = await resp.json();
    if (data.error) {
      alert('Error: ' + data.error);
      return;
    }
    showCrawlDetail(crawlId);
  } catch (e) {
    alert('Failed: ' + e.message);
  }
}

async function doAnalyzePreview(videoId, crawlId) {
  try {
    const resp = await fetch('/api/trigger/analyze-preview', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ source_crawl_ids: [crawlId], video_id: videoId }),
    });
    const data = await resp.json();
    if (data.error) {
      alert('Error: ' + data.error);
      return;
    }
    _pollAnalyzePreview(data.task_id, videoId, crawlId);
  } catch (e) {
    alert('Failed: ' + e.message);
  }
}

async function _pollAnalyzePreview(taskId, videoId, crawlId) {
  const poll = async () => {
    try {
      const resp = await fetch('/api/task/' + taskId);
      const task = await resp.json();
      if (task.status === 'done') {
        showCrawlDetail(crawlId);
        return;
      }
      if (task.status === 'error') {
        alert('分析失敗: ' + (task.error || '未知錯誤'));
        showCrawlDetail(crawlId);
        return;
      }
      setTimeout(poll, 2000);
    } catch (e) {
      setTimeout(poll, 3000);
    }
  };
  showCrawlDetail(crawlId);
  setTimeout(poll, 2000);
}

async function showAnalysisPreview(videoId) {
  openDetail('分析預覽: ' + videoId);
  const el = document.getElementById('detail-content');
  el.innerHTML = '<div class="preview-empty">載入中...</div>';
  try {
    const resp = await fetch('/api/analyses/pending/' + encodeURIComponent(videoId));
    if (!resp.ok) {
      el.innerHTML = '<div class="preview-empty">找不到分析結果</div>';
      return;
    }
    const data = await resp.json();
    let html = renderAnalysisReport(data);
    html += `
      <div class="review-actions">
        <button class="btn btn-accent review-confirm-btn" onclick="doConfirmKB('${esc(videoId)}')">確認入庫</button>
        <button class="btn btn-danger review-reject-btn" onclick="doRejectVideo('${esc(videoId)}')">不符合探索主題</button>
      </div>`;
    el.innerHTML = html;
  } catch (e) {
    el.innerHTML = '<div class="preview-empty">載入失敗: ' + esc(e.message) + '</div>';
  }
}

async function doConfirmKB(videoId) {
  if (!confirm('確認將此分析結果入庫？')) return;
  try {
    const resp = await fetch('/api/trigger/confirm-kb', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ video_id: videoId }),
    });
    const data = await resp.json();
    if (data.error) {
      alert('Error: ' + data.error);
      return;
    }
    alert(`入庫成功！新增 ${data.entries_added} 條，更新 ${data.entries_updated} 條`);
    if (_currentCrawlId) {
      showCrawlDetail(_currentCrawlId);
    } else {
      closeDetail();
    }
  } catch (e) {
    alert('Failed: ' + e.message);
  }
}

async function doRejectVideo(videoId) {
  const reason = prompt('拒絕原因（選填）：', '不符合廢棄建築探索主題');
  if (reason === null) return;
  try {
    const resp = await fetch('/api/trigger/reject-video', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ video_id: videoId, reason: reason }),
    });
    const data = await resp.json();
    if (data.error) {
      alert('Error: ' + data.error);
      return;
    }
    if (_currentCrawlId) {
      showCrawlDetail(_currentCrawlId);
    } else {
      closeDetail();
    }
  } catch (e) {
    alert('Failed: ' + e.message);
  }
}

function formatDuration(input) {
  if (!input) return '-';
  let sec = input;
  // Handle ISO 8601 duration strings like "PT1H2M30S" or "PT120S"
  if (typeof input === 'string' && input.startsWith('PT')) {
    const match = input.match(/PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?/);
    if (match) {
      sec = (parseInt(match[1] || 0) * 3600) + (parseInt(match[2] || 0) * 60) + parseInt(match[3] || 0);
    } else {
      return input;
    }
  }
  sec = Math.round(Number(sec));
  if (isNaN(sec) || sec < 0) return '-';
  const m = Math.floor(sec / 60);
  const s = sec % 60;
  if (m >= 60) {
    const h = Math.floor(m / 60);
    return h + ':' + String(m % 60).padStart(2, '0') + ':' + String(s).padStart(2, '0');
  }
  return m + ':' + String(s).padStart(2, '0');
}

// ══════════════════════════════════════════
// Step 2: Analyze — Unified Video Table (Redesigned)
// ══════════════════════════════════════════

async function loadStep2Videos() {
  const el = document.getElementById('step2-video-table');
  if (!el) return;
  el.innerHTML = '<div class="preview-empty" style="padding:20px 0">載入中...</div>';

  try {
    const resp = await fetch('/api/all-videos');
    const data = (await resp.json()).data || [];
    _allVideos = data;
    renderStep2VideoTable(data);
  } catch (e) {
    el.innerHTML = '<div class="preview-empty" style="padding:20px 0">載入失敗</div>';
  }
}

function filterStep2Videos() {
  renderStep2VideoTable(_allVideos);
}

function renderStep2VideoTable(videos) {
  const el = document.getElementById('step2-video-table');
  if (!el) return;

  const filter = (document.getElementById('step2-filter') || {}).value || 'ready';
  let filtered = videos;
  const _hasSub = v => v.subtitle && v.subtitle.status === 'done' && v.subtitle.text;
  if (filter === 'ready') filtered = videos.filter(v => !v.kb_analyzed && _hasSub(v));
  else if (filter === 'unanalyzed') filtered = videos.filter(v => !v.kb_analyzed);
  else if (filter === 'analyzed') filtered = videos.filter(v => v.kb_analyzed);
  else if (filter === 'no-subtitle') filtered = videos.filter(v => !v.kb_analyzed && !_hasSub(v));

  const countEl = document.getElementById('step2-video-count');
  if (countEl) countEl.textContent = `共 ${filtered.length} 部`;

  if (!filtered.length) {
    el.innerHTML = '<div class="empty-state"><div class="empty-icon">&#128200;</div><p>暫無視頻</p></div>';
    _updateStep2BulkBar();
    return;
  }

  let html = `
    <table class="step2-table">
      <thead>
        <tr>
          <th style="width:32px"></th>
          <th>影片</th>
          <th>頻道</th>
          <th style="width:100px">字幕</th>
          <th style="width:80px">狀態</th>
          <th style="width:60px">操作</th>
        </tr>
      </thead>
      <tbody>`;

  for (const v of filtered) {
    const vid = v.video_id || '';
    const ytUrl = v.url || (vid ? `https://www.youtube.com/watch?v=${vid}` : '');
    const analyzed = !!v.kb_analyzed;
    html += `
      <tr>
        <td>${analyzed ? '' : `<input type="checkbox" class="step2-video-cb" value="${esc(vid)}" onchange="_updateStep2BulkBar()">`}</td>
        <td>
          <div class="step2-video-title">${esc(v.title || vid)}</div>
          ${ytUrl ? `<a href="${esc(ytUrl)}" target="_blank" rel="noopener" class="step2-yt-link">YouTube &#8599;</a>` : ''}
        </td>
        <td class="step2-channel">${esc(v.channel || '')}</td>
        <td>${(() => {
          const sub = v.subtitle;
          if (sub && sub.status === 'done' && sub.text) {
            const len = sub.text.length;
            const lang = sub.language ? ` [${sub.language}]` : '';
            return `<span class="step2-badge" style="background:#1a3a2a;color:#4ade80;font-size:11px">✅ ${len.toLocaleString()}字${lang}</span>`;
          } else if (sub && sub.status === 'pending') {
            return '<span class="step2-badge" style="background:#3a2a1a;color:#f59e0b;font-size:11px">⏸ 待處理</span>';
          } else {
            return '<span class="step2-badge" style="background:#2a1a1a;color:#888;font-size:11px">—</span>';
          }
        })()}</td>
        <td>${analyzed
          ? '<span class="step2-badge step2-badge-analyzed">已分析</span>'
          : '<span class="step2-badge step2-badge-unanalyzed">未分析</span>'
        }</td>
        <td>${analyzed ? '' : `<button class="btn btn-sm btn-danger" onclick="doStep2DeleteVideo('${esc(vid)}','${esc(v.title || '')}')">刪除</button>`}</td>
      </tr>`;
  }

  html += '</tbody></table>';
  el.innerHTML = html;
  _updateStep2BulkBar();
}

function _updateStep2BulkBar() {
  const cbs = [...document.querySelectorAll('.step2-video-cb')];
  const checked = cbs.filter(cb => cb.checked);
  const bulkBar = document.getElementById('step2-bulk-bar');
  const countEl = document.getElementById('step2-selected-count');
  const allCb = document.getElementById('step2-select-all-cb');

  if (!bulkBar) return;

  if (cbs.length > 0) {
    bulkBar.style.display = 'flex';
  } else {
    bulkBar.style.display = 'none';
  }

  if (countEl) countEl.textContent = `已選 ${checked.length} / ${cbs.length} 部`;
  if (allCb) {
    allCb.checked = cbs.length > 0 && checked.length === cbs.length;
    allCb.indeterminate = checked.length > 0 && checked.length < cbs.length;
  }
}

function step2ToggleSelectAll(checked) {
  document.querySelectorAll('.step2-video-cb').forEach(cb => cb.checked = checked);
  _updateStep2BulkBar();
}

async function doStep2KBBatchAnalyze() {
  const btn = document.getElementById('btn-step2-kb-batch');
  const cbs = [...document.querySelectorAll('.step2-video-cb:checked')];
  if (!cbs.length) {
    alert('請先勾選要分析的視頻');
    return;
  }
  const videoIds = cbs.map(cb => cb.value);
  if (!confirm(`確認批量分析入庫 ${videoIds.length} 部視頻？`)) return;
  _setBusy(btn, true);

  try {
    const resp = await fetch('/api/trigger/kb-analyze-batch', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ video_ids: videoIds }),
    });
    const data = await resp.json();
    if (!resp.ok || data.error) {
      alert(data.error || '觸發失敗');
      return;
    }
    alert('批量分析入庫已啟動！可在日誌面板查看進度。');
    refreshAll();
    setTimeout(() => loadStep2Videos(), 2000);
  } catch (e) {
    alert('Failed: ' + e.message);
  } finally {
    _setBusy(btn, false);
  }
}

async function doStep2DeleteVideo(videoId, title) {
  if (!confirm(`確認刪除「${title}」？將從所有搜尋結果中刪除，此操作不可恢復。`)) return;
  const video = _allVideos.find(v => v.video_id === videoId);
  const crawlIds = (video && video._crawl_ids) || _crawls.map(c => c.id);
  try {
    for (const crawlId of crawlIds) {
      await fetch(`/api/crawls/${crawlId}/videos/${videoId}`, { method: 'DELETE' });
    }
    loadStep2Videos();
  } catch (e) {
    alert('刪除失敗: ' + e.message);
  }
}

async function doStep2GenerateReport() {
  const btn = document.getElementById('btn-step2-report');
  const name = document.getElementById('analysis-name').value.trim();
  _setBusy(btn, true);
  try {
    const resp = await fetch('/api/trigger/analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name }),
    });
    const data = await resp.json();
    if (data.error) alert('Error: ' + data.error);
    else alert('分析報告生成中，可在日誌面板查看進度。');
    refreshAll();
  } catch (e) {
    alert('Failed: ' + e.message);
  } finally {
    _setBusy(btn, false);
  }
}

// ══════════════════════════════════════════
// Analyses View (sidebar nav)
// ══════════════════════════════════════════

async function loadAnalysesView() {
  const listEl = document.getElementById('analyses-list');
  const countEl = document.getElementById('analyses-count');
  if (!listEl) return;
  listEl.innerHTML = '<div class="preview-empty">載入中...</div>';

  try {
    const resp = await fetch('/api/analyses');
    const analyses = (await resp.json()).data || [];
    if (countEl) countEl.textContent = `共 ${analyses.length} 筆`;

    if (!analyses.length) {
      listEl.innerHTML = '<div class="empty-state" style="padding:40px 20px"><div class="empty-icon">&#128200;</div><p>尚無分析報告</p><p style="font-size:12px;color:var(--text-muted);margin-top:8px">請先完成爬蟲，然後在步驟 2 生成分析報告</p></div>';
      return;
    }

    listEl.innerHTML = analyses.slice().reverse().map(a => `
      <div class="analyses-list-item" onclick="showAnalysisInView('${esc(a.id)}')">
        <div class="ali-title">${esc(a.name || a.id)}</div>
        <div class="ali-meta">
          <span>來源 ${(a.source_crawl_ids || []).length} 批爬蟲</span>
          <span>${esc(a.created_at || '')}</span>
        </div>
      </div>
    `).join('');
  } catch (e) {
    listEl.innerHTML = '<div class="preview-empty">載入失敗</div>';
  }
}

async function showAnalysisInView(analysisId) {
  // Highlight selected
  document.querySelectorAll('.analyses-list-item').forEach(el => el.classList.remove('active'));
  const clickedEl = document.querySelector(`.analyses-list-item[onclick*="${analysisId}"]`);
  if (clickedEl) clickedEl.classList.add('active');

  const detailEl = document.getElementById('analyses-detail');
  if (!detailEl) return;
  detailEl.innerHTML = '<div class="preview-empty">載入中...</div>';

  try {
    const resp = await fetch('/api/analyses/' + analysisId);
    const data = (await resp.json()).data;
    if (!data) {
      detailEl.innerHTML = '<div class="empty-state"><div class="empty-icon">&#128200;</div><p>無資料</p></div>';
      return;
    }
    detailEl.innerHTML = `
      <div class="analyses-detail-header">
        <h3>&#128200; ${esc(data.name || analysisId)}</h3>
        <div style="font-size:12px;color:var(--text-muted)">${esc(data.created_at || '')}</div>
      </div>
      ${renderAnalysisReport(data)}`;
  } catch (e) {
    detailEl.innerHTML = '<div class="empty-state"><div class="empty-icon">&#128683;</div><p>載入失敗</p></div>';
  }
}

// ══════════════════════════════════════════
// Scripts Library View
// ══════════════════════════════════════════

async function loadScriptsView() {
  const listEl = document.getElementById('scripts-lib-list');
  const countEl = document.getElementById('scripts-lib-count');
  if (!listEl) return;
  listEl.innerHTML = '<div class="preview-empty">載入中...</div>';

  try {
    const resp = await fetch('/api/scripts');
    const scripts = (await resp.json()).data || [];
    if (countEl) countEl.textContent = `共 ${scripts.length} 筆`;

    if (!scripts.length) {
      listEl.innerHTML = '<div class="empty-state" style="padding:40px 20px"><div class="empty-icon">&#128221;</div><p>尚無劇本</p><p style="font-size:12px;color:var(--text-muted);margin-top:8px">請先在流程管線中生成劇本</p></div>';
      return;
    }

    listEl.innerHTML = scripts.slice().reverse().map(s => `
      <div class="analyses-list-item" onclick="showScriptInLibrary('${esc(s.id)}')">
        <div class="ali-title">${esc(s.title || s.id)}</div>
        <div class="ali-meta">
          <span>${s.tags === 'kb-series' ? '&#128218; KB' : '&#128221;'} ${esc(s.type || '')}</span>
          <span>${esc(s.created_at || '')}</span>
        </div>
      </div>
    `).join('');
  } catch (e) {
    listEl.innerHTML = '<div class="preview-empty">載入失敗</div>';
  }
}

async function showScriptInLibrary(scriptId) {
  // Highlight selected
  document.querySelectorAll('#scripts-lib-list .analyses-list-item').forEach(el => el.classList.remove('active'));
  const clickedEl = document.querySelector(`#scripts-lib-list .analyses-list-item[onclick*="${scriptId}"]`);
  if (clickedEl) clickedEl.classList.add('active');

  const detailEl = document.getElementById('scripts-lib-detail');
  if (!detailEl) return;
  detailEl.innerHTML = '<div class="preview-empty">載入中...</div>';

  try {
    const resp = await fetch('/api/scripts/' + scriptId);
    const data = (await resp.json()).data;
    if (!data) {
      detailEl.innerHTML = '<div class="empty-state"><div class="empty-icon">&#128221;</div><p>無資料</p></div>';
      return;
    }
    const script = data.script || data;
    const meta = data.meta || {};
    let html = `<div class="analyses-detail-header">
      <h3>&#128221; ${esc(script.series_title || script.title || scriptId)}</h3>
      <div style="font-size:12px;color:var(--text-muted)">${esc(meta.created_at || '')}</div>
    </div>`;
    html += _renderScriptContent(script, meta);
    html += `<div style="margin-top:16px"><button class="btn btn-sm btn-primary" onclick="showTrace('scripts','${esc(scriptId)}')">&#128279; 追溯鏈</button></div>`;
    detailEl.innerHTML = html;
  } catch (e) {
    detailEl.innerHTML = '<div class="empty-state"><div class="empty-icon">&#128683;</div><p>載入失敗</p></div>';
  }
}

// ══════════════════════════════════════════
// Step 2: Analysis History (kept)
// ══════════════════════════════════════════

function renderAnalysisHistory(analyses) {
  const el = document.getElementById('analysis-history-sidebar');
  if (!analyses.length) {
    el.innerHTML = '<div class="preview-empty" style="padding:12px 0;font-size:12px">尚無分析紀錄</div>';
    return;
  }
  el.innerHTML = analyses.slice().reverse().map(a => `
    <div class="history-item" onclick="showAnalysisInPanel('${esc(a.id)}')">
      <div class="hi-top">
        <div class="hi-main">
          <div class="hi-title">${esc(a.name || a.id)}</div>
          <div class="hi-meta">來源: ${(a.source_crawl_ids || []).length} 批 · ${esc(a.created_at)}</div>
        </div>
        <div class="hi-actions">
          <button class="trace-btn" onclick="event.stopPropagation();showTrace('analyses','${esc(a.id)}')">追溯</button>
        </div>
      </div>
    </div>
  `).join('');
}

async function showAnalysisInPanel(analysisId) {
  // Step 2 redesign removed the inline panel — delegate to overlay view
  showAnalysisDetail(analysisId);
}

async function showAnalysisDetail(analysisId) {
  openDetail('分析結果: ' + analysisId);
  const el = document.getElementById('detail-content');
  el.innerHTML = '<div class="preview-empty">載入中...</div>';
  try {
    const resp = await fetch('/api/analyses/' + analysisId);
    const data = (await resp.json()).data;
    if (!data) {
      el.innerHTML = '<div class="preview-empty">無資料</div>';
      return;
    }
    el.innerHTML = renderAnalysisReport(data);
  } catch (e) {
    el.innerHTML = '<div class="preview-empty">載入失敗</div>';
  }
}

function renderAnalysisReport(data) {
  let html = '';

  if (data.summary) {
    html += `<div class="analysis-summary">${esc(data.summary)}</div>`;
  }

  if (data.narrative_structure) {
    const ns = data.narrative_structure;
    html += '<div class="analysis-section"><h4>&#128214; 劇情結構分析</h4>';
    if (ns.opening_hook) html += `<div style="margin-bottom:8px"><strong>開場鉤子：</strong>${esc(ns.opening_hook)}</div>`;
    if (ns.rising_action) html += `<div style="margin-bottom:8px"><strong>上升動作：</strong>${esc(ns.rising_action)}</div>`;
    if (ns.climax) html += `<div style="margin-bottom:8px"><strong>高潮：</strong>${esc(ns.climax)}</div>`;
    if (ns.resolution) html += `<div style="margin-bottom:8px"><strong>結局：</strong>${esc(ns.resolution)}</div>`;
    if (ns.mini_climaxes && ns.mini_climaxes.length) {
      html += '<div style="margin-top:8px"><strong>小高潮：</strong><ul>';
      ns.mini_climaxes.forEach(mc => html += `<li>${esc(mc)}</li>`);
      html += '</ul></div>';
    }
    html += '</div>';
  }

  if (data.pacing) {
    html += '<div class="analysis-section"><h4>&#127928; 節奏分析</h4>';
    if (data.pacing.overall_tempo) html += `<div style="margin-bottom:8px"><strong>整體節奏：</strong>${esc(data.pacing.overall_tempo)}</div>`;
    if (data.pacing.tension_curve) html += `<div style="margin-bottom:8px"><strong>張力曲線：</strong>${esc(data.pacing.tension_curve)}</div>`;
    if (data.pacing.scene_rhythm) html += `<div style="margin-bottom:8px"><strong>場景節奏：</strong>${esc(data.pacing.scene_rhythm)}</div>`;
    if (data.pacing.cliffhanger_pattern) html += `<div><strong>懸念模式：</strong>${esc(data.pacing.cliffhanger_pattern)}</div>`;
    html += '</div>';
  }

  if (data.plot_twists && data.plot_twists.length) {
    html += '<div class="analysis-section"><h4>&#128260; 反轉與轉折</h4><ul>';
    data.plot_twists.forEach(t => html += `<li>${esc(typeof t === 'string' ? t : t.description || JSON.stringify(t))}</li>`);
    html += '</ul></div>';
  }

  if (data.common_themes && data.common_themes.length) {
    html += '<div class="analysis-section"><h4>&#127919; 共同主題</h4><ul>';
    data.common_themes.forEach(t => html += `<li>${esc(t)}</li>`);
    html += '</ul></div>';
  }

  if (data.hook_patterns && data.hook_patterns.length) {
    html += '<div class="analysis-section"><h4>&#129693; 鉤子模式</h4><ul>';
    data.hook_patterns.forEach(h => html += `<li>${esc(h)}</li>`);
    html += '</ul></div>';
  }

  if (data.emotional_arcs && data.emotional_arcs.length) {
    html += '<div class="analysis-section"><h4>&#128147; 情感曲線</h4><ul>';
    data.emotional_arcs.forEach(a => html += `<li>${esc(a)}</li>`);
    html += '</ul></div>';
  }

  if (data.character_archetypes && data.character_archetypes.length) {
    html += '<div class="analysis-section"><h4>&#128100; 角色原型</h4><ul>';
    data.character_archetypes.forEach(c => html += `<li>${esc(c)}</li>`);
    html += '</ul></div>';
  }

  if (data.story_structures && data.story_structures.length) {
    html += '<div class="analysis-section"><h4>&#128218; 故事結構模式</h4><ul>';
    data.story_structures.forEach(s => html += `<li>${esc(s)}</li>`);
    html += '</ul></div>';
  }

  if (data.dialogue_patterns && data.dialogue_patterns.length) {
    html += '<div class="analysis-section"><h4>&#128172; 對白模式</h4><ul>';
    data.dialogue_patterns.forEach(d => html += `<li>${esc(d)}</li>`);
    html += '</ul></div>';
  }

  if (data.recommended_elements && data.recommended_elements.length) {
    html += '<div class="analysis-section"><h4>&#128161; 建議元素</h4><ul>';
    data.recommended_elements.forEach(r => html += `<li>${esc(r)}</li>`);
    html += '</ul></div>';
  }

  if (data.benchmark) {
    html += '<div class="analysis-section"><h4>&#128202; 基準數據</h4>';
    const b = data.benchmark;
    if (b.avg_scene_count) html += `<div>平均場景數: ${b.avg_scene_count}</div>`;
    if (b.avg_duration_sec) html += `<div>平均時長: ${formatDuration(b.avg_duration_sec)}</div>`;
    if (b.avg_dialogue_ratio) html += `<div>對白佔比: ${b.avg_dialogue_ratio}</div>`;
    html += '</div>';
  }

  if (!html) {
    html = '<div class="json-block">' + esc(JSON.stringify(data, null, 2)) + '</div>';
  }

  return html;
}

// ══════════════════════════════════════════
// Step 3: Generate Script — KB Cards (NEW)
// ══════════════════════════════════════════

// All KB categories to show as card rows
// tier: 'core' = recommended to select, 'aux' = optional
const KB_CARD_CATEGORIES = [
  { key: 'building_types', label: '建築類型', tier: 'core', apiUrl: '/api/knowledge/building_types' },
  { key: 'building_backstories', label: '廢棄原因', tier: 'core', apiUrl: '/api/knowledge/building_backstories' },
  { key: 'exploration_zones', label: '探索區域', tier: 'core', apiUrl: '/api/knowledge/exploration_zones' },
  { key: 'route_paths', label: '動線路徑', tier: 'core', apiUrl: '/api/knowledge/route_paths' },
  { key: 'encounters', label: '遭遇事件', tier: 'core', apiUrl: '/api/knowledge/encounters' },
  { key: 'found_items', label: '發現物品', tier: 'core', apiUrl: '/api/knowledge/found_items' },
  { key: 'traps_hazards', label: '陷阱/危險', tier: 'aux', apiUrl: '/api/knowledge/traps_hazards' },
  { key: 'narrative_clues', label: '敘事線索', tier: 'aux', apiUrl: '/api/knowledge/narrative_clues' },
  { key: 'time_settings', label: '時間設定', tier: 'aux', apiUrl: '/api/knowledge/time_settings' },
  { key: 'weather_conditions', label: '天氣狀況', tier: 'aux', apiUrl: '/api/knowledge/weather_conditions' },
  { key: 'ambient_triggers', label: '氛圍觸發', tier: 'aux', apiUrl: '/api/knowledge/ambient_triggers' },
  { key: 'tension_curves', label: '張力曲線', tier: 'aux', apiUrl: '/api/knowledge/tension_curves' },
  { key: 'ending_types', label: '結局類型', tier: 'aux', apiUrl: '/api/knowledge/ending_types' },
  { key: 'exploration_motives', label: '探索動機', tier: 'aux', apiUrl: '/api/knowledge/exploration_motives' },
  { key: 'explorer_equipment', label: '探索者裝備', tier: 'aux', apiUrl: '/api/knowledge/explorer_equipment' },
];

let _kbSkeletonBuilt = false;

async function loadStep3KBCards() {
  const panel = document.getElementById('kb-cards-panel');
  if (!panel) return;

  // First check if KB has any data
  try {
    const statsResp = await fetch('/api/knowledge/stats');
    const stats = await statsResp.json();
    if ((stats.total || 0) === 0) {
      _kbSkeletonBuilt = false;
      panel.innerHTML = `
        <div class="empty-state" style="padding:60px 20px">
          <div class="empty-icon">&#128218;</div>
          <p style="font-size:16px;margin-bottom:8px">知識庫還沒有資料</p>
          <p style="font-size:13px;color:var(--text-muted)">請先完成爬蟲和分析步驟，將視頻入庫後再生成劇本</p>
        </div>`;
      return;
    }
  } catch (e) {
    // proceed anyway
  }

  // Build skeleton only once
  if (!_kbSkeletonBuilt) {
    _kbSkeletonBuilt = true;
    let html = '';
    let lastTier = '';
    for (const cat of KB_CARD_CATEGORIES) {
      if (cat.tier !== lastTier) {
        lastTier = cat.tier;
        const tierLabel = cat.tier === 'core' ? '&#11088; 核心元素（建議優先選擇）' : '&#128736; 輔助元素（按需選擇）';
        html += `<div class="kb-tier-divider">${tierLabel}</div>`;
      }
      const tierBadge = cat.tier === 'core' ? '<span class="tier-badge tier-core">核心</span>' : '<span class="tier-badge tier-aux">輔助</span>';
      html += `
        <div class="kb-row" id="kb-row-${cat.key}">
          <div class="kb-row-header">
            <div class="kb-row-label">${tierBadge} ${esc(cat.label)}</div>
            <div class="kb-row-helper">不選 = AI 自由發揮</div>
          </div>
          <div class="kb-row-scroll">
            <div class="kb-row-cards" id="kb-row-cards-${cat.key}">
              <span class="kb-sel-loading">載入中...</span>
            </div>
          </div>
        </div>`;
    }
    panel.innerHTML = html;
  }

  // Always reload card data (preserves selections)
  await Promise.all(KB_CARD_CATEGORIES.map(cat => _loadKBCardRow(cat)));
}

// Category emoji map
const KB_CAT_ICONS = {
  building_types: '&#127970;', building_backstories: '&#128293;', exploration_zones: '&#127759;',
  route_paths: '&#128739;', encounters: '&#128123;', found_items: '&#128230;',
  traps_hazards: '&#9888;', narrative_clues: '&#128270;', time_settings: '&#127761;',
  weather_conditions: '&#127783;', ambient_triggers: '&#127787;', tension_curves: '&#128200;',
  ending_types: '&#127937;', exploration_motives: '&#128269;', explorer_equipment: '&#128294;',
};

async function _loadKBCardRow(cat) {
  const container = document.getElementById('kb-row-cards-' + cat.key);
  if (!container) return;

  try {
    const resp = await fetch(cat.apiUrl);
    const data = await resp.json();
    const entries = data.data || data.entries || data.items || (Array.isArray(data) ? data : []);

    if (!entries.length) {
      container.innerHTML = '<span class="kb-row-empty">尚無資料</span>';
      return;
    }

    const icon = KB_CAT_ICONS[cat.key] || '&#128218;';
    container.innerHTML = entries.map(e => {
      const selected = _kbCardSelections[cat.key] === e.id;
      const desc = (e.description || '').slice(0, 60);
      const seed = isSeedData(e);
      return `
        <div class="kb-card-item${selected ? ' kb-card-selected' : ''}${seed ? ' kb-card-seed' : ''}"
             data-id="${esc(e.id)}" data-cat="${esc(cat.key)}"
             onclick="selectKBCard(this, '${esc(cat.key)}', '${esc(e.id)}')"
             style="cursor:pointer">
          <div class="kb-card-item-icon">${icon}</div>
          <div class="kb-card-item-name">${esc(e.name || e.id)}${seed ? ' <span class="seed-badge">種子</span>' : ''}</div>
          <div class="kb-card-item-desc">${esc(desc)}${desc.length < (e.description||'').length ? '...' : ''}</div>
          <button class="kb-card-expand-btn" onclick="expandKBCard('${esc(cat.key)}','${esc(e.id)}',event)" title="展開詳情">&#8942;</button>
        </div>`;
    }).join('');
  } catch (err) {
    container.innerHTML = `<span class="kb-row-empty">載入失敗</span>`;
  }
}

async function expandKBCard(catKey, entryId, event) {
  event.stopPropagation();
  // Map card keys to actual KB category names
  const apiCat = catKey;
  try {
    const resp = await fetch('/api/knowledge/' + apiCat + '/' + encodeURIComponent(entryId));
    if (!resp.ok) return;
    const entry = (await resp.json()).data;
    if (!entry) return;
    openDetail(`${entry.name || entryId}`);
    const el = document.getElementById('detail-content');
    let html = `
      <div style="margin-bottom:16px">
        <h3 style="margin:0 0 4px">${esc(entry.name || entry.id)}
          ${entry.name_en ? '<span style="color:var(--text-muted);font-size:0.85rem"> · ' + esc(entry.name_en) + '</span>' : ''}
        </h3>
        <div style="display:flex;gap:6px;align-items:center;margin-bottom:8px">
          <span class="tag">${esc(catKey)}</span>
          ${entry.subcategory ? '<span class="tag tag-outline">' + esc(entry.subcategory) + '</span>' : ''}
          ${entry.effectiveness_score ? '<span class="score-badge" style="margin-left:auto">效果分: ' + entry.effectiveness_score + '</span>' : ''}
        </div>
        <p style="color:var(--text-primary);font-size:0.9rem;line-height:1.7">${esc(entry.description || '')}</p>
      </div>`;
    if ((entry.tags || []).length) {
      html += '<div style="margin-bottom:12px">' + entry.tags.map(t => '<span class="tag tag-sm" style="margin-right:4px">' + esc(t) + '</span>').join('') + '</div>';
    }
    if ((entry.examples || []).length) {
      html += '<h4 style="color:var(--accent-light);margin-bottom:8px">範例片段</h4>';
      for (const ex of entry.examples) {
        html += `<div class="analysis-section" style="margin-bottom:8px">
          <div style="font-weight:600;margin-bottom:4px">${esc(ex.video_title || ex.drama_title || '未知影片')}</div>
          <div style="font-size:0.85rem;border-left:3px solid var(--accent);padding-left:12px;margin-top:4px">${esc(ex.excerpt || '')}</div>
          ${ex.context ? '<div style="font-size:0.8rem;color:var(--text-muted);margin-top:4px">' + esc(ex.context) + '</div>' : ''}
        </div>`;
      }
    }
    html += `
      <div style="margin-top:16px;padding-top:12px;border-top:1px solid var(--border)">
        <button class="btn btn-accent" onclick="selectKBCardById('${esc(catKey)}','${esc(entryId)}');closeDetail()">
          選擇此元素
        </button>
      </div>`;
    el.innerHTML = html;
  } catch (e) {
    openDetail('載入失敗');
  }
}

function selectKBCardById(catKey, entryId) {
  const row = document.getElementById('kb-row-cards-' + catKey);
  if (!row) return;
  const el = row.querySelector(`[data-id="${entryId}"]`);
  if (el) selectKBCard(el, catKey, entryId);
}

function selectKBCard(el, catKey, entryId) {
  const row = document.getElementById('kb-row-cards-' + catKey);
  if (!row) return;

  // If already selected, deselect
  if (_kbCardSelections[catKey] === entryId) {
    _kbCardSelections[catKey] = null;
    el.classList.remove('kb-card-selected');
    return;
  }

  // Deselect previous in same category
  row.querySelectorAll('.kb-card-selected').forEach(c => c.classList.remove('kb-card-selected'));

  // Select new
  _kbCardSelections[catKey] = entryId;
  el.classList.add('kb-card-selected');
}

function _getSelectedElements() {
  // Build selected_elements for the API
  const result = {};
  for (const cat of KB_CARD_CATEGORIES) {
    const id = _kbCardSelections[cat.key];
    if (id) {
      if (!result[cat.key]) result[cat.key] = [];
      result[cat.key].push(id);
    }
  }
  return result;
}

function _getSelectedGenreStyle() {
  // Look up building/zone names from selected KB card IDs
  const result = {};
  for (const cat of KB_CARD_CATEGORIES) {
    if (cat.key !== 'buildings' && cat.key !== 'zones') continue;
    const id = _kbCardSelections[cat.key];
    if (id) {
      const row = document.getElementById('kb-row-cards-' + cat.key);
      if (row) {
        const card = row.querySelector(`[data-id="${id}"] .kb-card-item-name`);
        if (card) result[cat.key] = card.textContent.trim();
      }
    }
  }
  return result;
}

async function doGenerateKB() {
  const btn = document.getElementById('btn-generate-kb');
  if (btn && btn.disabled) return;
  _setBusy(btn, true);

  const requirements = document.getElementById('gen-requirements').value.trim();
  const episodeCount = _genMode === 'series' ? (parseInt(document.getElementById('gen-episodes').value) || 30) : 1;
  const selected_elements = _getSelectedElements();

  try {
    const resp = await fetch('/api/trigger/generate-kb', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        episode_count: episodeCount,
        duration_sec: _durationSec,
        human_requirements: requirements,
        selected_elements,
        ..._getSelectedGenreStyle(),
      }),
    });
    const data = await resp.json();
    if (data.error) alert('Error: ' + data.error);
    else alert('劇本生成中！可在日誌面板查看進度，完成後在左側劇本紀錄查看結果。');
    refreshAll();
  } catch (e) {
    alert('Failed: ' + e.message);
  } finally {
    _setBusy(btn, false);
  }
}

function renderScriptHistory(scripts) {
  const el = document.getElementById('script-history-sidebar');
  if (!scripts.length) {
    el.innerHTML = '<div class="preview-empty" style="padding:12px 0;font-size:12px">尚無劇本</div>';
    return;
  }
  el.innerHTML = scripts.slice().reverse().map(s => `
    <div class="history-item" onclick="showScriptInPanel('${esc(s.id)}')">
      <div class="hi-top">
        <div class="hi-main">
          <div class="hi-title">${esc(s.title || s.id)} ${s.type === 'kb-series' ? '<span class="tag tag-sm" style="background:var(--green);color:#000">KB</span>' : ''}</div>
          <div class="hi-meta">${esc(s.type || '')} · ${esc(s.created_at)}</div>
        </div>
        <div class="hi-actions">
          <button class="trace-btn" onclick="event.stopPropagation();showTrace('scripts','${esc(s.id)}')">追溯</button>
        </div>
      </div>
    </div>
  `).join('');
}

async function showScriptInPanel(scriptId) {
  // Show the script preview section and hide KB cards
  const previewSection = document.getElementById('script-preview-section');
  if (previewSection) previewSection.style.display = '';
  const el = document.getElementById('script-results');
  el.innerHTML = '<div class="preview-empty">載入中...</div>';
  document.getElementById('script-results-meta').textContent = '';

  try {
    const resp = await fetch('/api/scripts/' + scriptId);
    const json = await resp.json();
    const script = json.data;
    const meta = json.meta;
    if (!script) {
      el.innerHTML = '<div class="empty-state"><div class="empty-icon">&#128221;</div><p>無資料</p></div>';
      return;
    }

    document.getElementById('script-results-meta').textContent = esc(script.title || script.series_title || scriptId);
    el.innerHTML = _renderScriptContent(script, meta);
  } catch (e) {
    el.innerHTML = '<div class="empty-state"><div class="empty-icon">&#128683;</div><p>載入失敗</p></div>';
  }
}

async function showScriptDetail(scriptId) {
  openDetail('劇本: ' + scriptId);
  const el = document.getElementById('detail-content');
  el.innerHTML = '<div class="preview-empty">載入中...</div>';
  try {
    const resp = await fetch('/api/scripts/' + scriptId);
    const json = await resp.json();
    const script = json.data;
    const meta = json.meta;
    if (!script) {
      el.innerHTML = '<div class="preview-empty">無資料</div>';
      return;
    }
    el.innerHTML = _renderScriptContent(script, meta);
  } catch (e) {
    el.innerHTML = '<div class="preview-empty">載入失敗: ' + esc(e.message) + '</div>';
  }
}

function _renderScriptContent(script, meta) {
  let html = '';
  html += `<h3 style="margin:0 0 4px">${esc(script.title || script.series_title || '')}
    <span style="color:var(--text-muted);font-size:0.85rem">${esc(script.genre || '')}</span></h3>`;
  html += `<p style="color:var(--text-muted);font-size:0.9rem;margin-bottom:16px">${esc(script.logline || '')}</p>`;

  if (meta && meta.human_requirements) {
    html += `<div style="margin-bottom:12px;padding:8px 12px;background:var(--accent-bg);border-radius:6px;font-size:0.85rem">
      <strong>人為要求:</strong> ${esc(meta.human_requirements)}</div>`;
  }

  // KB elements display — prefer _kb_combination (actual entry IDs) over kb_elements_used (text from Claude)
  const _kbCatLabels = {buildings:'建築', routes:'路線', zones:'區域', encounters:'遭遇', found_items:'發現物品', traps:'陷阱/危機', clues:'線索', atmosphere:'氛圍', endings:'結局', tension_curves:'張力曲線', series_hooks:'系列連結'};
  if (script._kb_combination) {
    const userSel = script._kb_user_selected || [];
    html += '<div style="margin-bottom:12px;padding:8px 12px;background:rgba(0,184,148,0.1);border-radius:6px;font-size:0.85rem">';
    html += '<strong>知識庫元素（組合）:</strong><br>';
    for (const [cat, ids] of Object.entries(script._kb_combination)) {
      if (!ids || !ids.length) continue;
      const label = _kbCatLabels[cat] || cat;
      const source = userSel.includes(cat) ? ' \ud83d\udc64 用戶指定' : ' \ud83c\udfb2 隨機';
      html += `<span style="color:var(--text-secondary)">${esc(label)}</span>${source}: ${ids.map(id => '<code style="font-size:0.75rem;background:var(--bg-tertiary);padding:1px 4px;border-radius:3px">' + esc(id) + '</code>').join(', ')}<br>`;
    }
    html += '</div>';
  } else if (script.kb_elements_used) {
    html += '<div style="margin-bottom:12px;padding:8px 12px;background:rgba(0,184,148,0.1);border-radius:6px;font-size:0.85rem">';
    html += '<strong>知識庫元素:</strong><br>';
    const kbe = script.kb_elements_used;
    if (kbe.buildings) html += `建築: ${Array.isArray(kbe.buildings) ? kbe.buildings.map(b => esc(b)).join(', ') : esc(kbe.buildings)}<br>`;
    if (kbe.zones) html += `區域: ${Array.isArray(kbe.zones) ? kbe.zones.map(z => esc(z)).join(', ') : esc(kbe.zones)}<br>`;
    if (kbe.encounters) html += `遭遇: ${Array.isArray(kbe.encounters) ? kbe.encounters.map(e => esc(e)).join(', ') : esc(kbe.encounters)}<br>`;
    if (kbe.found_items) html += `發現物品: ${Array.isArray(kbe.found_items) ? kbe.found_items.map(f => esc(f)).join(', ') : esc(kbe.found_items)}<br>`;
    if (kbe.traps) html += `陷阱/危機: ${Array.isArray(kbe.traps) ? kbe.traps.map(h => esc(h)).join(', ') : esc(kbe.traps)}`;
    html += '</div>';
  }

  if (script.characters && script.characters.length) {
    html += '<h4 style="margin-bottom:8px;color:var(--accent-light)">角色</h4>';
    html += '<div class="char-grid">';
    for (const c of script.characters) {
      html += `<div class="char-card">
        <div class="char-name">${esc(c.name || '')} <span style="font-size:0.8rem;color:var(--text-muted)">${esc(c.role || '')}</span></div>
        <div class="char-detail">
          ${esc(c.gender || '')} · ${esc(c.age_range || '')}<br>
          ${esc(c.hair || '')}<br>
          ${esc(c.outfit || '')}<br>
          ${esc(c.personality || '')}
        </div>
      </div>`;
    }
    html += '</div>';
  }

  if (script.episodes && script.episodes.length) {
    html += '<h4 style="margin:16px 0 8px;color:var(--accent-light)">劇集</h4>';
    for (const ep of script.episodes) {
      html += `<div class="episode-card" onclick="this.querySelector('.ep-summary')&&this.querySelector('.ep-summary').classList.toggle('hidden')">
        <div class="ep-header">
          <div>
            <div class="ep-number">第 ${ep.episode_number || ''} 集</div>
            <div class="ep-title">${esc(ep.title || '')}</div>
          </div>
          <span class="ep-chevron">&#9654;</span>
        </div>
        ${ep.summary ? '<div class="ep-summary">' + esc(ep.summary) + '</div>' : ''}
      </div>`;
    }
  }

  if (script.scenes && script.scenes.length) {
    html += '<h4 style="margin:16px 0 8px;color:var(--accent-light)">場景</h4>';
    html += '<div class="scene-cards">';
    for (const s of script.scenes) {
      html += `<div class="scene-card">
        <div class="scene-num">Scene ${s.scene_number} <span style="color:var(--text-muted)">(${s.duration_sec || '?'}s)</span></div>
        <div class="scene-loc">${esc(s.location || '')} ${esc(s.location_en || '')}</div>
        <div class="scene-action">${esc(s.action_zh || '')}</div>
        ${s.dialogue_zh ? '<div class="scene-dialogue">' + esc(s.dialogue_zh) + '</div>' : ''}
      </div>`;
    }
    html += '</div>';
  }

  return html;
}

function populateScriptSelect(scripts) {
  const sel = document.getElementById('sb-script-select');
  const cur = sel.value;
  let html = '<option value="">-- 選擇劇本 --</option>';
  for (const s of scripts.slice().reverse()) {
    html += `<option value="${esc(s.id)}">${esc(s.title || s.id)} (${esc(s.created_at)})</option>`;
  }
  sel.innerHTML = html;
  if (cur) sel.value = cur;
}

// ══════════════════════════════════════════
// Step 4: Storyboard
// ══════════════════════════════════════════

async function doStoryboard() {
  const btn = document.getElementById('btn-storyboard');
  if (btn && btn.disabled) return;

  const scriptId = document.getElementById('sb-script-select').value;
  if (!scriptId) {
    alert('請選擇劇本');
    return;
  }

  _setBusy(btn, true);
  try {
    const resp = await fetch('/api/trigger/storyboard', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ source_script_id: scriptId }),
    });
    const data = await resp.json();
    if (data.error) alert('Error: ' + data.error);
    refreshAll();
  } catch (e) {
    alert('Failed: ' + e.message);
  } finally {
    _setBusy(btn, false);
  }
}

function renderStoryboardHistory(storyboards) {
  const el = document.getElementById('storyboard-history-sidebar');
  if (!storyboards.length) {
    el.innerHTML = '<div class="preview-empty" style="padding:12px 0;font-size:12px">尚無分鏡</div>';
    return;
  }
  el.innerHTML = storyboards.slice().reverse().map(sb => `
    <div class="history-item" onclick="showStoryboardInPanel('${esc(sb.id)}')">
      <div class="hi-top">
        <div class="hi-main">
          <div class="hi-title">${esc(sb.script_title || sb.source_script_id)}</div>
          <div class="hi-meta">${sb.frame_count} 個畫面 · ${esc(sb.created_at)}</div>
        </div>
        <div class="hi-actions">
          <button class="trace-btn" onclick="event.stopPropagation();showTrace('storyboards','${esc(sb.id)}')">追溯</button>
        </div>
      </div>
    </div>
  `).join('');
}

async function showStoryboardInPanel(sbId) {
  const el = document.getElementById('storyboard-results');
  el.innerHTML = '<div class="preview-empty">載入中...</div>';
  document.getElementById('storyboard-results-meta').textContent = '';

  try {
    const resp = await fetch('/api/storyboards/' + sbId);
    const json = await resp.json();
    const frames = json.data || [];
    if (!frames.length) {
      el.innerHTML = '<div class="empty-state"><div class="empty-icon">&#127916;</div><p>無分鏡資料</p></div>';
      return;
    }
    document.getElementById('storyboard-results-meta').textContent = `${frames.length} 個鏡頭`;
    el.innerHTML = _renderStoryboardGrid(frames);
  } catch (e) {
    el.innerHTML = '<div class="empty-state"><div class="empty-icon">&#128683;</div><p>載入失敗</p></div>';
  }
}

async function showStoryboardDetail(sbId) {
  openDetail('分鏡: ' + sbId);
  const el = document.getElementById('detail-content');
  el.innerHTML = '<div class="preview-empty">載入中...</div>';
  try {
    const resp = await fetch('/api/storyboards/' + sbId);
    const json = await resp.json();
    const frames = json.data || [];
    if (!frames.length) {
      el.innerHTML = '<div class="preview-empty">無分鏡資料</div>';
      return;
    }
    el.innerHTML = `<p style="color:var(--text-muted);margin-bottom:12px">${frames.length} 個分鏡畫面</p>` + _renderStoryboardGrid(frames);
  } catch (e) {
    el.innerHTML = '<div class="preview-empty">載入失敗</div>';
  }
}

function _renderStoryboardGrid(frames) {
  return `<div class="storyboard-grid">
    ${frames.map((f, i) => {
      const colors = [
        'linear-gradient(135deg,#1a1a2e,#16213e)',
        'linear-gradient(135deg,#0f3460,#1a1a2e)',
        'linear-gradient(135deg,#1a1a2e,#2d1b69)',
        'linear-gradient(135deg,#533483,#1a1a2e)',
        'linear-gradient(135deg,#1a1a2e,#1b4332)',
        'linear-gradient(135deg,#1a1a2e,#3d0000)',
      ];
      const bgStyle = colors[i % colors.length];
      return `
        <div class="storyboard-card">
          <div class="sb-image" style="background:${bgStyle}">
            <span class="scene-num">#${i + 1}</span>
            <span style="opacity:0.5;font-size:0.7em">場景${f.scene_number || '?'} · ${f.duration_sec || '?'}s</span>
          </div>
          <div class="sb-content">
            ${f.image_prompt ? '<div class="sb-field"><div class="sb-field-label">Image Prompt</div><div class="sb-field-value">' + esc(f.image_prompt) + '</div></div>' : ''}
            ${f.video_prompt ? '<div class="sb-field"><div class="sb-field-label">Video Prompt</div><div class="sb-field-value">' + esc(f.video_prompt) + '</div></div>' : ''}
            ${f.subtitle_zh ? '<div class="sb-field"><div class="sb-field-label">字幕</div><div class="sb-field-value">' + esc(f.subtitle_zh) + (f.subtitle_en ? ' / ' + esc(f.subtitle_en) : '') + '</div></div>' : ''}
            ${f.duration_sec ? '<div class="sb-field"><div class="sb-field-label">時長</div><div class="sb-field-value">' + f.duration_sec + 's</div></div>' : ''}
          </div>
        </div>`;
    }).join('')}
  </div>`;
}

// ══════════════════════════════════════════
// Step 5: Image Generation
// ══════════════════════════════════════════

function populateStoryboardSelect(storyboards) {
  const sel = document.getElementById('img-storyboard-select');
  if (!sel) return;
  const cur = sel.value;
  let html = '<option value="">-- 選擇分鏡 --</option>';
  for (const sb of storyboards.slice().reverse()) {
    html += `<option value="${esc(sb.id)}">${esc(sb.script_title || sb.source_script_id)} (${sb.frame_count} 鏡 · ${esc(sb.created_at)})</option>`;
  }
  sel.innerHTML = html;
  if (cur) sel.value = cur;
}

async function doGenerateImages() {
  const btn = document.getElementById('btn-gen-images');
  if (btn && btn.disabled) return;

  const storyboardId = document.getElementById('img-storyboard-select').value;
  if (!storyboardId) {
    alert('請選擇分鏡表');
    return;
  }

  const stylePrefix = (document.getElementById('img-style-prefix') || {}).value || '';

  _setBusy(btn, true);

  // Show progress bar
  const progressEl = document.getElementById('img-gen-progress');
  if (progressEl) progressEl.style.display = '';
  _updateImageProgress(0, 0, '準備中...');

  try {
    const resp = await fetch('/api/trigger/generate-images', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ storyboard_id: storyboardId, style_prefix: stylePrefix }),
    });
    const data = await resp.json();
    if (data.error) {
      alert('Error: ' + data.error);
      if (progressEl) progressEl.style.display = 'none';
      return;
    }

    // Poll task for progress
    const taskId = data.task_id;
    _pollImageTask(taskId);
  } catch (e) {
    alert('Failed: ' + e.message);
    if (progressEl) progressEl.style.display = 'none';
  } finally {
    _setBusy(btn, false);
  }
}

function _pollImageTask(taskId) {
  const poll = async () => {
    try {
      const resp = await fetch('/api/task/' + taskId);
      const task = await resp.json();

      // Update progress
      if (task.progress) {
        _updateImageProgress(task.progress.current, task.progress.total, task.progress.step);
      }

      if (task.status === 'done') {
        _updateImageProgress(task.progress.total, task.progress.total, '完成！');
        if (task.result && task.result.image_set_id) {
          showImageSetInPanel(task.result.image_set_id);
        }
        refreshAll();
        setTimeout(() => {
          const progressEl = document.getElementById('img-gen-progress');
          if (progressEl) progressEl.style.display = 'none';
        }, 3000);
        return;
      }
      if (task.status === 'error') {
        _updateImageProgress(0, 0, '生圖失敗: ' + (task.error || '未知錯誤'));
        alert('生圖失敗: ' + (task.error || '未知錯誤'));
        refreshAll();
        return;
      }
      setTimeout(poll, 3000);
    } catch (e) {
      setTimeout(poll, 5000);
    }
  };
  setTimeout(poll, 2000);
}

function _updateImageProgress(current, total, message) {
  const bar = document.getElementById('img-gen-progress-bar');
  const text = document.getElementById('img-gen-progress-text');
  if (bar) {
    const pct = total > 0 ? Math.round(current / total * 100) : 0;
    bar.style.width = pct + '%';
  }
  if (text) {
    text.textContent = total > 0 ? `[${current}/${total}] ${message}` : message;
  }
}

function renderImageHistory(imageSets) {
  const el = document.getElementById('image-history-sidebar');
  if (!el) return;
  if (!imageSets.length) {
    el.innerHTML = '<div class="preview-empty" style="padding:12px 0;font-size:12px">尚無生圖紀錄</div>';
    return;
  }
  el.innerHTML = imageSets.map(s => `
    <div class="history-item" onclick="showImageSetInPanel('${esc(s.id || s.image_set_id)}')">
      <div class="hi-top">
        <div class="hi-main">
          <div class="hi-title">${esc(s.image_set_id || s.id)}</div>
          <div class="hi-meta">${s.success_count || 0}/${s.total_frames || 0} 張成功${s.style_prefix ? ' · ' + esc(s.style_prefix.substring(0, 30)) : ''}</div>
        </div>
      </div>
    </div>
  `).join('');
}

async function showImageSetInPanel(setId) {
  const el = document.getElementById('image-results');
  el.innerHTML = '<div class="preview-empty">載入中...</div>';
  document.getElementById('image-results-meta').textContent = '';

  try {
    const resp = await fetch('/api/image-sets/' + encodeURIComponent(setId));
    const json = await resp.json();
    const meta = json.data || {};
    const frames = meta.frames || [];
    if (!frames.length) {
      el.innerHTML = '<div class="empty-state"><div class="empty-icon">&#128444;</div><p>無圖片資料</p></div>';
      return;
    }

    const successCount = frames.filter(f => f.status === 'ok').length;
    document.getElementById('image-results-meta').textContent = `${successCount}/${frames.length} 張圖片`;

    el.innerHTML = `<div class="frame-card-grid">
      ${frames.map((f, i) => {
        const num = f.frame_number || (i + 1);
        if (f.status === 'ok' && f.image_path) {
          const imgUrl = '/api/images/' + encodeURIComponent(setId) + '/frame_' + String(num).padStart(3, '0') + '.png';
          return `
            <div class="frame-card">
              <div class="frame-card-img">
                <img src="${imgUrl}" alt="Frame ${num}" loading="lazy">
                <span class="scene-num">#${num}</span>
              </div>
              <div class="frame-card-body">
                ${f.image_prompt ? '<div class="frame-card-prompt">' + esc(f.image_prompt) + '</div>' : ''}
              </div>
            </div>`;
        } else {
          return `
            <div class="frame-card frame-card-error">
              <div class="frame-card-img frame-card-img-error">
                <span class="scene-num">#${num}</span>
                <span style="color:var(--red);font-size:12px">${esc(f.error || '生成失敗')}</span>
              </div>
              <div class="frame-card-body">
                ${f.image_prompt ? '<div class="frame-card-prompt">' + esc(f.image_prompt) + '</div>' : ''}
              </div>
            </div>`;
        }
      }).join('')}
    </div>`;
  } catch (e) {
    el.innerHTML = '<div class="empty-state"><div class="empty-icon">&#128683;</div><p>載入失敗</p></div>';
  }
}

// ══════════════════════════════════════════
// Step 6: Video Generation
// ══════════════════════════════════════════

let _videoSets = [];
let _selectedVideoDuration = 5;
let _selectedVideoMode = 'std';

function setVideoDuration(dur) {
  _selectedVideoDuration = dur;
  document.querySelectorAll('[data-viddur]').forEach(b => b.classList.toggle('active', parseInt(b.dataset.viddur) === dur));
}

function setVideoMode(mode) {
  _selectedVideoMode = mode;
  document.getElementById('vid-mode-std').classList.toggle('active', mode === 'std');
  document.getElementById('vid-mode-pro').classList.toggle('active', mode === 'pro');
}

function populateImageSelect(imageSets) {
  const sel = document.getElementById('vid-image-select');
  if (!sel) return;
  const cur = sel.value;
  let html = '<option value="">-- 選擇已生成的分鏡圖 --</option>';
  for (const s of (imageSets || []).slice().reverse()) {
    const id = s.id || s.image_set_id;
    const label = `${id} (${s.success_count || 0}/${s.total_frames || 0} 張)`;
    html += `<option value="${esc(id)}">${esc(label)}</option>`;
  }
  sel.innerHTML = html;
  if (cur) sel.value = cur;
}

async function doGenerateVideos() {
  const btn = document.getElementById('btn-gen-video');
  if (btn && btn.disabled) return;

  const imageSetId = document.getElementById('vid-image-select').value;
  if (!imageSetId) {
    alert('請選擇已生成的分鏡圖組');
    return;
  }

  _setBusy(btn, true);

  const progressEl = document.getElementById('vid-gen-progress');
  if (progressEl) progressEl.style.display = '';
  _updateVideoProgress(0, 0, '準備中...');

  try {
    const resp = await fetch('/api/trigger/generate-videos', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        image_set_id: imageSetId,
        duration_sec: _selectedVideoDuration,
        mode: _selectedVideoMode,
      }),
    });
    const data = await resp.json();
    if (data.error) {
      alert('Error: ' + data.error);
      if (progressEl) progressEl.style.display = 'none';
      return;
    }
    _pollVideoTask(data.task_id);
  } catch (e) {
    alert('Failed: ' + e.message);
    if (progressEl) progressEl.style.display = 'none';
  } finally {
    _setBusy(btn, false);
  }
}

function _pollVideoTask(taskId) {
  const poll = async () => {
    try {
      const resp = await fetch('/api/task/' + taskId);
      const task = await resp.json();

      if (task.progress) {
        _updateVideoProgress(task.progress.current, task.progress.total, task.progress.step);
      }

      if (task.status === 'done') {
        _updateVideoProgress(task.progress.total, task.progress.total, '完成！');
        if (task.result && task.result.video_set_id) {
          showVideoSetInPanel(task.result.video_set_id);
        }
        refreshAll();
        setTimeout(() => {
          const progressEl = document.getElementById('vid-gen-progress');
          if (progressEl) progressEl.style.display = 'none';
        }, 3000);
        return;
      }
      if (task.status === 'error') {
        _updateVideoProgress(0, 0, '視頻生成失敗: ' + (task.error || '未知錯誤'));
        alert('視頻生成失敗: ' + (task.error || '未知錯誤'));
        refreshAll();
        return;
      }
      setTimeout(poll, 5000);
    } catch (e) {
      setTimeout(poll, 7000);
    }
  };
  setTimeout(poll, 3000);
}

function _updateVideoProgress(current, total, message) {
  const bar = document.getElementById('vid-gen-progress-bar');
  const text = document.getElementById('vid-gen-progress-text');
  if (bar) {
    const pct = total > 0 ? Math.round(current / total * 100) : 0;
    bar.style.width = pct + '%';
  }
  if (text) {
    text.textContent = total > 0 ? `生成中 ${current}/${total} 段 — ${message}` : message;
  }
}

function renderVideoHistory(videoSets) {
  const el = document.getElementById('video-history-sidebar');
  if (!el) return;
  if (!videoSets || !videoSets.length) {
    el.innerHTML = '<div class="preview-empty" style="padding:12px 0;font-size:12px">尚無視頻紀錄</div>';
    return;
  }
  el.innerHTML = videoSets.map(s => {
    const id = s.id || s.video_set_id;
    return `
      <div class="history-item" onclick="showVideoSetInPanel('${esc(id)}')">
        <div class="hi-top">
          <div class="hi-main">
            <div class="hi-title">${esc(id)}</div>
            <div class="hi-meta">${s.success_count || 0}/${s.total_clips || 0} 段 · ${s.duration_sec || 5}s/${s.mode || 'std'}</div>
          </div>
        </div>
      </div>`;
  }).join('');
}

async function showVideoSetInPanel(setId) {
  const el = document.getElementById('video-results');
  el.innerHTML = '<div class="preview-empty">載入中...</div>';
  document.getElementById('video-results-meta').textContent = '';

  try {
    const resp = await fetch('/api/video-sets/' + encodeURIComponent(setId));
    const json = await resp.json();
    const meta = json.data || {};
    const clips = meta.clips || [];
    if (!clips.length) {
      el.innerHTML = '<div class="empty-state"><div class="empty-icon">&#127909;</div><p>無視頻資料</p></div>';
      return;
    }

    const successCount = clips.filter(c => c.status === 'ok').length;
    document.getElementById('video-results-meta').textContent = `${successCount}/${clips.length} 段視頻`;

    el.innerHTML = `<div class="frame-card-grid">
      ${clips.map((c, i) => {
        const num = c.frame_number || (i + 1);
        if (c.status === 'ok' && c.video_path) {
          const vidUrl = '/api/videos/' + encodeURIComponent(setId) + '/clip_' + String(num).padStart(3, '0') + '.mp4';
          return `
            <div class="frame-card">
              <div class="frame-card-img" style="background:#111;display:flex;align-items:center;justify-content:center">
                <video controls style="width:100%;height:100%;object-fit:cover" preload="none">
                  <source src="${vidUrl}" type="video/mp4">
                </video>
                <span class="scene-num">#${num}</span>
              </div>
              <div class="frame-card-body">
                ${c.video_prompt ? '<div class="frame-card-prompt">' + esc(c.video_prompt) + '</div>' : ''}
                <a href="${vidUrl}" download class="btn btn-sm" style="margin-top:6px;display:inline-block">下載 MP4</a>
              </div>
            </div>`;
        } else {
          return `
            <div class="frame-card frame-card-error">
              <div class="frame-card-img frame-card-img-error">
                <span class="scene-num">#${num}</span>
                <span style="color:var(--red);font-size:12px">${esc(c.error || '生成失敗')}</span>
              </div>
              <div class="frame-card-body">
                ${c.video_prompt ? '<div class="frame-card-prompt">' + esc(c.video_prompt) + '</div>' : ''}
              </div>
            </div>`;
        }
      }).join('')}
    </div>`;
  } catch (e) {
    el.innerHTML = '<div class="empty-state"><div class="empty-icon">&#128683;</div><p>載入失敗</p></div>';
  }
}

// ══════════════════════════════════════════
// Knowledge Base
// ══════════════════════════════════════════

const KB_CAT_LABELS = {
  buildings: '建築類型',
  routes: '路線/動線',
  zones: '探索區域',
  encounters: '遭遇事件',
  found_items: '發現物品',
  traps: '陷阱/危機',
  clues: '線索/敘事碎片',
  atmosphere: '氛圍觸發器',
  endings: '結局類型',
  tension_curves: '張力/緊張感曲線',
  series_hooks: '系列連結',
};

async function refreshKB() {
  try {
    const statsResp = await fetch('/api/knowledge/stats');
    const stats = await statsResp.json();
    renderKBStats(stats);
    document.getElementById('badge-kb').textContent = stats.total || 0;
    loadKBCategory(currentKBCategory);
  } catch (e) {
    console.error('KB refresh failed:', e);
  }
}

function renderKBStats(stats) {
  const el = document.getElementById('kb-stats');
  const cats = stats.categories || {};
  let cardsHtml = `
    <div class="kb-stat-card">
      <div class="kb-stat-num">${stats.total || 0}</div>
      <div class="kb-stat-label">總條目</div>
    </div>`;

  for (const [key, label] of Object.entries(KB_CAT_LABELS)) {
    const count = (cats[key] || {}).count || 0;
    cardsHtml += `
      <div class="kb-stat-card">
        <div class="kb-stat-num">${count}</div>
        <div class="kb-stat-label">${label}</div>
      </div>`;
  }

  cardsHtml += `
    <div class="kb-stat-card">
      <div class="kb-stat-num">${stats.videos || stats.dramas || 0}</div>
      <div class="kb-stat-label">已分析影片</div>
    </div>`;

  el.innerHTML = cardsHtml;
}

function switchKBCategory(cat) {
  currentKBCategory = cat;
  document.querySelectorAll('.kb-cat-btn').forEach(b => b.classList.remove('active'));
  const btn = document.querySelector(`.kb-cat-btn[data-cat="${cat}"]`);
  if (btn) btn.classList.add('active');
  loadKBCategory(cat);
}

async function loadKBCategory(category) {
  const el = document.getElementById('kb-entries');
  el.innerHTML = '<div class="preview-empty">載入中...</div>';
  try {
    const resp = await fetch('/api/knowledge/' + category);
    const data = (await resp.json()).data || [];
    if (!data.length) {
      el.innerHTML = '<div class="preview-empty">此分類尚無條目。請先分析探索影片入庫。</div>';
      return;
    }
    el.innerHTML = data.map(e => renderKBCard(e)).join('');
  } catch (e) {
    el.innerHTML = '<div class="preview-empty">載入失敗</div>';
  }
}

function isSeedData(entry) {
  const exs = entry.examples || [];
  return exs.length > 0 && exs.every(e => e.drama_title === '種子數據');
}

function renderKBCard(entry) {
  const examples = (entry.examples || []).slice(0, 2);
  const tags = (entry.tags || []).filter(Boolean);
  const seed = isSeedData(entry);
  return `
    <div class="kb-card${seed ? ' kb-card-seed' : ''}" onclick="showKBDetail('${esc(entry.category)}','${esc(entry.id)}')">
      <div class="kb-card-header">
        <div class="kb-card-name">${esc(entry.name)}${seed ? ' <span class="seed-badge">種子</span>' : ''}</div>
        ${entry.subcategory ? '<span class="tag tag-outline tag-sm">' + esc(entry.subcategory) + '</span>' : ''}
        <div class="kb-card-score">
          <span class="score-badge">${entry.effectiveness_score || 0}</span>
        </div>
      </div>
      ${entry.name_en ? '<div class="kb-card-name-en">' + esc(entry.name_en) + '</div>' : ''}
      <div class="kb-card-desc">${esc((entry.description || '').substring(0, 120))}${(entry.description || '').length > 120 ? '...' : ''}</div>
      ${tags.length ? '<div class="kb-card-tags">' + tags.slice(0, 4).map(t => '<span class="tag tag-sm">' + esc(t) + '</span>').join('') + '</div>' : ''}
      ${examples.length ? '<div class="kb-card-example"><strong>範例:</strong> ' + esc((examples[0].excerpt || '').substring(0, 80)) + '...</div>' : ''}
    </div>`;
}

async function showKBDetail(category, entryId) {
  openDetail('知識庫條目');
  const el = document.getElementById('detail-content');
  el.innerHTML = '<div class="preview-empty">載入中...</div>';
  try {
    const resp = await fetch('/api/knowledge/' + category + '/' + encodeURIComponent(entryId));
    if (!resp.ok) {
      el.innerHTML = '<div class="preview-empty">找不到條目</div>';
      return;
    }
    const entry = (await resp.json()).data;
    if (!entry) {
      el.innerHTML = '<div class="preview-empty">找不到條目</div>';
      return;
    }
    let html = `
      <div style="margin-bottom:16px">
        <h3 style="margin:0 0 4px">${esc(entry.name)}
          <span style="color:var(--text-muted);font-size:0.85rem">${esc(entry.name_en || '')}</span>
        </h3>
        <div style="display:flex;gap:6px;align-items:center;margin-bottom:8px">
          <span class="tag">${esc(entry.category)}</span>
          ${entry.subcategory ? '<span class="tag tag-outline">' + esc(entry.subcategory) + '</span>' : ''}
          <span class="score-badge" style="margin-left:auto">效果分: ${entry.effectiveness_score || 0}</span>
        </div>
        <p style="color:var(--text-primary);font-size:0.9rem;line-height:1.7">${esc(entry.description)}</p>
      </div>`;
    if ((entry.tags || []).length) {
      html += '<div style="margin-bottom:12px">' + entry.tags.map(t => '<span class="tag tag-sm" style="margin-right:4px">' + esc(t) + '</span>').join('') + '</div>';
    }
    if ((entry.examples || []).length) {
      html += '<h4 style="color:var(--accent-light);margin-bottom:8px">範例片段</h4>';
      for (const ex of entry.examples) {
        html += `<div class="analysis-section" style="margin-bottom:8px">
          <div style="font-weight:600;margin-bottom:4px">${esc(ex.video_title || ex.drama_title || '未知影片')}</div>
          <div style="font-size:0.85rem;border-left:3px solid var(--accent);padding-left:12px;margin-top:4px">${esc(ex.excerpt || '')}</div>
          ${ex.context ? '<div style="font-size:0.8rem;color:var(--text-muted);margin-top:4px">' + esc(ex.context) + '</div>' : ''}
        </div>`;
      }
    }
    html += `<div style="font-size:0.75rem;color:var(--text-muted);margin-top:16px">
      建立: ${esc(entry.created_at || '')} · 更新: ${esc(entry.updated_at || '')} · ID: ${esc(entry.id)}
    </div>`;
    el.innerHTML = html;
  } catch (e) {
    el.innerHTML = '<div class="preview-empty">載入失敗</div>';
  }
}

async function doKBSearch() {
  const q = document.getElementById('kb-search-input').value.trim();
  if (!q) return;
  const el = document.getElementById('kb-search-results');
  el.innerHTML = '<div class="preview-empty">搜尋中...</div>';
  try {
    const resp = await fetch('/api/knowledge/search?q=' + encodeURIComponent(q));
    const data = (await resp.json()).data || [];
    if (!data.length) {
      el.innerHTML = '<div class="preview-empty">無結果</div>';
      return;
    }
    el.innerHTML = '<div class="kb-entries-grid" style="margin-bottom:24px">' + data.map(e => renderKBCard(e)).join('') + '</div>';
  } catch (e) {
    el.innerHTML = '<div class="preview-empty">搜尋失敗</div>';
  }
}

// ══════════════════════════════════════════
// Tasks / Log Panel
// ══════════════════════════════════════════

function renderTasks(tasks) {
  const el = document.getElementById('tasks');
  const dot = document.getElementById('log-dot');
  if (!tasks || !tasks.length) {
    el.innerHTML = '<div class="preview-empty" style="padding:8px 0;font-size:0.78rem;color:var(--text-muted)">尚無任務紀錄</div>';
    if (dot) dot.classList.remove('active');
    return;
  }
  const hasRunning = tasks.some(t => t.status === 'running');
  if (dot) dot.classList.toggle('active', hasRunning);
  const sorted = [...tasks].reverse();
  el.innerHTML = sorted.map(t => {
    const p = t.progress || {};
    const hasProgress = t.status === 'running' && p.total > 0;
    const progressHtml = hasProgress ? `
      <div class="progress-container">
        <div class="progress-bar" style="width:${p.percent}%"></div>
        <span class="progress-text">${p.percent}% — ${esc(p.step || '')}</span>
      </div>` : '';
    const kwHtml = t.keyword ? `<span class="tag" style="margin-left:6px">${esc(t.keyword)}</span>` : '';
    const vidHtml = t.video_id ? `<span class="tag tag-outline" style="margin-left:6px">${esc(t.video_id)}</span>` : '';
    return `
    <div class="task-item">
      <div class="task-header">
        <span class="task-stage">
          <span class="badge-status ${t.status}" style="position:static;margin-right:8px">${t.status}</span>
          ${STAGE_LABELS[t.stage] || t.stage} ${kwHtml}${vidHtml}
        </span>
        <span class="task-time">${t.started_at}${t.finished_at ? ' → ' + t.finished_at : ''}</span>
      </div>
      ${progressHtml}
      <div class="task-logs">${[...(t.logs || [])].reverse().map(l => '<div>' + esc(l) + '</div>').join('')}</div>
      ${t.error ? '<div class="task-error">Error: ' + esc(t.error) + '</div>' : ''}
      ${t.result ? '<div class="task-result"><pre>' + esc(JSON.stringify(t.result, null, 2)) + '</pre></div>' : ''}
    </div>`;
  }).join('');
}

function toggleLogPanel() {
  _logExpanded = !_logExpanded;
  const body = document.getElementById('log-body');
  const toggle = document.getElementById('log-toggle');
  const panel = document.getElementById('log-panel');
  if (_logExpanded) {
    body.style.display = 'block';
    toggle.innerHTML = '&#9660; 收合';
    panel.classList.add('expanded');
    body.scrollTop = 0;
  } else {
    body.style.display = 'none';
    toggle.innerHTML = '&#9650; 展開';
    panel.classList.remove('expanded');
  }
}

// ══════════════════════════════════════════
// Traceability
// ══════════════════════════════════════════

async function showTrace(itemType, itemId) {
  const overlay = document.getElementById('trace-overlay');
  const content = document.getElementById('trace-content');
  overlay.style.display = 'flex';
  content.innerHTML = '<div class="preview-empty">載入中...</div>';

  try {
    const resp = await fetch(`/api/trace/${itemType}/${itemId}`);
    const chain = await resp.json();

    let html = '<div class="trace-chain">';
    const _kbLabels = {buildings:'建築', routes:'路線', zones:'區域', encounters:'遭遇', found_items:'發現物品', traps:'陷阱/危機', clues:'線索', atmosphere:'氛圍', endings:'結局', tension_curves:'張力曲線', series_hooks:'系列連結'};
    const upstream = (chain.upstream || []).slice().reverse();
    let kbDetailHtml = '';
    for (const u of upstream) {
      if (!u.id) continue;
      let nodeLabel = esc(u.type);
      if (u.type === 'knowledge_base') {
        nodeLabel = '知識庫生成';
        // Build KB combination detail
        const combo = u.kb_combination || {};
        const userSel = u.kb_user_selected || [];
        let lines = [];
        for (const [cat, ids] of Object.entries(combo)) {
          if (!ids || !ids.length) continue;
          const catLabel = _kbLabels[cat] || cat;
          const src = userSel.includes(cat) ? '👤 用戶指定' : '🎲 隨機';
          lines.push(`<span style="color:var(--accent-light)">${esc(catLabel)}</span> ${src}: <code style="font-size:0.7rem">${ids.map(i=>esc(i)).join(', ')}</code>`);
        }
        if (lines.length) {
          kbDetailHtml = `<div style="margin-top:12px;padding:10px;background:rgba(0,184,148,0.1);border-radius:6px;font-size:0.85rem"><strong>知識庫元素組合:</strong><br>${lines.join('<br>')}</div>`;
        }
      }
      if (u.type === 'analyses' && u.id === 'knowledge_base') nodeLabel = '知識庫生成';
      html += `<div class="trace-node" onclick="onTraceNodeClick('${esc(u.type)}','${esc(u.id)}')">${nodeLabel}<br><span style="font-size:0.7rem">${u.type === 'knowledge_base' ? '知識庫' : esc(u.id)}</span></div>`;
      html += '<span class="trace-arrow">&rarr;</span>';
    }
    html += `<div class="trace-node current">${esc(itemType)}<br><span style="font-size:0.7rem">${esc(itemId)}</span></div>`;
    for (const d of (chain.downstream || [])) {
      if (!d.id) continue;
      html += '<span class="trace-arrow">&rarr;</span>';
      html += `<div class="trace-node" onclick="onTraceNodeClick('${esc(d.type)}','${esc(d.id)}')">${esc(d.type)}<br><span style="font-size:0.7rem">${esc(d.id)}</span></div>`;
    }
    html += '</div>';
    if (kbDetailHtml) html += kbDetailHtml;
    content.innerHTML = html;
  } catch (e) {
    content.innerHTML = '<div class="preview-empty">追溯失敗</div>';
  }
}

function onTraceNodeClick(type, id) {
  if (type === 'knowledge_base') return; // KB trace detail is shown inline
  const detailFns = {
    crawls: showCrawlDetail,
    analyses: showAnalysisDetail,
    scripts: showScriptDetail,
    storyboards: showStoryboardDetail,
  };
  if (detailFns[type]) detailFns[type](id);
}

function closeTrace() {
  document.getElementById('trace-overlay').style.display = 'none';
}

// ══════════════════════════════════════════
// Detail Panel (Overlay)
// ══════════════════════════════════════════

function openDetail(title) {
  document.getElementById('detail-overlay').style.display = 'flex';
  document.getElementById('detail-title').textContent = title;
}

function closeDetail() {
  document.getElementById('detail-overlay').style.display = 'none';
}

// ══════════════════════════════════════════
// Util
// ══════════════════════════════════════════

function esc(str) {
  if (!str) return '';
  return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}
