(function () {
  const BACKEND_NODES = [
    'PREP-INGEST',
    'HB-PT-000', 'HB-PT-001', 'HB-PT-002', 'HB-PT-003', 'HB-PT-004', 'HB-PT-005',
    'HB-PT-006', 'HB-PT-007', 'HB-PT-008', 'HB-PT-009', 'HB-PT-010', 'HB-PT-011',
  ];
  const SPECIALTY_NODES = [
    'HB-PT-002', 'HB-PT-003', 'HB-PT-004', 'HB-PT-005',
    'HB-PT-006', 'HB-PT-007', 'HB-PT-008', 'HB-PT-009',
  ];
  const STEP_NODE_MAP = {
    1: 'PREP-INGEST',
    2: 'HB-PT-000',
    3: 'HB-PT-001',
    4: 'HB-PT-002',
    5: 'HB-PT-003',
    6: 'HB-PT-004',
    7: 'HB-PT-005',
    8: 'HB-PT-006',
    9: 'HB-PT-007',
    10: 'HB-PT-008',
    11: 'HB-PT-009',
    12: 'HB-PT-010',
    13: 'HB-PT-011',
  };
  const PREVIOUS_NODE_MAP = {
    'HB-PT-001': 'HB-PT-000',
    'HB-PT-002': 'HB-PT-001',
    'HB-PT-003': 'HB-PT-002',
    'HB-PT-004': 'HB-PT-003',
    'HB-PT-005': 'HB-PT-004',
    'HB-PT-006': 'HB-PT-005',
    'HB-PT-007': 'HB-PT-006',
    'HB-PT-008': 'HB-PT-007',
    'HB-PT-009': 'HB-PT-008',
    'HB-PT-010': 'HB-PT-009',
    'HB-PT-011': 'HB-PT-010',
  };
  const NODE_STEP_MAP = {
    'PREP-INGEST': 1,
    'HB-PT-000': 2,
    'HB-PT-001': 3,
    'HB-PT-002': 4,
    'HB-PT-003': 5,
    'HB-PT-004': 6,
    'HB-PT-005': 7,
    'HB-PT-006': 8,
    'HB-PT-007': 9,
    'HB-PT-008': 10,
    'HB-PT-009': 11,
    'HB-PT-010': 12,
    'HB-PT-011': 13,
  };
  const BACKEND_NODE_LABELS = {
    'PREP-INGEST': '项目资料读取与项目档案构建',
    'HB-PT-000': '项目资料完整性审查与模块选择',
    'HB-PT-001': '项目概况提取',
    'HB-PT-002': '行业类别、环评类别及审批路径判定',
    'HB-PT-003': '产业政策符合性分析',
    'HB-PT-004': '规划及规划环评符合性分析',
    'HB-PT-005': '生态环境分区管控符合性分析',
    'HB-PT-006': '长江保护及岸线管控符合性分析',
    'HB-PT-007': '两高项目或化工项目管理要求符合性分析',
    'HB-PT-008': '行业环评审批原则符合性分析',
    'HB-PT-009': '同类项目污染节点与治理措施借鉴分析',
    'HB-PT-010': '综合研判报告生成',
    'HB-PT-011': '交叉一致性核查与人工复核清单生成',
    'FILE-VALIDATION': '上传资料有效性与可用性验证',
    'WEB-SEARCH': '联网检索与候选依据发现',
  };

  function ensureBackendState() {
    state.backendBase = localStorage.getItem('hb_backend_base') || window.location.origin;
    state.taskId = localStorage.getItem('hb_task_id') || state.taskId || '';
    state.taskStatus = localStorage.getItem('hb_task_status') || state.taskStatus || '';
    state.nextNode = localStorage.getItem('hb_next_node') || state.nextNode || '';
    state.projectUploadFiles = state.projectUploadFiles || [];
    state.nodeStatuses = state.nodeStatuses || {};
    state.nodeEvidenceRefs = state.nodeEvidenceRefs || {};
    state.evidenceRefs = state.evidenceRefs || [];
    state.liveOutput = state.liveOutput || {};
    state.eventLog = state.eventLog || [];
    state.currentNode = localStorage.getItem('hb_current_node') || state.currentNode || '';
    state.activeHermesRunId = localStorage.getItem('hb_active_hermes_run_id') || state.activeHermesRunId || '';
    state.runStatusMessage = localStorage.getItem('hb_run_status_message') || state.runStatusMessage || '';
    state.promptDrafts = JSON.parse(localStorage.getItem('hb_prompt_drafts') || '{}');
    state.autoSearch = true;
    state.searchApiUrl = state.searchApiUrl || 'backend-agent';
  }

  ensureBackendState();
  const originalSaveState = saveState;
  saveState = function () {
    originalSaveState();
    localStorage.setItem('hb_backend_base', state.backendBase || window.location.origin);
    localStorage.setItem('hb_task_id', state.taskId || '');
    localStorage.setItem('hb_task_status', state.taskStatus || '');
    localStorage.setItem('hb_next_node', state.nextNode || '');
    localStorage.setItem('hb_current_node', state.currentNode || '');
    localStorage.setItem('hb_active_hermes_run_id', state.activeHermesRunId || '');
    localStorage.setItem('hb_run_status_message', state.runStatusMessage || '');
    localStorage.setItem('hb_prompt_drafts', JSON.stringify(state.promptDrafts || {}));
  };

  function backendUrl(path) {
    return `${(state.backendBase || window.location.origin).replace(/\/+$/, '')}${path}`;
  }

  async function apiFetch(path, options = {}) {
    const response = await fetch(backendUrl(path), options);
    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new Error(err.detail || err.error?.message || `后端请求失败 (${response.status})`);
    }
    return response.json();
  }

  function currentModuleCode() {
    if (state.currentStep === 1) return 'PREP-INGEST';
    return STEP_NODE_MAP[state.currentStep] || '';
  }

  function nodeLabel(code) {
    if (!code) return '';
    if (typeof MODULE_LABELS !== 'undefined' && MODULE_LABELS[code]) return MODULE_LABELS[code];
    return BACKEND_NODE_LABELS[code] || code;
  }

  function activeRunNode() {
    if (state.currentNode) return state.currentNode;
    const running = Object.entries(state.nodeStatuses || {}).find(([, status]) => status === 'running');
    if (running) return running[0];
    if (state.taskStatus === 'running') return state.nextNode || '';
    return '';
  }

  function moduleInputPrefill(code) {
    if (code === 'HB-PT-001') {
      return state.results['HB-PT-000'] || state.results['PREP-INGEST'] || state.projectInfo || '';
    }
    if (code === 'HB-PT-000' || code === 'HB-PT-010' || code === 'HB-PT-011') return '';
    const previousNode = PREVIOUS_NODE_MAP[code] || '';
    return state.results['HB-PT-001'] || state.results[previousNode] || state.results['PREP-INGEST'] || state.projectInfo || '';
  }

  function prefillModuleInput(code) {
    const input = document.getElementById('moduleInput');
    if (!input) return;
    const text = moduleInputPrefill(code);
    if (!text) return;
    input.value = text;
    input.dataset.backendPrefillFor = code;
  }

  function injectWordPreviewStyles() {
    if (document.getElementById('adapterWordPreviewStyles')) return;
    const style = document.createElement('style');
    style.id = 'adapterWordPreviewStyles';
    style.textContent = `
      .result-box.document-box { background:#eef1f4; border-color:#d7dde5; padding:18px; white-space:normal; max-height:680px; }
      .result-box.document-box.loading { color:inherit; font-style:normal; }
      .word-page { max-width:840px; margin:0 auto; min-height:420px; background:#fff; border:1px solid #e1e5ea; box-shadow:0 2px 12px rgba(31,41,55,0.10); padding:44px 56px; color:#1f2933; font-family:"Microsoft YaHei","SimSun",serif; font-size:14px; line-height:1.85; }
      .word-page h1,.word-page h2,.word-page h3,.word-page h4 { color:#1a5276; line-height:1.35; margin:18px 0 10px; font-weight:700; }
      .word-page h1 { font-size:24px; text-align:center; border-bottom:2px solid #1a5276; padding-bottom:12px; margin-top:0; }
      .word-page h2 { font-size:19px; border-bottom:1px solid #d8dee6; padding-bottom:6px; }
      .word-page h3 { font-size:16px; }
      .word-page h4 { font-size:15px; color:#334155; }
      .word-page p { margin:8px 0; }
      .word-page ul,.word-page ol { margin:8px 0 10px 24px; padding-left:14px; }
      .word-page li { margin:4px 0; }
      .word-page table { width:100%; border-collapse:collapse; margin:12px 0 16px; table-layout:auto; }
      .word-page th,.word-page td { border:1px solid #cfd8e3; padding:7px 9px; vertical-align:top; word-break:break-word; }
      .word-page th { background:#edf3f8; color:#12344d; font-weight:700; }
      .word-page blockquote { margin:10px 0; padding:8px 12px; border-left:3px solid #9fb8cc; background:#f5f8fb; color:#52616f; }
      .word-page code { font-family:Consolas,"Courier New",monospace; background:#f3f4f6; border:1px solid #e5e7eb; border-radius:4px; padding:1px 4px; font-size:12px; }
      .word-page pre { white-space:pre-wrap; background:#f8fafc; border:1px solid #e5e7eb; border-radius:6px; padding:10px; overflow-x:auto; }
      .word-page a { color:#1f6fb2; word-break:break-all; }
      .word-status { max-width:840px; margin:0 auto 8px; color:#888; font-size:12px; }
      .prompt-editor { width:100%; min-height:260px; max-height:520px; overflow:auto; resize:vertical; font-family:Consolas,"Microsoft YaHei",monospace; font-size:12px; line-height:1.6; color:#334155; background:#fff; border:1px solid #dce1e6; border-radius:6px; padding:12px; white-space:pre-wrap; }
      .prompt-editor:focus { outline:none; border-color:#2980b9; box-shadow:0 0 0 3px rgba(41,128,185,0.10); }
      .backend-run-status { display:flex; align-items:center; justify-content:space-between; gap:16px; margin:0 0 16px; padding:12px 14px; border:1px solid #b8d7ee; background:#eef7ff; border-radius:8px; color:#12344d; box-shadow:0 1px 4px rgba(31,41,55,0.06); }
      .backend-run-main { display:flex; align-items:center; gap:10px; min-width:0; }
      .backend-run-spinner { width:16px; height:16px; flex:0 0 auto; border:2px solid #b8d7ee; border-top-color:#1f6fb2; border-radius:50%; animation:backendSpin 0.8s linear infinite; }
      .backend-run-title { font-size:14px; font-weight:700; line-height:1.4; }
      .backend-run-detail { font-size:12px; color:#52616f; margin-top:2px; word-break:break-word; }
      .backend-run-status .btn { flex:0 0 auto; }
      .step-item.backend-running { background:#eef7ff; border-left-color:#1f6fb2; }
      .step-item.backend-running .step-status { color:#1f6fb2; font-weight:700; }
      @keyframes backendSpin { to { transform:rotate(360deg); } }
      @media (max-width:768px) { .word-page { padding:24px 20px; font-size:13px; } }
    `;
    document.head.appendChild(style);
  }

  function safeHtml(text) {
    if (typeof escapeHtml === 'function') return escapeHtml(String(text || ''));
    return String(text || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  function renderInlineMarkdown(text) {
    let html = safeHtml(text || '');
    html = html.replace(/`([^`]+)`/g, '<code>$1</code>');
    html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
    html = html.replace(/__([^_]+)__/g, '<strong>$1</strong>');
    html = html.replace(/\[([^\]]+)\]\((https?:\/\/[^)\s]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>');
    html = html.replace(/(https?:\/\/[^\s<]+)/g, '<a href="$1" target="_blank" rel="noopener noreferrer">$1</a>');
    return html;
  }

  function isTableSeparator(line) {
    return /^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?\s*$/.test(line || '');
  }

  function splitTableRow(line) {
    return (line || '').trim().replace(/^\|/, '').replace(/\|$/, '').split('|').map(cell => cell.trim());
  }

  function renderMarkdownBody(markdown) {
    const lines = String(markdown || '').replace(/\r\n/g, '\n').split('\n');
    const html = [];
    let i = 0;
    while (i < lines.length) {
      const line = lines[i];
      const trimmed = line.trim();
      if (!trimmed) { i += 1; continue; }

      if (/^```/.test(trimmed)) {
        const codeLines = [];
        i += 1;
        while (i < lines.length && !/^```/.test(lines[i].trim())) {
          codeLines.push(lines[i]);
          i += 1;
        }
        if (i < lines.length) i += 1;
        html.push(`<pre><code>${safeHtml(codeLines.join('\n'))}</code></pre>`);
        continue;
      }

      if (trimmed.includes('|') && i + 1 < lines.length && isTableSeparator(lines[i + 1])) {
        const headers = splitTableRow(trimmed);
        i += 2;
        const rows = [];
        while (i < lines.length && lines[i].trim().includes('|') && lines[i].trim()) {
          rows.push(splitTableRow(lines[i]));
          i += 1;
        }
        html.push(`<table><thead><tr>${headers.map(cell => `<th>${renderInlineMarkdown(cell)}</th>`).join('')}</tr></thead><tbody>${rows.map(row => `<tr>${headers.map((_, idx) => `<td>${renderInlineMarkdown(row[idx] || '')}</td>`).join('')}</tr>`).join('')}</tbody></table>`);
        continue;
      }

      const heading = trimmed.match(/^(#{1,4})\s+(.+)$/);
      if (heading) {
        const level = heading[1].length;
        html.push(`<h${level}>${renderInlineMarkdown(heading[2])}</h${level}>`);
        i += 1;
        continue;
      }

      if (/^>\s?/.test(trimmed)) {
        const quote = [];
        while (i < lines.length && /^>\s?/.test(lines[i].trim())) {
          quote.push(lines[i].trim().replace(/^>\s?/, ''));
          i += 1;
        }
        html.push(`<blockquote>${quote.map(renderInlineMarkdown).join('<br>')}</blockquote>`);
        continue;
      }

      if (/^[-*]\s+/.test(trimmed)) {
        const items = [];
        while (i < lines.length && /^[-*]\s+/.test(lines[i].trim())) {
          items.push(lines[i].trim().replace(/^[-*]\s+/, ''));
          i += 1;
        }
        html.push(`<ul>${items.map(item => `<li>${renderInlineMarkdown(item)}</li>`).join('')}</ul>`);
        continue;
      }

      if (/^\d+[.)]\s+/.test(trimmed)) {
        const items = [];
        while (i < lines.length && /^\d+[.)]\s+/.test(lines[i].trim())) {
          items.push(lines[i].trim().replace(/^\d+[.)]\s+/, ''));
          i += 1;
        }
        html.push(`<ol>${items.map(item => `<li>${renderInlineMarkdown(item)}</li>`).join('')}</ol>`);
        continue;
      }

      const paragraph = [trimmed];
      i += 1;
      while (i < lines.length && lines[i].trim() && !/^(#{1,4})\s+/.test(lines[i].trim()) && !/^[-*]\s+/.test(lines[i].trim()) && !/^\d+[.)]\s+/.test(lines[i].trim()) && !/^```/.test(lines[i].trim()) && !(lines[i].trim().includes('|') && i + 1 < lines.length && isTableSeparator(lines[i + 1]))) {
        paragraph.push(lines[i].trim());
        i += 1;
      }
      html.push(`<p>${renderInlineMarkdown(paragraph.join(' '))}</p>`);
    }
    return html.join('\n') || '<p style="color:#999;text-align:center;">暂无内容</p>';
  }

  function renderWordPreview(markdown, loading) {
    const status = loading ? '<div class="word-status">正在接收后端输出，内容会持续更新...</div>' : '';
    return `${status}<div class="word-page">${renderMarkdownBody(markdown)}</div>`;
  }

  function resultBox() {
    return document.getElementById('resultBox');
  }

  function setResultText(text, loading) {
    const box = resultBox();
    if (!box) return;
    injectWordPreviewStyles();
    box.className = loading ? 'result-box document-box loading' : 'result-box document-box';
    box.innerHTML = renderWordPreview(text || '', loading);
    box.scrollTop = box.scrollHeight;
  }

  function runningStatusHtml() {
    if (state.taskStatus !== 'running') return '';
    const code = activeRunNode();
    const title = code ? `${code} ${nodeLabel(code)}` : '等待后端节点启动';
    const detail = state.runStatusMessage || (state.activeHermesRunId ? `模型调用中：${state.activeHermesRunId}` : '正在等待后端事件...');
    return `
      <div class="backend-run-status" id="backendRunStatus">
        <div class="backend-run-main">
          <span class="backend-run-spinner" aria-hidden="true"></span>
          <div>
            <div class="backend-run-title">正在分析：${safeHtml(title)}</div>
            <div class="backend-run-detail">${safeHtml(detail)}</div>
          </div>
        </div>
        <button class="btn btn-outline btn-sm" onclick="pauseBackendTask().catch(err => toast(err.message, 'error'))">暂停</button>
      </div>
    `;
  }

  function applyRunningSidebarState() {
    document.querySelectorAll('.step-item.backend-running').forEach(el => el.classList.remove('backend-running'));
    if (state.taskStatus !== 'running') return;
    const code = activeRunNode();
    const step = NODE_STEP_MAP[code];
    if (!step && step !== 0) return;
    const stepEl = document.querySelector(`.step-item[data-step="${step}"]`);
    if (!stepEl) return;
    stepEl.classList.add('backend-running');
    const status = stepEl.querySelector('.step-status');
    if (status) status.textContent = '…';
  }

  function applyRunButtonState() {
    const btn = document.getElementById('btnRun');
    if (!btn) return;
    const runningNode = activeRunNode();
    const currentCode = currentModuleCode();
    const isRunning = state.taskStatus === 'running';
    btn.disabled = isRunning;
    if (isRunning) {
      btn.textContent = runningNode === currentCode ? '分析中...' : `等待 ${runningNode || '后端节点'}...`;
    } else {
      btn.textContent = '运行分析';
    }
  }

  function injectBackendRunStatus() {
    injectWordPreviewStyles();
    const existing = document.getElementById('backendRunStatus');
    if (existing) existing.remove();
    const html = runningStatusHtml();
    if (!html) {
      applyRunButtonState();
      applyRunningSidebarState();
      return;
    }
    const main = document.getElementById('mainContent');
    if (!main) return;
    const firstCard = main.querySelector('.card');
    if (firstCard) firstCard.insertAdjacentHTML('beforebegin', html);
    else main.insertAdjacentHTML('afterbegin', html);
    applyRunButtonState();
    applyRunningSidebarState();
  }

  function makePromptPreviewEditable(code) {
    const preview = document.getElementById('promptPreview');
    if (!preview || preview.tagName === 'TEXTAREA') return;
    const currentPrompt = state.promptDrafts?.[code] || preview.textContent || '';
    preview.outerHTML = `<textarea class="prompt-editor" id="promptPreview" data-node-id="${safeHtml(code)}" oninput="state.promptDrafts=state.promptDrafts||{};state.promptDrafts['${safeHtml(code)}']=this.value;saveState();" spellcheck="false">${safeHtml(currentPrompt)}</textarea>`;
  }

  function currentPromptOverride(code) {
    const editor = document.getElementById('promptPreview');
    const text = editor?.value?.trim() || state.promptDrafts?.[code] || '';
    return text.trim();
  }

  function appendEvent(evt) {
    state.eventLog.push(evt);
    if (state.eventLog.length > 300) state.eventLog = state.eventLog.slice(-300);
  }

  function syncTaskState(task) {
    if (!task) return;
    state.taskId = task.task_id || state.taskId;
    state.taskStatus = task.status || '';
    state.currentNode = task.current_node || '';
    state.activeHermesRunId = task.active_hermes_run_id || '';
    state.nextNode = task.next_node || '';
    state.evidenceRefs = task.evidence_refs || [];
    if (state.taskStatus === 'running' && state.currentNode) {
      state.runStatusMessage = state.runStatusMessage || '后端 Agent 正在运行';
    }
    if (state.taskStatus !== 'running') {
      state.currentNode = '';
      state.activeHermesRunId = '';
      state.runStatusMessage = '';
    }
    const results = task.module_results || {};
    BACKEND_NODES.forEach(code => {
      if (!Object.prototype.hasOwnProperty.call(results, code)) {
        delete state.results[code];
        delete state.nodeStatuses[code];
        delete state.nodeEvidenceRefs[code];
        delete state.liveOutput[code];
      }
    });
    Object.entries(results).forEach(([code, result]) => {
      state.nodeStatuses[code] = result.status || 'completed';
      state.nodeEvidenceRefs[code] = result.evidence_refs || [];
      if (Object.prototype.hasOwnProperty.call(result, 'markdown')) state.results[code] = result.markdown || '';
      if (result.status === 'completed' || result.status === 'failed') delete state.liveOutput[code];
    });
    (task.events || []).forEach(evt => {
      if (!state.eventLog.find(old => old.id === evt.id)) appendEvent(evt);
    });
    saveState();
    injectBackendRunStatus();
  }

  async function refreshTask(rerender) {
    if (!state.taskId) return null;
    const task = await apiFetch(`/api/tasks/${state.taskId}`);
    syncTaskState(task);
    if (rerender) {
      renderStep();
      updateSidebar();
    }
    return task;
  }

  function connectTaskEvents(taskId = state.taskId) {
    if (!taskId || typeof EventSource === 'undefined') return;
    if (state.eventSource) state.eventSource.close();
    const source = new EventSource(backendUrl(`/api/tasks/${taskId}/events`));
    state.eventSource = source;
    source.onmessage = event => {
      const evt = JSON.parse(event.data);
      const nodeId = evt.node_id || '';
      if (evt.type === 'node_output_partial') {
        state.liveOutput[nodeId] = `${state.liveOutput[nodeId] || ''}${evt.message || ''}`;
        state.currentNode = nodeId || state.currentNode;
        state.taskStatus = 'running';
        state.runStatusMessage = '正在接收模型输出';
        if (currentModuleCode() === nodeId || (currentModuleCode() === 'PREP-INGEST' && nodeId === 'PREP-INGEST')) {
          setResultText(state.liveOutput[nodeId], true);
        }
        injectBackendRunStatus();
        saveState();
        return;
      }
      appendEvent(evt);
      if (evt.type === 'node_start') {
        state.nodeStatuses[nodeId] = 'running';
        state.currentNode = nodeId;
        state.taskStatus = 'running';
        state.runStatusMessage = `正在执行 ${nodeLabel(nodeId)}`;
      }
      if (evt.type === 'hermes_call_start' || evt.type === 'hermes_run_started') {
        state.currentNode = nodeId || state.currentNode;
        state.activeHermesRunId = evt.payload?.run_id || evt.payload?.run?.run_id || state.activeHermesRunId || '';
        state.taskStatus = 'running';
        state.runStatusMessage = state.activeHermesRunId ? `模型调用中：${state.activeHermesRunId}` : '模型调用中';
      }
      if (evt.type === 'tool_event') {
        state.currentNode = nodeId || state.currentNode;
        state.taskStatus = 'running';
        state.runStatusMessage = `正在使用工具：${evt.message || 'tool'}`;
      }
      if (evt.type === 'node_workspace_output_used') {
        state.currentNode = nodeId || state.currentNode;
        state.runStatusMessage = '正在整理 Agent 写入的完整结果';
      }
      if (evt.type === 'node_failed') {
        state.nodeStatuses[nodeId] = 'failed';
        state.currentNode = '';
        state.activeHermesRunId = '';
        state.runStatusMessage = '';
      }
      if (evt.type === 'node_complete') {
        state.nodeStatuses[nodeId] = 'completed';
        state.runStatusMessage = `${nodeId} 已完成，正在刷新结果`;
      }
      if (evt.type === 'task_run_started') {
        state.taskStatus = 'running';
        state.currentNode = state.currentNode || state.nextNode || '';
        state.runStatusMessage = '后台连续研判已启动';
      }
      if (evt.type === 'task_paused') {
        state.taskStatus = 'paused';
        state.currentNode = '';
        state.activeHermesRunId = '';
        state.runStatusMessage = '';
      }
      if (evt.type === 'task_completed') {
        state.taskStatus = 'completed';
        state.currentNode = '';
        state.activeHermesRunId = '';
        state.runStatusMessage = '';
      }
      if (['node_complete', 'node_failed', 'task_paused', 'task_completed'].includes(evt.type)) {
        delete state.liveOutput[nodeId];
        refreshTask(true).catch(err => toast(`刷新任务失败：${err.message}`, 'error'));
      }
      updateSidebar();
      injectBackendRunStatus();
      saveState();
    };
    source.onerror = () => {
      source.close();
      if (state.eventSource === source) state.eventSource = null;
    };
  }

  async function createBackendTask() {
    state.projectInfo = document.getElementById('projectInfo')?.value.trim() || state.projectInfo;
    state.knowledgeBase = document.getElementById('knowledgeBase')?.value.trim() || state.knowledgeBase;
    const projectText = [state.projectInfo, state.knowledgeBase ? `【临时补充材料】\n${state.knowledgeBase}` : ''].filter(Boolean).join('\n\n');
    if (!projectText && (!state.projectUploadFiles || state.projectUploadFiles.length === 0)) {
      throw new Error('请先输入项目简介或上传项目资料');
    }
    const form = new FormData();
    form.append('project_text', projectText);
    (state.projectUploadFiles || []).forEach(file => form.append('files', file, file.name));
    const response = await apiFetch('/api/tasks', { method: 'POST', body: form });
    state.taskId = response.task_id;
    state.taskStatus = response.status;
    state.nextNode = response.next_node || '';
    state.results = {};
    state.nodeStatuses = {};
    state.nodeEvidenceRefs = {};
    state.evidenceRefs = [];
    state.liveOutput = {};
    state.eventLog = [];
    saveState();
    connectTaskEvents(state.taskId);
    return response;
  }

  async function ensureTask() {
    if (state.taskId) return state.taskId;
    const task = await createBackendTask();
    return task.task_id;
  }

  callDeepSeek = async function () {
    throw new Error('前端直连模型已禁用，请通过后端 Hermes Agent 执行任务');
  };

  saveApiConfig = function () {
    state.apiBase = document.getElementById('apiBase')?.value.trim() || state.apiBase;
    state.model = document.getElementById('apiModel')?.value.trim() || state.model;
    state.apiKey = document.getElementById('apiKey')?.value.trim() || state.apiKey;
    saveState();
    toast('页面保持原型配置入口；实际模型调用使用后端环境变量和 Hermes 服务', 'info');
  };

  saveSearchApiConfig = function () {
    state.searchApiUrl = 'backend-agent';
    state.searchApiKey = '';
    saveState();
    toast('联网检索使用后端 Agent，不需要前端搜索 API', 'info');
  };

  saveProjectInfo = async function () {
    const btn = window.event?.target || null;
    if (btn) {
      btn.disabled = true;
      btn.textContent = '正在初始化...';
    }
    try {
      await createBackendTask();
      toast('项目信息已保存，后端任务已初始化', 'success');
      renderStep();
      updateSidebar();
    } catch (err) {
      toast(`初始化失败：${err.message}`, 'error');
    } finally {
      if (btn) {
        btn.disabled = false;
        btn.textContent = '保存项目信息';
      }
    }
  };

  handleProjectFiles = async function (fileList) {
    if (!fileList || fileList.length === 0) return;
    state.projectUploadFiles = [...(state.projectUploadFiles || []), ...Array.from(fileList)];
    const progressEl = document.getElementById('projectFileProgress');
    const names = Array.from(fileList).map(file => file.name).join('、');
    if (progressEl) progressEl.textContent = `已选择 ${state.projectUploadFiles.length} 个原始文件：${names}。文件不会在浏览器解析，初始化任务时提交给后端 Agent。`;
    saveState();
    toast('文件已加入待上传队列，保存项目信息后由后端 Agent 读取', 'success');
  };

  runModule = async function (code) {
    if (!BACKEND_NODES.includes(code)) {
      toast(`${code} 未接入后端 Agent`, 'error');
      return;
    }
    const btn = document.getElementById('btnRun');
    state.taskStatus = 'running';
    state.currentNode = state.nextNode === 'PREP-INGEST' && code === 'HB-PT-000' ? 'PREP-INGEST' : code;
    state.runStatusMessage = state.currentNode === 'PREP-INGEST'
      ? '正在先读取项目资料并构建项目档案'
      : `正在启动 ${code} ${nodeLabel(code)}`;
    saveState();
    injectBackendRunStatus();
    updateSidebar();
    if (btn) btn.disabled = true;
    setResultText('正在启动后端 Agent 节点...', true);
    try {
      await ensureTask();
      if (state.nextNode === 'PREP-INGEST' && code === 'HB-PT-000') {
        state.currentNode = 'PREP-INGEST';
        state.runStatusMessage = '正在先读取项目资料并构建项目档案';
        saveState();
        injectBackendRunStatus();
        setResultText('正在先读取项目资料并构建项目档案...', true);
        const prepResponse = await apiFetch(`/api/tasks/${state.taskId}/step`, { method: 'POST' });
        if (prepResponse.result?.markdown) state.results['PREP-INGEST'] = prepResponse.result.markdown;
        if (prepResponse.result?.status) state.nodeStatuses['PREP-INGEST'] = prepResponse.result.status;
        state.taskStatus = prepResponse.status;
        state.nextNode = prepResponse.next_node || '';
        saveState();
        await refreshTask(false);
        if (prepResponse.result?.status && prepResponse.result.status !== 'completed') {
          throw new Error(prepResponse.result.error || prepResponse.result.markdown || '项目资料读取失败');
        }
      }
      if (state.nextNode && state.nextNode !== code) {
        throw new Error(`当前任务下一节点是 ${state.nextNode}，请按流程执行`);
      }
      state.taskStatus = 'running';
      state.currentNode = code;
      state.runStatusMessage = `正在执行 ${code} ${nodeLabel(code)}`;
      saveState();
      injectBackendRunStatus();
      connectTaskEvents(state.taskId);
      const promptOverride = currentPromptOverride(code);
      const response = await apiFetch(`/api/tasks/${state.taskId}/step`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(promptOverride ? { prompt_override: promptOverride } : {}),
      });
      if (response.result?.markdown) state.results[code] = response.result.markdown;
      if (response.result?.status) state.nodeStatuses[code] = response.result.status;
      state.taskStatus = response.status;
      state.nextNode = response.next_node || '';
      saveState();
      await refreshTask(true);
      if (response.result?.status && response.result.status !== 'completed') {
        throw new Error(response.result.error || response.result.markdown || `${code} 执行失败`);
      }
      toast(`${code} 分析完成`, 'success');
    } catch (err) {
      state.currentNode = '';
      state.activeHermesRunId = '';
      state.runStatusMessage = '';
      if (state.taskStatus === 'running') state.taskStatus = 'paused';
      saveState();
      injectBackendRunStatus();
      const box = resultBox();
      if (box) {
        box.className = 'result-box error';
        box.textContent = `错误：${err.message}`;
      }
      toast(`分析失败：${err.message}`, 'error');
    } finally {
      if (btn) {
        applyRunButtonState();
      }
    }
  };

  runAllModules = async function () {
    try {
      await ensureTask();
      await refreshTask(false);
      if (!state.results['HB-PT-001']) {
        throw new Error('请先完成 HB-PT-001 项目概况提取');
      }
      const needsReset = state.nextNode !== 'HB-PT-002'
        || SPECIALTY_NODES.some(code => Object.prototype.hasOwnProperty.call(state.results, code));
      if (needsReset) {
        await apiFetch(`/api/tasks/${state.taskId}/rerun/HB-PT-002`, { method: 'POST' });
        await refreshTask(false);
      }
      state.taskStatus = 'running';
      state.currentNode = 'HB-PT-002';
      state.runStatusMessage = needsReset ? '正在重新运行全部专项研判' : '正在连续运行全部专项研判';
      saveState();
      renderStep();
      updateSidebar();
      injectBackendRunStatus();
      connectTaskEvents(state.taskId);
      const response = await apiFetch(`/api/tasks/${state.taskId}/run-until`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ stop_after_node: 'HB-PT-009' }),
      });
      state.taskStatus = response.status;
      state.nextNode = response.next_node || '';
      saveState();
      toast(needsReset
        ? '已保留项目概况，并从 HB-PT-002 重新运行全部专项研判'
        : '已启动全部专项研判，完成后停在综合报告前', 'success');
      renderStep();
      updateSidebar();
    } catch (err) {
      toast(`专项一键运行失败：${err.message}`, 'error');
    }
  };

  window.pauseBackendTask = async function () {
    if (!state.taskId) {
      toast('还没有后端任务', 'info');
      return;
    }
    const response = await apiFetch(`/api/tasks/${state.taskId}/pause`, { method: 'POST' });
    state.taskStatus = response.status;
    state.currentNode = '';
    state.activeHermesRunId = '';
    state.runStatusMessage = '';
    saveState();
    renderStep();
    updateSidebar();
    toast('已请求暂停任务', 'info');
  };

  window.runFileValidation = async function () {
    try {
      await ensureTask();
      connectTaskEvents(state.taskId);
      const result = await apiFetch(`/api/tasks/${state.taskId}/validate-files`, { method: 'POST' });
      if (result.markdown) state.results['FILE-VALIDATION'] = result.markdown;
      if (result.status) state.nodeStatuses['FILE-VALIDATION'] = result.status;
      state.nodeEvidenceRefs['FILE-VALIDATION'] = result.evidence_refs || [];
      saveState();
      toast('上传资料验证完成', 'success');
      alert(result.markdown || '上传资料验证完成');
    } catch (err) {
      toast(`资料验证失败：${err.message}`, 'error');
    }
  };

  doSearch = async function () {
    const query = document.getElementById('searchQuery')?.value.trim();
    if (!query) {
      toast('请输入搜索关键词', 'error');
      return;
    }
    const btn = document.getElementById('btnSearch');
    if (btn) {
      btn.disabled = true;
      btn.textContent = '搜索中...';
    }
    try {
      const data = await apiFetch('/api/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query, task_id: state.taskId || undefined, purpose: 'manual_search' }),
      });
      const structuredResults = data.result?.structured?.results;
      const evidenceResults = (data.result?.evidence_refs || []).map(ref => ({
        title: ref.title || ref.source_url || '候选依据',
        url: ref.source_url || '',
        snippet: ref.quote || ref.note || ref.title || '',
        content: ref.quote || ref.note || '',
      }));
      state.searchResults = Array.isArray(structuredResults) && structuredResults.length
        ? structuredResults.map(item => ({
          title: item.title || item.policy_name || item.url || '检索结果',
          url: item.url || item.source_url || '',
          snippet: item.summary || item.snippet || item.key_points || '',
          content: item.summary || item.snippet || item.key_points || '',
        }))
        : evidenceResults;
      state.searchContext = data.result?.markdown || state.searchResults.map(r => `【来源】${r.title}\n【链接】${r.url}\n【内容】${r.snippet || r.content || ''}`).join('\n\n---\n\n');
      state.searchApiUrl = 'backend-agent';
      saveState();
      renderSearchPanel(document.getElementById('mainContent'));
      toast(`后端检索完成，发现 ${state.searchResults.length} 条候选结果`, 'success');
    } catch (err) {
      toast(`搜索失败：${err.message}`, 'error');
    } finally {
      if (btn) {
        btn.disabled = false;
        btn.textContent = '搜索';
      }
    }
  };

  autoSearch = async function () {
    return null;
  };

  rerunWithFeedback = async function (code) {
    const feedback = document.getElementById('feedbackInput')?.value.trim();
    if (!feedback) {
      toast('请输入修正意见', 'error');
      return;
    }
    if (!state.taskId) {
      toast('请先初始化任务', 'error');
      return;
    }
    closeModal();
    setResultText('正在根据反馈重新分析...', true);
    try {
      const result = await apiFetch(`/api/tasks/${state.taskId}/feedback/${code}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ feedback, action: 'revise' }),
      });
      if (result.markdown) state.results[code] = result.markdown;
      state.nodeStatuses[code] = result.status || 'completed';
      saveState();
      await refreshTask(true);
      toast('已根据反馈修正，下游节点已清理', 'success');
    } catch (err) {
      toast(`重新分析失败：${err.message}`, 'error');
      setResultText(`错误：${err.message}`, false);
    }
  };

  analyzeErrorReasons = async function (code) {
    const feedback = document.getElementById('feedbackInput')?.value.trim();
    if (!feedback) {
      toast('请先输入修正意见', 'error');
      return;
    }
    if (!state.taskId) {
      toast('请先初始化任务', 'error');
      return;
    }
    closeModal();
    setResultText('正在分析错误原因...', true);
    try {
      const result = await apiFetch(`/api/tasks/${state.taskId}/feedback/${code}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ feedback, action: 'analyze_error' }),
      });
      setResultText(result.markdown || '错误原因分析完成', false);
      toast('错误原因分析完成，正式节点结果未被替换', 'success');
    } catch (err) {
      toast(`分析失败：${err.message}`, 'error');
      setResultText(`错误：${err.message}`, false);
    }
  };

  exportReport = function () {
    if (state.taskId) {
      const a = document.createElement('a');
      a.href = backendUrl(`/api/tasks/${state.taskId}/report.md`);
      a.download = `环评前期研判报告_${state.taskId}.md`;
      a.click();
      toast('正在下载后端报告', 'success');
      return;
    }
    toast('请先初始化任务并生成综合研判报告', 'error');
  };

  resetAll = function () {
    if (!confirm('确定要重置当前前端任务和项目数据吗？参考资料和检索结果不会受影响。')) return;
    state.projectInfo = '';
    state.knowledgeBase = '';
    state.results = {};
    state.currentStep = 0;
    state.searchContext = '';
    state.searchResults = null;
    state.taskId = '';
    state.taskStatus = '';
    state.nextNode = '';
    state.projectUploadFiles = [];
    state.nodeStatuses = {};
    state.nodeEvidenceRefs = {};
    state.evidenceRefs = [];
    state.eventLog = [];
    state.liveOutput = {};
    state.currentNode = '';
    state.activeHermesRunId = '';
    state.runStatusMessage = '';
    if (state.eventSource) state.eventSource.close();
    saveState();
    renderStep();
    updateSidebar();
    toast('已重置当前任务', 'info');
  };

  const originalUpdateSidebar = updateSidebar;
  updateSidebar = function () {
    originalUpdateSidebar();
    applyRunningSidebarState();
    applyRunButtonState();
  };

  const originalRenderStep = renderStep;
  renderStep = function () {
    const result = originalRenderStep.apply(this, arguments);
    setTimeout(() => injectBackendRunStatus(), 0);
    return result;
  };

  const originalRenderProjectInput = renderProjectInput;
  renderProjectInput = function (container) {
    originalRenderProjectInput(container);
    const group = container.querySelector('.btn-group');
    if (group && state.taskId) {
      group.insertAdjacentHTML('afterbegin', '<button class="btn btn-outline" onclick="runFileValidation()">AI验证上传资料</button>');
      if (state.taskStatus === 'running') {
        group.insertAdjacentHTML('beforeend', "<button class=\"btn btn-outline\" onclick=\"pauseBackendTask().catch(err => toast(err.message, 'error'))\">暂停</button>");
      }
    }
    const hint = container.querySelector('.file-drop-zone p:nth-child(2)');
    if (hint) hint.textContent = `支持格式：.docx / .pdf / .txt / .html / 图片（文件提交给后端 Agent 读取；已选择 ${(state.projectUploadFiles || []).length} 个）`;
  };

  const originalRenderModuleStep = renderModuleStep;
  renderModuleStep = function (container, moduleIndex) {
    originalRenderModuleStep(container, moduleIndex);
    const code = `HB-PT-${String(moduleIndex).padStart(3, '0')}`;
    const renderedResult = state.liveOutput[code] || state.results[code] || '';
    if (renderedResult) {
      setResultText(renderedResult, Boolean(state.liveOutput[code]));
    }
    prefillModuleInput(code);
    const group = container.querySelector('.btn-group');
    if (group && state.taskStatus === 'running') {
      group.insertAdjacentHTML('beforeend', "<button class=\"btn btn-outline btn-sm\" onclick=\"pauseBackendTask().catch(err => toast(err.message, 'error'))\">暂停</button>");
    }
    setTimeout(() => makePromptPreviewEditable(code), 0);
    if (code === 'HB-PT-000' && state.results['PREP-INGEST']) {
      const note = container.querySelector('.card > div[style*="margin-bottom:12px"]');
      if (note) note.textContent = '此模块基于后端 PREP-INGEST 生成的项目档案审查资料完整性，并给出建议启动的模块清单。';
    }
  };

  function boot() {
    if (state.currentStep === -4 || state.currentStep === -1) state.currentStep = -3;
    state.searchApiUrl = 'backend-agent';
    saveState();
    if (state.taskId) {
      connectTaskEvents(state.taskId);
      refreshTask(true).catch(err => toast(`恢复任务失败：${err.message}`, 'error'));
    } else {
      renderStep();
      updateSidebar();
    }
  }

  boot();
}());
