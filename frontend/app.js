// ============ KB CATEGORIES ============
const KB_CATEGORIES = ['政策法规', '技术导则', '审批原则', '行业准入', '园区规划', '其他'];
const CATEGORY_COLORS = { '政策法规': '#1565c0', '技术导则': '#7b1fa2', '审批原则': '#2e7d32', '行业准入': '#e65100', '园区规划': '#00695c', '其他': '#616161' };

// ============ STATE ============
const state = {
  apiKey: '',
  apiBase: localStorage.getItem('hb_api_base') || 'https://api.deepseek.com/v1',
  model: localStorage.getItem('hb_model') || 'deepseek-chat',
  backendBase: localStorage.getItem('hb_backend_base') || 'http://127.0.0.1:8501',
  taskId: localStorage.getItem('hb_task_id') || '',
  taskStatus: localStorage.getItem('hb_task_status') || '',
  nextNode: localStorage.getItem('hb_next_node') || '',
  nodeStatuses: JSON.parse(localStorage.getItem('hb_node_statuses') || '{}'),
  nodeEvidenceRefs: JSON.parse(localStorage.getItem('hb_node_evidence_refs') || '{}'),
  evidenceRefs: JSON.parse(localStorage.getItem('hb_evidence_refs') || '[]'),
  eventLog: JSON.parse(localStorage.getItem('hb_event_log') || '[]'),
  liveOutput: {},
  eventSource: null,
  projectUploadFiles: [],
  projectInfo: localStorage.getItem('hb_project_info') || '',
  knowledgeBase: localStorage.getItem('hb_knowledge_base') || '',
  extraFiles: { planning: localStorage.getItem('hb_extra_planning') || '', threeLines: localStorage.getItem('hb_extra_threeLines') || '', industryPrinciple: localStorage.getItem('hb_extra_industryPrinciple') || '', similarReport: localStorage.getItem('hb_extra_similarReport') || '' },
  results: JSON.parse(localStorage.getItem('hb_results') || '{}'),
  currentStep: parseInt(localStorage.getItem('hb_step') || '0'),
  // KB state (deprecated, will be migrated to localFiles)
  kbEntries: JSON.parse(localStorage.getItem('hb_kb_entries') || '[]'),
  selectedKbIds: [],
  // Search state
  searchApiUrl: localStorage.getItem('hb_search_api_url') || '',
  searchApiKey: localStorage.getItem('hb_search_api_key') || '',
  searchResults: JSON.parse(localStorage.getItem('hb_search_results') || 'null'),
  searchContext: localStorage.getItem('hb_search_context') || '', // 用户选中的搜索结果内容，可注入研判
  // KB validity state
  kbValidityResults: JSON.parse(localStorage.getItem('hb_kb_validity') || '{}'),
  // Auto search
  autoSearch: localStorage.getItem('hb_auto_search') !== 'false', // 默认开启
  // Local files
  localFiles: JSON.parse(localStorage.getItem('hb_local_files') || '[]'),
  knowledgeDocuments: JSON.parse(localStorage.getItem('hb_knowledge_documents') || '[]'),
  knowledgeStatusFilter: localStorage.getItem('hb_knowledge_status_filter') || '',
  taskKnowledgeDocIds: JSON.parse(localStorage.getItem('hb_task_knowledge_doc_ids') || '[]'),
  selectedKnowledgeDocIds: JSON.parse(localStorage.getItem('hb_selected_knowledge_doc_ids') || '[]'),
  adminKnowledgeHistory: [],
  adminWorkflowNodes: [],
};

function saveState() {
  localStorage.setItem('hb_api_key', state.apiKey);
  localStorage.setItem('hb_api_base', state.apiBase);
  localStorage.setItem('hb_model', state.model);
  localStorage.setItem('hb_backend_base', state.backendBase);
  localStorage.setItem('hb_task_id', state.taskId || '');
  localStorage.setItem('hb_task_status', state.taskStatus || '');
  localStorage.setItem('hb_next_node', state.nextNode || '');
  localStorage.setItem('hb_node_statuses', JSON.stringify(state.nodeStatuses || {}));
  localStorage.setItem('hb_node_evidence_refs', JSON.stringify(state.nodeEvidenceRefs || {}));
  localStorage.setItem('hb_evidence_refs', JSON.stringify(state.evidenceRefs || []));
  localStorage.setItem('hb_event_log', JSON.stringify((state.eventLog || []).slice(-120)));
  localStorage.setItem('hb_project_info', state.projectInfo);
  localStorage.setItem('hb_knowledge_base', state.knowledgeBase);
  localStorage.setItem('hb_extra_planning', state.extraFiles.planning);
  localStorage.setItem('hb_extra_threeLines', state.extraFiles.threeLines);
  localStorage.setItem('hb_extra_industryPrinciple', state.extraFiles.industryPrinciple);
  localStorage.setItem('hb_extra_similarReport', state.extraFiles.similarReport);
  localStorage.setItem('hb_results', JSON.stringify(state.results));
  localStorage.setItem('hb_step', state.currentStep);
  localStorage.setItem('hb_kb_entries', JSON.stringify(state.kbEntries));
  localStorage.setItem('hb_selected_kb_ids', JSON.stringify(state.selectedKbIds));
  localStorage.setItem('hb_search_api_url', state.searchApiUrl);
  localStorage.setItem('hb_search_api_key', state.searchApiKey);
  localStorage.setItem('hb_search_results', JSON.stringify(state.searchResults));
  localStorage.setItem('hb_search_context', state.searchContext);
  localStorage.setItem('hb_kb_validity', JSON.stringify(state.kbValidityResults));
  localStorage.setItem('hb_auto_search', state.autoSearch);
  localStorage.setItem('hb_local_files', JSON.stringify(state.localFiles));
  localStorage.setItem('hb_knowledge_documents', JSON.stringify(state.knowledgeDocuments || []));
  localStorage.setItem('hb_knowledge_status_filter', state.knowledgeStatusFilter || '');
  localStorage.setItem('hb_task_knowledge_doc_ids', JSON.stringify(state.taskKnowledgeDocIds || []));
  localStorage.setItem('hb_selected_knowledge_doc_ids', JSON.stringify(state.selectedKnowledgeDocIds || []));
  const refCountEl = document.getElementById('refCount');
  if (refCountEl) refCountEl.textContent = state.localFiles.length;
}

// ============ SYSTEM PROMPT ============
const SYSTEM_PROMPT = `你是一位资深的环境影响评价工程师，具有15年以上环评咨询经验，精通建设项目环境影响评价相关法律法规、技术导则和审批流程。你的工作职责包括：

1. 角色定位：你作为"环评研判助手"，辅助环评工程师进行项目前期准入分析，不做最终决策，所有结论需标注"人工复核"提示。

2. 行为准则：
   - 严格基于用户提供的项目资料和知识库内容进行分析判断，不得凭空编造或猜测；
   - 当知识库中缺乏相关信息时，明确说明"知识库中未检索到相关内容，需人工补充查询"；
   - 引用政策法规时，必须注明文件全称、文号（如有）和具体条款；
   - 对不确定的判断，使用"可能""建议核实"等措辞，并标注风险等级；
   - 不得编造废止文件、替代文件或条款号。

3. 输出规范：
   - 采用结构化格式输出，每个研判维度独立成段；
   - 结论前置，先给出判断结论，再列出依据和风险提示；
   - 所有输出内容末尾标注"【以上分析由AI辅助生成，最终结论需经环评工程师人工复核确认】"。`;

// ============ PROMPT TEMPLATES (unchanged from V2) ============
const PROMPTS = {
  'HB-PT-000': (projectInfo) => `请根据以下原始项目信息，审查资料完整性并确定应启动的研判模块：

原始项目信息：
${projectInfo}

请按以下结构输出：

一、资料完整性审查
  □ 项目名称：{已提供/未提供}
  □ 建设地点（省/市/区/街道/园区）：{已提供/未提供}
  □ 所在工业园区名称：{已提供/未提供}
  □ 是否位于合规化工园区：{已提供/未提供/不涉及}
  □ 环境管控单元编码：{已提供/未提供}
  □ 环境管控单元名称：{已提供/未提供}
  □ 产品方案：{已提供/未提供}
  □ 生产工艺：{已提供/未提供}
  □ 原辅材料：{已提供/未提供}
  □ 用地性质：{已提供/未提供}
  □ 是否涉及长江流域或敏感区域：{已提供/未提供/需核实}
  □ 能耗情况：{已提供/未提供，未提供时列为后续补充}
  □ 排污去向：{已提供/未提供，未提供时列为后续补充}

二、模块启动建议
  根据已有资料，建议启动以下模块：
  □ HB-PT-001 项目概况提取 — {建议启动/暂缓，原因}
  □ HB-PT-002 行业类别、环评类别及审批路径判定 — {建议启动/暂缓，原因}
  □ HB-PT-003 产业政策符合性分析 — {建议启动/暂缓，原因}
  □ HB-PT-004 规划及规划环评符合性分析 — {建议启动/暂缓，原因}
  □ HB-PT-005 生态环境分区管控符合性分析 — {建议启动/暂缓，原因}
  □ HB-PT-006 长江保护及岸线管控符合性分析 — {建议启动/暂缓，原因}
  □ HB-PT-007 "两高"项目或化工项目管理要求符合性分析 — {建议启动/暂缓，原因}
  □ HB-PT-008 行业环评审批原则符合性分析 — {建议启动/暂缓，原因}
  □ HB-PT-009 同类项目污染节点与治理措施借鉴分析 — {建议启动/暂缓，原因}

三、优先补充资料清单
  {列出前期研判最急需补充的资料项，按优先级排序}

【以上分析由AI辅助生成，最终结论需经环评工程师人工复核确认】`,
  'HB-PT-001': (projectInfo) => `请根据以下项目材料，提取并整理项目概况信息，按以下结构输出。注意：能耗情况、排污去向如未提供，标注"未提供，需后续补充"，不作为阻断项。

材料内容：
${projectInfo}

输出要求：
一、项目基本信息
  - 项目名称：（全称）
  - 建设单位：（全称）
  - 建设地点：（省/市/区/街道/园区，精确到地块编号）
  - 建设性质：（新建/改建/扩建/技术改造）
  - 项目投资：（总投资额，其中环保投资额及占比）
  - 用地面积及用地性质：（总用地面积，新增用地面积，用地性质）

二、建设内容与规模
  - 主要产品及产能：（产品名称、年产量）
  - 主要生产工艺：（简述工艺流程，标注关键产污环节）
  - 主要原辅材料：（名称、年用量、储存方式）
  - 主要生产设备：（名称、型号、数量）

三、园区与环境管控信息
  - 所在工业园区名称：
  - 是否位于合规化工园区：（是/否/不涉及）
  - 环境管控单元编码：（如有）
  - 环境管控单元名称：（如有）
  - 园区规划环评情况：（是否已完成规划环评、批复文号）
  - 园区基础设施：（污水处理厂、供热设施等）

四、能耗与排放概况（前期如未提供，标注"未提供，需后续补充"）
  - 能源消耗/主要污染物/排污去向/污染治理措施

五、区域敏感信息
六、需补充资料清单

【以上分析由AI辅助生成，最终结论需经环评工程师人工复核确认】`,
  'HB-PT-002': (projectOverview) => `请根据以下项目信息，参照《国民经济行业分类》（GB/T 4754-2017）和《建设项目环境影响评价分类管理名录》（2021年版），完成以下判定：

项目信息：
${projectOverview}

请按以下结构输出分析结果：

一、国民经济行业类别判定
二、环评类别判定（报告书/报告表/登记表）
三、审批路径判定（审批权限/审批层级 + 审批程序）
四、绩效评级行业识别
五、风险提示与建议

【以上分析由AI辅助生成，最终结论需经环评工程师人工复核确认】`,
  'HB-PT-003': (projectOverview) => `请根据以下项目信息，对照《产业结构调整指导目录》（2024年本）及相关产业政策文件，进行产业政策符合性分析。

项目信息：
${projectOverview}

请按以下结构输出分析结果：

一、产业政策符合性总判断（鼓励类/允许类/限制类/淘汰类）
二、《产业结构调整指导目录》对照分析
三、行业准入条件符合性分析
四、市场准入负面清单符合性
五、风险提示与建议

【以上分析由AI辅助生成，最终结论需经环评工程师人工复核确认】`,
  'HB-PT-004': (projectOverview, extra) => `请根据以下项目信息，对照所在区域的规划及规划环评文件，进行规划符合性分析：

项目信息：
${projectOverview}

所在区域规划文件：
${extra || '（如知识库中有相关规划文件，请基于知识库内容分析；如无，请标注需补充）'}

请按以下结构输出分析结果：

一、规划符合性总判断
二、总体规划符合性（用地性质、产业定位、选址）
三、规划环评符合性（准入清单、负面清单、总量控制）
四、基础设施建设条件符合性
五、所引用规划文件有效性识别
六、风险提示与建议

【以上分析由AI辅助生成，最终结论需经环评工程师人工复核确认】`,
  'HB-PT-005': (projectOverview, extra) => `请根据以下项目信息，对照所在区域的生态环境分区管控（"三线一单"）要求，进行符合性分析：

项目信息：
${projectOverview}

所在区域"三线一单"文件：
${extra || '（如知识库中有相关文件，请基于知识库内容分析；如无，请标注需补充）'}

请按以下结构输出：一、总判断+管控单元信息 / 二、生态保护红线 / 三、环境质量底线 / 四、资源利用上线 / 五、准入清单 / 六、风险提示

【以上分析由AI辅助生成，最终结论需经环评工程师人工复核确认】`,
  'HB-PT-006': (projectOverview) => `请根据以下项目信息，对照《中华人民共和国长江保护法》及相关配套法规，进行长江保护及岸线管控符合性分析：

项目信息：
${projectOverview}

请按以下结构输出：一、适用性判断 / 二、岸线管控 / 三、产业布局 / 四、水污染防治 / 五、生态保护 / 六、资源保护 / 七、风险提示

【以上分析由AI辅助生成，最终结论需经环评工程师人工复核确认】`,
  'HB-PT-007': (projectOverview) => `请根据以下项目信息，对照"两高"项目及化工项目管理相关政策文件，进行符合性分析：

项目信息：
${projectOverview}

请按以下结构输出：一、两高项目判定 / 二、化工项目判定 / 三、两高管理要求 / 四、化工管理要求 / 五、风险提示

【以上分析由AI辅助生成，最终结论需经环评工程师人工复核确认】`,
  'HB-PT-008': (projectOverview, extra) => `请根据以下项目信息，对照该行业建设项目环境影响评价文件审批原则，进行行业审批原则符合性分析：

项目信息：
${projectOverview}

行业审批原则文件：
${extra || '（如知识库中有相关审批原则文件，请基于知识库内容分析；如无，请标注需补充）'}

请按以下结构输出：一、总判断 / 二、选址与布局 / 三、工艺与装备 / 四、污染防治 / 五、环境风险 / 六、总量控制 / 七、风险提示

【以上分析由AI辅助生成，最终结论需经环评工程师人工复核确认】`,
  'HB-PT-009': (projectOverview, extra) => `请根据以下同类项目环评报告内容，审查并梳理主要污染排放节点和治理措施，为新建项目提供借鉴：

同类项目环评报告：
${extra || '（如知识库中有同类项目报告，请基于知识库内容分析；如无，请标注需补充）'}

新建项目信息：
${projectOverview}

请按以下结构输出：一、同类项目概况对比 / 二、废气污染节点 / 三、废水污染节点 / 四、固废产生节点 / 五、噪声源 / 六、总结与建议

【以上分析由AI辅助生成，最终结论需经环评工程师人工复核确认】`,
  'HB-PT-010': (allResults) => {
    let parts = [];
    for (let i = 1; i <= 9; i++) { const code = `HB-PT-00${i}`; if (allResults[code]) parts.push(`${code} 结果：\n${allResults[code]}\n`); }
    return `请根据以下各专项模块输出结果，整合生成一份完整的环评前期研判报告，要求结构清晰、结论明确，可直接用于内部技术会审。

${parts.join('\n---\n')}

请按以下结构生成：
═══════════════════════════════════
       环评前期研判报告
═══════════════════════════════════
一、项目概况
二、综合研判结论（总体准入判断 + 各维度研判结论汇总表）
三、关键风险提示
四、政策有效性风险提示
五、综合承接建议
六、需补充资料汇总清单
七、人工复核要点

【以上分析由AI辅助生成，最终结论需经环评工程师人工复核确认】`;
  },
  'HB-PT-011': (allResults) => {
    let parts = [];
    for (let i = 1; i <= 9; i++) { const code = `HB-PT-00${i}`; if (allResults[code]) parts.push(`${code} 结果：\n${allResults[code]}\n`); }
    const report010 = allResults['HB-PT-010'] || '';
    return `请根据以下各专项模块输出结果，进行交叉一致性核查，并生成人工复核清单。

综合研判报告：
${report010}

各专项模块输出：
${parts.join('\n---\n')}

请按以下结构输出：
一、交叉一致性核查（6项核查）
二、矛盾项汇总
三、人工复核清单（至少15项，表格格式）
四、最终质量评估

【以上分析由AI辅助生成，最终结论需经环评工程师人工复核确认】`;
  }
};

const MODULE_LABELS = {
  'PREP-INGEST': '项目资料读取与项目档案构建',
  'HB-PT-000': '资料完整性审查与模块选择', 'HB-PT-001': '项目概况提取',
  'HB-PT-002': '行业类别、环评类别及审批路径判定', 'HB-PT-003': '产业政策符合性分析',
  'HB-PT-004': '规划及规划环评符合性分析', 'HB-PT-005': '生态环境分区管控符合性分析',
  'HB-PT-006': '长江保护及岸线管控符合性分析', 'HB-PT-007': '两高项目或化工项目管理要求符合性分析',
  'HB-PT-008': '行业环评审批原则符合性分析', 'HB-PT-009': '同类项目污染节点与治理措施借鉴分析',
  'HB-PT-010': '综合研判报告生成', 'HB-PT-011': '交叉一致性核查与人工复核清单生成',
};

const MODULE_EXTRAS = { 'HB-PT-004': 'planning', 'HB-PT-005': 'threeLines', 'HB-PT-008': 'industryPrinciple', 'HB-PT-009': 'similarReport' };
const BACKEND_IMPLEMENTED_NODES = [
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

// ============ API CALL ============
async function callDeepSeek(systemPrompt, userPrompt) {
  throw new Error('前端直连模型已禁用，请通过后端 Hermes Agent 执行任务');
}

// ============ BACKEND API ============
function backendUrl(path) {
  return `${(state.backendBase || 'http://127.0.0.1:8501').replace(/\/+$/, '')}${path}`;
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
  if (state.currentStep >= 2 && state.currentStep <= 11) return `HB-PT-${String(state.currentStep - 2).padStart(3, '0')}`;
  if (state.currentStep === 12) return 'HB-PT-010';
  if (state.currentStep === 13) return 'HB-PT-011';
  return '';
}

const autoScrollState = {};

function getAutoScrollState(key) {
  if (!autoScrollState[key]) autoScrollState[key] = { hovering: false, pinned: false };
  return autoScrollState[key];
}

function isNearBottom(el) {
  return !el || (el.scrollHeight - el.scrollTop - el.clientHeight) < 36;
}

function scrollElementToBottom(el) {
  if (!el) return;
  requestAnimationFrame(() => { el.scrollTop = el.scrollHeight; });
}

function bindAutoScrollElement(el, key) {
  if (!el || el.dataset.autoscrollBound === '1') return;
  const status = getAutoScrollState(key);
  el.dataset.autoscrollBound = '1';
  el.addEventListener('mouseenter', () => { status.hovering = true; });
  el.addEventListener('mouseleave', () => {
    status.hovering = false;
    if (!status.pinned) scrollElementToBottom(el);
  });
  el.addEventListener('scroll', () => {
    status.pinned = !isNearBottom(el);
  }, { passive: true });
  if (!status.hovering) {
    status.pinned = false;
    scrollElementToBottom(el);
  }
}

function refreshAutoScrolledContent(id, key, updateFn) {
  const el = document.getElementById(id);
  if (!el) return;
  bindAutoScrollElement(el, key);
  const status = getAutoScrollState(key);
  const follow = !status.hovering && (!status.pinned || isNearBottom(el));
  updateFn(el);
  if (follow) {
    status.pinned = false;
    scrollElementToBottom(el);
  }
}

function bindAutoScrollContainers() {
  document.querySelectorAll('[data-autoscroll-key]').forEach(el => {
    const key = el.dataset.autoscrollKey;
    bindAutoScrollElement(el, key);
    const status = getAutoScrollState(key);
    if (!status.hovering && !status.pinned) scrollElementToBottom(el);
  });
}

function isTableSeparator(line) {
  return /^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?\s*$/.test(line || '');
}

function splitTableRow(line) {
  return (line || '').trim().replace(/^\|/, '').replace(/\|$/, '').split('|').map(cell => cell.trim());
}

function renderInlineMarkdown(text) {
  let html = escapeHtml(text || '');
  html = html.replace(/`([^`]+)`/g, '<code>$1</code>');
  html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
  html = html.replace(/__([^_]+)__/g, '<strong>$1</strong>');
  html = html.replace(/\[([^\]]+)\]\((https?:\/\/[^)\s]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>');
  return html;
}

function renderMarkdownBody(markdown) {
  const lines = String(markdown || '').replace(/\r\n/g, '\n').split('\n');
  const html = [];
  let i = 0;
  while (i < lines.length) {
    const line = lines[i];
    const trimmed = line.trim();
    if (!trimmed) { i++; continue; }

    if (/^```/.test(trimmed)) {
      const codeLines = [];
      i++;
      while (i < lines.length && !/^```/.test(lines[i].trim())) {
        codeLines.push(lines[i]);
        i++;
      }
      if (i < lines.length) i++;
      html.push(`<pre><code>${escapeHtml(codeLines.join('\n'))}</code></pre>`);
      continue;
    }

    const heading = trimmed.match(/^(#{1,6})\s+(.+)$/);
    if (heading) {
      const level = Math.min(heading[1].length, 4);
      html.push(`<h${level}>${renderInlineMarkdown(heading[2])}</h${level}>`);
      i++;
      continue;
    }

    if (/^[-*_]{3,}$/.test(trimmed)) {
      html.push('<hr>');
      i++;
      continue;
    }

    if (trimmed.includes('|') && i + 1 < lines.length && isTableSeparator(lines[i + 1])) {
      const header = splitTableRow(trimmed);
      i += 2;
      const rows = [];
      while (i < lines.length && lines[i].trim().includes('|') && lines[i].trim()) {
        rows.push(splitTableRow(lines[i]));
        i++;
      }
      html.push(`<table><thead><tr>${header.map(cell => `<th>${renderInlineMarkdown(cell)}</th>`).join('')}</tr></thead><tbody>${rows.map(row => `<tr>${row.map(cell => `<td>${renderInlineMarkdown(cell)}</td>`).join('')}</tr>`).join('')}</tbody></table>`);
      continue;
    }

    const unordered = trimmed.match(/^[-*+]\s+(.+)$/);
    if (unordered) {
      const items = [];
      while (i < lines.length) {
        const match = lines[i].trim().match(/^[-*+]\s+(.+)$/);
        if (!match) break;
        items.push(match[1]);
        i++;
      }
      html.push(`<ul>${items.map(item => `<li>${renderInlineMarkdown(item)}</li>`).join('')}</ul>`);
      continue;
    }

    const ordered = trimmed.match(/^\d+[.)]\s+(.+)$/);
    if (ordered) {
      const items = [];
      while (i < lines.length) {
        const match = lines[i].trim().match(/^\d+[.)]\s+(.+)$/);
        if (!match) break;
        items.push(match[1]);
        i++;
      }
      html.push(`<ol>${items.map(item => `<li>${renderInlineMarkdown(item)}</li>`).join('')}</ol>`);
      continue;
    }

    if (trimmed.startsWith('>')) {
      const quotes = [];
      while (i < lines.length && lines[i].trim().startsWith('>')) {
        quotes.push(lines[i].trim().replace(/^>\s?/, ''));
        i++;
      }
      html.push(`<blockquote>${quotes.map(renderInlineMarkdown).join('<br>')}</blockquote>`);
      continue;
    }

    const paragraph = [];
    while (i < lines.length) {
      const current = lines[i];
      const t = current.trim();
      if (!t) break;
      if (/^(#{1,6})\s+/.test(t) || /^```/.test(t) || /^[-*+]\s+/.test(t) || /^\d+[.)]\s+/.test(t) || t.startsWith('>')) break;
      if (t.includes('|') && i + 1 < lines.length && isTableSeparator(lines[i + 1])) break;
      paragraph.push(t);
      i++;
    }
    html.push(`<p>${paragraph.map(renderInlineMarkdown).join('<br>')}</p>`);
  }
  return html.join('');
}

function renderWordDocument(markdown, { loading = false } = {}) {
  const status = loading ? '<div class="word-status">正在接收后端输出...</div>' : '';
  return `${status}<div class="word-page">${renderMarkdownBody(markdown)}</div>`;
}

function renderResultBox(markdown, { id = 'resultBox', loading = false, placeholder = '', placeholderStyle = '', scrollKey = 'resultBox' } = {}) {
  if (!markdown) {
    const style = placeholderStyle ? ` style="${placeholderStyle}"` : '';
    return `<div class="result-box" id="${id}" data-autoscroll-key="${scrollKey}"${style}>${placeholder}</div>`;
  }
  const classes = `result-box document-box${loading ? ' loading' : ''}`;
  return `<div class="${classes}" id="${id}" data-autoscroll-key="${scrollKey}">${renderWordDocument(markdown, { loading })}</div>`;
}

function setResultBoxMarkdown(markdown, { loading = false } = {}) {
  refreshAutoScrolledContent('resultBox', 'resultBox', box => {
    box.className = `result-box document-box${loading ? ' loading' : ''}`;
    box.innerHTML = renderWordDocument(markdown || '正在接收后端输出...', { loading });
  });
}

function slimTaskEvent(evt) {
  if (!evt || evt.type === 'node_output_partial') return;
  return {
    id: evt.id || `${evt.created_at || ''}|${evt.type || ''}|${evt.node_id || ''}|${evt.message || ''}`,
    type: evt.type || 'event',
    node_id: evt.node_id || '',
    message: evt.message || '',
    created_at: evt.created_at || new Date().toISOString(),
  };
}

function appendEventLog(evt) {
  const slim = slimTaskEvent(evt);
  if (!slim) return;
  const existingIds = new Set((state.eventLog || []).map(item => item.id).filter(Boolean));
  if (!existingIds.has(slim.id)) state.eventLog = [...(state.eventLog || []), slim].slice(-120);
  saveState();
  refreshAutoScrolledContent('eventLog', 'eventLog', eventBox => {
    eventBox.innerHTML = renderEventLogHtml();
  });
}

function syncTaskEvents(events) {
  if (!Array.isArray(events)) return;
  const slimEvents = events.map(slimTaskEvent).filter(Boolean);
  const byId = new Map();
  [...(state.eventLog || []), ...slimEvents].forEach(evt => {
    const id = evt.id || `${evt.created_at}|${evt.type}|${evt.node_id}|${evt.message}`;
    byId.set(id, { ...evt, id });
  });
  state.eventLog = Array.from(byId.values())
    .sort((a, b) => String(a.created_at || '').localeCompare(String(b.created_at || '')))
    .slice(-120);
  const eventBox = document.getElementById('eventLog');
  if (eventBox) {
    refreshAutoScrolledContent('eventLog', 'eventLog', box => {
      box.innerHTML = renderEventLogHtml();
    });
  }
}

function renderEventLogHtml() {
  const events = (state.eventLog || []).slice(-80);
  if (!events.length) return '<div style="color:#bbb;text-align:center;padding:18px;">暂无后端事件</div>';
  return events.map(evt => {
    const time = evt.created_at ? new Date(evt.created_at).toLocaleTimeString('zh-CN', { hour12: false }) : '';
    const node = evt.node_id ? ` · ${evt.node_id}` : '';
    return `<div style="padding:6px 0;border-bottom:1px solid var(--border);font-size:12px;">
      <span style="color:var(--text-muted);">${escapeHtml(time)}${escapeHtml(node)}</span>
      <span style="font-weight:600;margin-left:8px;">${escapeHtml(evt.type)}</span>
      <span style="margin-left:8px;color:var(--text-secondary);">${escapeHtml(evt.message || '')}</span>
    </div>`;
  }).join('');
}

function renderEvidenceRefsHtml(code) {
  const refs = ((state.nodeEvidenceRefs || {})[code] || []).filter(ref => ref && (ref.source_url || ref.file_name || ref.title));
  if (!refs.length) return '<div style="color:#bbb;text-align:center;padding:18px;">当前节点暂无已记录依据</div>';
  return refs.map(ref => {
    const title = ref.title || ref.file_name || ref.source_url || '未命名依据';
    const url = ref.source_url || '';
    const meta = [ref.source_type, ref.confidence, ref.knowledge_document_id ? `doc:${ref.knowledge_document_id.slice(0, 8)}` : ''].filter(Boolean).join(' · ');
    return `<div style="padding:8px 0;border-bottom:1px solid var(--border);font-size:12px;">
      <div style="font-weight:600;color:var(--text-primary);">${escapeHtml(title)}</div>
      ${url ? `<a href="${escapeHtml(url)}" target="_blank" rel="noopener noreferrer" style="word-break:break-all;color:var(--primary-light);">${escapeHtml(url)}</a>` : ''}
      <div style="color:var(--text-muted);margin-top:3px;">${escapeHtml(meta)}</div>
    </div>`;
  }).join('');
}

function renderReviewHistory(doc) {
  const history = doc?.metadata?.review_history;
  if (!Array.isArray(history) || !history.length) return '<div style="color:#bbb;font-size:12px;">暂无审核记录</div>';
  return history.slice().reverse().map(item => {
    const time = item.reviewed_at ? new Date(item.reviewed_at).toLocaleString() : '';
    const line = [
      item.status ? `状态：${item.status}` : '',
      item.validity ? `有效性：${item.validity}` : '',
      item.reviewer ? `审核人：${item.reviewer}` : '',
    ].filter(Boolean).join(' · ');
    return `<div style="padding:6px 0;border-bottom:1px solid var(--border);font-size:12px;">
      <div style="font-weight:600;">${escapeHtml(line || '审核记录')}</div>
      <div style="color:var(--text-muted);">${escapeHtml(time)}${item.note ? ` · ${escapeHtml(item.note)}` : ''}</div>
    </div>`;
  }).join('');
}

function downloadBackendFile(path, fallbackName = '') {
  const a = document.createElement('a');
  a.href = backendUrl(path);
  if (fallbackName) a.download = fallbackName;
  document.body.appendChild(a);
  a.click();
  a.remove();
}

function downloadNodeOutput(code, ext) {
  if (!state.taskId) { toast('请先初始化任务', 'error'); return; }
  const fileName = `${code}.${ext}`;
  downloadBackendFile(`/api/tasks/${state.taskId}/outputs/${encodeURIComponent(fileName)}`, fileName);
}

function downloadWordResult(code) {
  const text = state.results[code] || '';
  if (!text) { toast('当前节点还没有可导出的结果', 'error'); return; }
  const title = `${code} ${MODULE_LABELS[code] || ''}`.trim();
  const html = `<!DOCTYPE html><html><head><meta charset="UTF-8"><title>${escapeHtml(title)}</title><style>
    body { font-family: "Microsoft YaHei", "SimSun", serif; color: #1f2933; line-height: 1.85; font-size: 14px; }
    h1, h2, h3, h4 { color: #1a5276; line-height: 1.35; }
    h1 { text-align: center; border-bottom: 2px solid #1a5276; padding-bottom: 10px; }
    table { width: 100%; border-collapse: collapse; margin: 12px 0 16px; }
    th, td { border: 1px solid #cfd8e3; padding: 7px 9px; vertical-align: top; }
    th { background: #edf3f8; }
    blockquote { border-left: 3px solid #9fb8cc; background: #f5f8fb; padding: 8px 12px; color: #52616f; }
    code { background: #f3f4f6; padding: 1px 4px; }
  </style></head><body><h1>${escapeHtml(title)}</h1>${renderMarkdownBody(text)}</body></html>`;
  const blob = new Blob([html], { type: 'application/msword;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `${code}_${new Date().toISOString().slice(0, 10)}.doc`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
  toast('已生成 Word 格式文件', 'success');
}

function openTaskManifest() {
  if (!state.taskId) { toast('请先初始化任务', 'error'); return; }
  window.open(backendUrl(`/api/tasks/${state.taskId}/manifest`), '_blank');
}

function toggleKnowledgeDocSelection(docId, checked) {
  const selected = new Set(state.selectedKnowledgeDocIds || []);
  if (checked) selected.add(docId);
  else selected.delete(docId);
  state.selectedKnowledgeDocIds = Array.from(selected);
  saveState();
  renderStep();
}

function selectVisibleKnowledgeDocuments(checked) {
  const visibleIds = (state.knowledgeDocuments || []).map(doc => doc.id);
  const selected = new Set(state.selectedKnowledgeDocIds || []);
  visibleIds.forEach(docId => checked ? selected.add(docId) : selected.delete(docId));
  state.selectedKnowledgeDocIds = Array.from(selected);
  saveState();
  renderStep();
}

async function batchReviewKnowledgeDocuments(status) {
  const docIds = state.selectedKnowledgeDocIds || [];
  if (!docIds.length) { toast('请先勾选依据', 'error'); return; }
  const defaultValidity = status === 'verified' ? 'effective' : (status === 'deprecated' ? 'superseded' : 'unknown');
  const note = status === 'rejected' ? '批量驳回' : (status === 'verified' ? '批量确认正式依据' : '批量审核');
  const response = await apiFetch('/api/knowledge/documents/batch-review', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ doc_ids: docIds, status, validity: defaultValidity, note, reviewer: 'frontend_batch' }),
  });
  state.selectedKnowledgeDocIds = [];
  saveState();
  toast(`已批量更新 ${response.documents?.length || 0} 条依据`, response.errors?.length ? 'info' : 'success');
  await refreshKnowledgeDocuments(state.knowledgeStatusFilter || '');
}

async function batchUpdateTaskKnowledgeDocuments(mode) {
  if (!state.taskId) { toast('请先初始化任务', 'error'); return; }
  const docIds = state.selectedKnowledgeDocIds || [];
  if (!docIds.length) { toast('请先勾选依据', 'error'); return; }
  const response = await apiFetch(`/api/tasks/${state.taskId}/knowledge-documents`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ mode, doc_ids: docIds }),
  });
  state.taskKnowledgeDocIds = response.knowledge_doc_ids || [];
  state.selectedKnowledgeDocIds = [];
  saveState();
  toast(mode === 'remove' ? '已批量移出本任务依据' : '已批量加入本任务依据', 'success');
  await refreshKnowledgeDocuments(state.knowledgeStatusFilter || '');
}

function knowledgeStatusBadge(status, validity) {
  const label = { candidate: '候选', verified_candidate: '待复核', verified: '正式', rejected: '驳回', deprecated: '废止' }[status] || status || '未知';
  const color = status === 'verified' ? '#27ae60' : status === 'rejected' || status === 'deprecated' ? '#e74c3c' : status === 'verified_candidate' ? '#e67e22' : '#1565c0';
  const validityText = validity && validity !== 'unknown' ? ` / ${validity}` : '';
  return `<span class="badge" style="background:${color};color:#fff;">${escapeHtml(label + validityText)}</span>`;
}

function renderKnowledgeDocumentsHtml() {
  const docs = state.knowledgeDocuments || [];
  const selectedIds = new Set(state.selectedKnowledgeDocIds || []);
  const visibleIds = docs.map(doc => doc.id);
  const selectedVisibleCount = visibleIds.filter(id => selectedIds.has(id)).length;
  const counts = docs.reduce((acc, doc) => {
    acc[doc.status || 'unknown'] = (acc[doc.status || 'unknown'] || 0) + 1;
    return acc;
  }, {});
  const filters = [
    ['', '全部'],
    ['candidate', '候选'],
    ['verified_candidate', '待复核'],
    ['verified', '正式'],
    ['rejected', '驳回'],
    ['deprecated', '废止'],
  ];
  const filterButtons = filters.map(([value, label]) => {
    const active = (state.knowledgeStatusFilter || '') === value;
    const count = value ? (counts[value] || 0) : docs.length;
    return `<button class="btn btn-xs ${active ? 'btn-primary' : 'btn-outline'}" onclick="refreshKnowledgeDocuments('${value}').catch(err => toast(err.message, 'error'))">${label} ${count}</button>`;
  }).join(' ');

  const batchBar = docs.length ? `
    <div class="kb-select-bar" style="background:#f8f9fa;border-color:var(--border);justify-content:space-between;flex-wrap:wrap;">
      <label style="display:flex;align-items:center;gap:6px;margin:0;">
        <input type="checkbox" ${docs.length && selectedVisibleCount === docs.length ? 'checked' : ''} onchange="selectVisibleKnowledgeDocuments(this.checked)">
        当前筛选已选 ${selectedVisibleCount} / ${docs.length}
      </label>
      <div class="btn-group">
        <button class="btn btn-xs btn-outline" onclick="batchReviewKnowledgeDocuments('verified').catch(err => toast(err.message, 'error'))">批量确认正式</button>
        <button class="btn btn-xs btn-outline" onclick="batchReviewKnowledgeDocuments('verified_candidate').catch(err => toast(err.message, 'error'))">批量待复核</button>
        <button class="btn btn-xs btn-danger" onclick="batchReviewKnowledgeDocuments('rejected').catch(err => toast(err.message, 'error'))">批量驳回</button>
        ${state.taskId ? `<button class="btn btn-xs btn-outline" onclick="batchUpdateTaskKnowledgeDocuments('add').catch(err => toast(err.message, 'error'))">批量用于本任务</button>` : ''}
        ${state.taskId ? `<button class="btn btn-xs btn-outline" onclick="batchUpdateTaskKnowledgeDocuments('remove').catch(err => toast(err.message, 'error'))">批量移出任务</button>` : ''}
      </div>
    </div>` : '';

  const list = docs.length ? docs.map(doc => {
    const selectedForTask = (state.taskKnowledgeDocIds || []).includes(doc.id) || doc.selected_for_task;
    const checked = selectedIds.has(doc.id);
    const meta = [
      doc.source_domain,
      doc.issuer,
      doc.doc_no,
      doc.file_hash ? doc.file_hash.slice(0, 19) : '',
    ].filter(Boolean).join(' · ');
    const reviewedAt = doc.metadata?.review?.reviewed_at || '';
    return `<div class="kb-item">
      <label style="display:flex;align-items:flex-start;padding-top:4px;">
        <input type="checkbox" ${checked ? 'checked' : ''} onclick="toggleKnowledgeDocSelection('${doc.id}', this.checked)">
      </label>
      <div class="kb-info">
        <div class="kb-name">${escapeHtml(doc.title || doc.source_url || doc.id)} ${knowledgeStatusBadge(doc.status, doc.validity)}</div>
        <div class="kb-meta">${escapeHtml(meta || '暂无元数据')}${reviewedAt ? ` · 审核：${escapeHtml(new Date(reviewedAt).toLocaleString())}` : ''}</div>
        ${doc.source_url ? `<a href="${escapeHtml(doc.source_url)}" target="_blank" rel="noopener noreferrer" style="font-size:12px;color:var(--primary-light);word-break:break-all;">${escapeHtml(doc.source_url)}</a>` : ''}
        ${doc.local_path ? `<div style="font-size:11px;color:#888;margin-top:3px;">快照：${escapeHtml(doc.local_path)}</div>` : ''}
        <details style="margin-top:6px;">
          <summary style="font-size:12px;color:var(--primary-light);cursor:pointer;">审核历史</summary>
          <div style="margin-top:4px;">${renderReviewHistory(doc)}</div>
        </details>
      </div>
      <div class="kb-actions">
        ${doc.status !== 'verified' ? `<button class="btn btn-xs btn-outline" onclick="reviewKnowledgeDocument('${doc.id}', 'verified').catch(err => toast(err.message, 'error'))">确认为正式</button>` : ''}
        ${doc.status === 'verified' && state.taskId && !selectedForTask ? `<button class="btn btn-xs btn-outline" onclick="updateTaskKnowledgeDocument('${doc.id}', 'add').catch(err => toast(err.message, 'error'))">用于本任务</button>` : ''}
        ${doc.status === 'verified' && state.taskId && selectedForTask ? `<button class="btn btn-xs btn-outline" onclick="updateTaskKnowledgeDocument('${doc.id}', 'remove').catch(err => toast(err.message, 'error'))">移出任务</button>` : ''}
        ${doc.status === 'candidate' ? `<button class="btn btn-xs btn-outline" onclick="reviewKnowledgeDocument('${doc.id}', 'verified_candidate').catch(err => toast(err.message, 'error'))">待复核</button>` : ''}
        ${doc.status !== 'rejected' && doc.status !== 'verified' ? `<button class="btn btn-xs btn-danger" onclick="reviewKnowledgeDocument('${doc.id}', 'rejected').catch(err => toast(err.message, 'error'))">驳回</button>` : ''}
        ${doc.status === 'verified' ? `<button class="btn btn-xs btn-danger" onclick="reviewKnowledgeDocument('${doc.id}', 'deprecated').catch(err => toast(err.message, 'error'))">标记废止</button>` : ''}
      </div>
    </div>`;
  }).join('') : '<div class="kb-empty">暂无候选或正式政策依据。运行含 web_search 的节点后会自动生成候选，也可以手动提交 URL。</div>';

  return `
    <div class="card" style="margin-bottom:12px;">
      <h2>政策依据库 <span class="badge badge-new">候选审核</span></h2>
      <div class="kb-select-bar" style="background:#eef7ff;border-color:#bbdefb;">搜索发现的政策文件先进入候选库；人工确认后才作为正式政策库依据使用。</div>
      <div class="btn-group" style="margin-bottom:10px;">
        ${filterButtons}
        <button class="btn btn-xs btn-outline" onclick="refreshKnowledgeDocuments(state.knowledgeStatusFilter || '').catch(err => toast(err.message, 'error'))">刷新</button>
      </div>
      ${batchBar}
      <div class="form-group" style="margin-bottom:10px;">
        <label>手动提交政策 URL</label>
        <div style="display:grid;grid-template-columns:2fr 1fr auto;gap:8px;align-items:center;">
          <input id="knowledgeCandidateUrl" placeholder="https://..." style="padding:8px;border:1px solid var(--border);border-radius:4px;">
          <input id="knowledgeCandidateTitle" placeholder="标题（可选）" style="padding:8px;border:1px solid var(--border);border-radius:4px;">
          <button class="btn btn-primary btn-sm" onclick="ingestKnowledgeUrl().catch(err => toast(err.message, 'error'))">抓取候选</button>
        </div>
      </div>
      <div class="kb-list">${list}</div>
    </div>`;
}

function syncTaskState(task) {
  if (!task) return;
  state.taskId = task.task_id || state.taskId;
  state.taskStatus = task.status || '';
  state.nextNode = task.next_node || '';
  state.evidenceRefs = task.evidence_refs || [];
  state.taskKnowledgeDocIds = task.knowledge_doc_ids || [];
  const results = task.module_results || {};
  BACKEND_IMPLEMENTED_NODES.forEach(code => {
    if (!Object.prototype.hasOwnProperty.call(results, code)) {
      delete state.results[code];
      delete state.nodeStatuses[code];
      delete state.nodeEvidenceRefs[code];
      delete state.liveOutput[code];
    }
  });
  Object.entries(results).forEach(([code, result]) => {
    state.nodeStatuses[code] = result.status || 'completed';
    if (Object.prototype.hasOwnProperty.call(result, 'markdown')) state.results[code] = result.markdown || '';
    state.nodeEvidenceRefs[code] = result.evidence_refs || [];
    if (result.status === 'completed' || result.status === 'failed') delete state.liveOutput[code];
  });
  syncTaskEvents(task.events || []);
  saveState();
}

async function refreshAdminData({ rerender = true } = {}) {
  const [workflow, knowledge, history] = await Promise.all([
    apiFetch('/api/admin/workflow/nodes').catch(() => ({ nodes: [], missing_nodes: [] })),
    apiFetch('/api/knowledge/documents').catch(() => ({ documents: [] })),
    apiFetch('/api/admin/knowledge/review-history').catch(() => ({ records: [] })),
  ]);
  state.adminWorkflowNodes = workflow.nodes || [];
  state.knowledgeDocuments = knowledge.documents || [];
  state.adminKnowledgeHistory = history.records || [];
  saveState();
  if (rerender) { renderStep(); updateSidebar(); }
  return { workflow, knowledge, history };
}

async function refreshTask({ rerender = false } = {}) {
  if (!state.taskId) return null;
  const task = await apiFetch(`/api/tasks/${state.taskId}`);
  syncTaskState(task);
  if (rerender) { renderStep(); updateSidebar(); }
  return task;
}

async function testBackendConnection() {
  state.backendBase = document.getElementById('backendBase')?.value.trim() || state.backendBase;
  saveState();
  const health = await apiFetch('/api/health');
  toast(`后端连接正常：Hermes ${health.hermes?.status || 'unknown'}`, 'success');
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
  state.nodeStatuses = {};
  state.nodeEvidenceRefs = {};
  state.evidenceRefs = [];
  state.results = {};
  state.eventLog = [];
  state.liveOutput = {};
  state.taskKnowledgeDocIds = [];
  state.selectedKnowledgeDocIds = [];
  saveState();
  connectTaskEvents(state.taskId);
  return response;
}

async function ensureBackendTask() {
  if (state.taskId) return state.taskId;
  const task = await createBackendTask();
  return task.task_id;
}

function connectTaskEvents(taskId = state.taskId) {
  if (!taskId || typeof EventSource === 'undefined') return;
  if (state.eventSource) state.eventSource.close();
  const source = new EventSource(backendUrl(`/api/tasks/${taskId}/events`));
  state.eventSource = source;
  source.onmessage = event => {
    const evt = JSON.parse(event.data);
    handleTaskEvent(evt);
  };
  source.onerror = () => {
    source.close();
    if (state.eventSource === source) state.eventSource = null;
  };
}

function handleTaskEvent(evt) {
  const nodeId = evt.node_id || '';
  if (evt.type === 'node_output_partial') {
	    state.liveOutput[nodeId] = `${state.liveOutput[nodeId] || ''}${evt.message || ''}`;
	    if (currentModuleCode() === nodeId) {
	      setResultBoxMarkdown(state.liveOutput[nodeId] || '正在接收后端输出...', { loading: true });
	    }
	    return;
	  }
  appendEventLog(evt);
  if (evt.type === 'node_start') state.nodeStatuses[nodeId] = 'running';
  if (evt.type === 'node_failed') state.nodeStatuses[nodeId] = 'failed';
  if (evt.type === 'node_complete') state.nodeStatuses[nodeId] = 'completed';
  if (['node_complete', 'node_failed', 'node_paused'].includes(evt.type)) delete state.liveOutput[nodeId];
  if (evt.type === 'task_run_started') state.taskStatus = 'running';
  if (evt.type === 'task_paused') state.taskStatus = 'paused';
  if (evt.type === 'task_completed') state.taskStatus = 'completed';
  if (['node_complete', 'node_failed', 'task_paused', 'task_completed'].includes(evt.type)) {
    refreshTask({ rerender: true }).catch(err => toast(`刷新任务失败：${err.message}`, 'error'));
  }
}

async function runBackendStep(code) {
  if (!BACKEND_IMPLEMENTED_NODES.includes(code)) {
    toast(`${code} 当前缺少后端提示词，暂未接入`, 'info');
    return;
  }
  await ensureBackendTask();
  if (state.nextNode && state.nextNode !== code) {
    throw new Error(`当前任务下一节点是 ${state.nextNode}，请按流程执行`);
  }
  connectTaskEvents(state.taskId);
  const response = await apiFetch(`/api/tasks/${state.taskId}/step`, { method: 'POST' });
  if (response.result?.markdown) state.results[code] = response.result.markdown;
  if (response.result?.status) state.nodeStatuses[code] = response.result.status;
  state.taskStatus = response.status;
  state.nextNode = response.next_node || '';
  saveState();
  if (response.result?.status && response.result.status !== 'completed') {
    throw new Error(response.result.error || response.result.markdown || `${code} 执行失败`);
  }
}

async function runBackendAll() {
  await ensureBackendTask();
  connectTaskEvents(state.taskId);
  const response = await apiFetch(`/api/tasks/${state.taskId}/run`, { method: 'POST' });
  state.taskStatus = response.status;
  state.nextNode = response.next_node || '';
  saveState();
  renderStep();
  updateSidebar();
  toast('已启动一键分析全部流程，可随时暂停', 'success');
}

async function pauseBackendTask() {
  if (!state.taskId) { toast('还没有后端任务', 'info'); return; }
  const response = await apiFetch(`/api/tasks/${state.taskId}/pause`, { method: 'POST' });
  state.taskStatus = response.status;
  saveState();
  toast('已请求暂停任务', 'info');
}

async function runPrepIngest() {
  await ensureBackendTask();
  if (state.nextNode && state.nextNode !== 'PREP-INGEST') {
    throw new Error(`当前任务下一节点是 ${state.nextNode}，不能重复运行资料读取 Agent`);
  }
  connectTaskEvents(state.taskId);
  const response = await apiFetch(`/api/tasks/${state.taskId}/step`, { method: 'POST' });
  if (response.result?.markdown) state.results['PREP-INGEST'] = response.result.markdown;
  if (response.result?.status) state.nodeStatuses['PREP-INGEST'] = response.result.status;
  state.taskStatus = response.status;
  state.nextNode = response.next_node || '';
  saveState();
  if (response.result?.status && response.result.status !== 'completed') {
    throw new Error(response.result.error || response.result.markdown || '项目资料读取失败');
  }
  await refreshTask({ rerender: true });
  toast('项目档案已生成，下一步执行 HB-PT-000', 'success');
}

async function runFileValidation() {
  await ensureBackendTask();
  connectTaskEvents(state.taskId);
  const btn = window.event?.target || null;
  if (btn) { btn.disabled = true; btn.textContent = '验证中...'; }
  try {
    const result = await apiFetch(`/api/tasks/${state.taskId}/validate-files`, { method: 'POST' });
    if (result.markdown) state.results['FILE-VALIDATION'] = result.markdown;
    if (result.status) state.nodeStatuses['FILE-VALIDATION'] = result.status;
    state.nodeEvidenceRefs['FILE-VALIDATION'] = result.evidence_refs || [];
    saveState();
    await refreshTask({ rerender: true });
    toast('上传资料验证完成', 'success');
  } finally {
    if (btn) { btn.disabled = false; btn.textContent = 'AI验证上传资料'; }
  }
}

async function refreshKnowledgeDocuments(status = state.knowledgeStatusFilter || '') {
  state.knowledgeStatusFilter = status || '';
  if (state.taskId) {
    const response = await apiFetch(`/api/tasks/${state.taskId}/knowledge-candidates`);
    const allDocuments = response.documents || [];
    state.taskKnowledgeDocIds = allDocuments.filter(doc => doc.selected_for_task).map(doc => doc.id);
    state.knowledgeDocuments = status ? allDocuments.filter(doc => doc.status === status) : allDocuments;
  } else {
    const query = status ? `?status=${encodeURIComponent(status)}` : '';
    const response = await apiFetch(`/api/knowledge/documents${query}`);
    state.knowledgeDocuments = response.documents || [];
  }
  saveState();
  renderStep();
  updateSidebar();
  return state.knowledgeDocuments;
}

async function ingestKnowledgeUrl() {
  const url = document.getElementById('knowledgeCandidateUrl')?.value.trim();
  const title = document.getElementById('knowledgeCandidateTitle')?.value.trim();
  if (!url) { toast('请填写 URL', 'error'); return; }
  await apiFetch('/api/knowledge/ingest', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ url, title }),
  });
  toast('候选依据已抓取入库', 'success');
  await refreshKnowledgeDocuments('');
}

async function reviewKnowledgeDocument(docId, status) {
  const defaultValidity = status === 'verified' ? 'effective' : (status === 'deprecated' ? 'superseded' : 'unknown');
  const note = status === 'rejected' ? '人工驳回' : (status === 'verified' ? '人工确认正式依据' : '');
  await apiFetch(`/api/knowledge/documents/${docId}/verify`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ status, validity: defaultValidity, note, reviewer: 'frontend' }),
  });
  toast('依据状态已更新', 'success');
  await refreshKnowledgeDocuments(state.knowledgeStatusFilter || '');
}

async function updateTaskKnowledgeDocument(docId, mode) {
  if (!state.taskId) { toast('请先初始化任务', 'error'); return; }
  const response = await apiFetch(`/api/tasks/${state.taskId}/knowledge-documents`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ mode, doc_ids: [docId] }),
  });
  state.taskKnowledgeDocIds = response.knowledge_doc_ids || [];
  toast(mode === 'remove' ? '已移出本任务依据' : '已加入本任务依据', 'success');
  await refreshTask({ rerender: false }).catch(() => null);
  await refreshKnowledgeDocuments(state.knowledgeStatusFilter || '');
}

function resetBackendTask() {
  if (state.eventSource) state.eventSource.close();
  state.taskId = '';
  state.taskStatus = '';
  state.nextNode = '';
  state.nodeStatuses = {};
  state.nodeEvidenceRefs = {};
  state.evidenceRefs = [];
  state.taskKnowledgeDocIds = [];
  state.selectedKnowledgeDocIds = [];
  state.eventLog = [];
  state.liveOutput = {};
  saveState();
  renderStep();
  updateSidebar();
  toast('已清空前端任务绑定，后端历史记录仍可通过 task_id 查询', 'info');
}

// ============ KB HELPERS ============
function getSelectedKbContent() {
  const selected = state.kbEntries.filter(e => state.selectedKbIds.includes(e.id));
  if (selected.length === 0) return '';
  return selected.map(e => `【${e.category}】${e.name}\n${e.content}`).join('\n\n---\n\n');
}

function buildFullSystemPrompt() {
  let prompt = SYSTEM_PROMPT;
  if (state.knowledgeBase) {
    prompt += `\n\n【项目补充参考材料】\n${state.knowledgeBase}`;
  }
  if (state.searchContext) {
    prompt += `\n\n【联网检索结果——以下为针对当前研判问题从互联网检索到的官方回复和解读文件，请基于这些信息辅助判断】\n${state.searchContext}`;
  }
  // 参考资料库自动注入（含手动添加的文本条目和本地文件）
  if (state.localFiles.length > 0) {
    const groups = {};
    state.localFiles.forEach(f => {
      const label = f.folderLabel || '未分类';
      if (!groups[label]) groups[label] = [];
      groups[label].push(f);
    });
    const fileContent = Object.entries(groups).map(([label, files]) => 
      `### ${label}\n` + files.map(f => `【文件：${f.name}（${f.type || '手动添加'}）】\n${f.content}`).join('\n\n')
    ).join('\n\n---\n\n');
    prompt += `\n\n【参考资料库——以下为用户加载的参考文件和政策法规，按分类整理，请基于这些材料进行分析判断】\n${fileContent}`;
  }
  return prompt;
}

// ============ UI HELPERS ============
function toast(msg, type = 'info') {
  const container = document.getElementById('toastContainer');
  const el = document.createElement('div'); el.className = `toast ${type}`; el.textContent = msg;
  container.appendChild(el); setTimeout(() => el.remove(), 3000);
}

function updateSidebar() {
  document.querySelectorAll('.step-item').forEach(el => {
    const step = parseInt(el.dataset.step);
    el.classList.remove('active', 'done');
    const statusEl = el.querySelector('.step-status');
    if (statusEl) statusEl.textContent = '';
    if (step === state.currentStep) el.classList.add('active');
    if (step >= 0 && step < state.currentStep) el.classList.add('done');
    const code = STEP_NODE_MAP[step];
    if (code && !BACKEND_IMPLEMENTED_NODES.includes(code)) {
      el.classList.remove('done');
      if (statusEl) statusEl.textContent = '未接入';
      el.title = `${code} 尚未接入后端提示词`;
    }
  });
  // Update module result statuses
  for (let i = 0; i <= 11; i++) {
    const code = `HB-PT-${String(i).padStart(3, '0')}`;
    const stepEl = document.querySelector(`.step-item[data-step="${i + 2}"]`);
    if (stepEl && state.results[code]) { stepEl.classList.add('done'); stepEl.querySelector('.step-status').textContent = '✓'; }
    if (stepEl && state.nodeStatuses[code] === 'running') { stepEl.querySelector('.step-status').textContent = '…'; }
    if (stepEl && state.nodeStatuses[code] === 'failed') { stepEl.querySelector('.step-status').textContent = '!'; }
  }
  if (state.results['HB-PT-010']) { const el = document.querySelector('.step-item[data-step="12"]'); if (el) { el.classList.add('done'); el.querySelector('.step-status').textContent = '✓'; } }
  if (state.results['HB-PT-011']) { const el = document.querySelector('.step-item[data-step="13"]'); if (el) { el.classList.add('done'); el.querySelector('.step-status').textContent = '✓'; } }
  const btnExport = document.getElementById('btnExport');
  if (btnExport) btnExport.disabled = !state.results['HB-PT-010'];
  const btnExportArchive = document.getElementById('btnExportArchive');
  if (btnExportArchive) btnExportArchive.disabled = !state.taskId;
  const kbCountEl = document.getElementById('kbCount');
  if (kbCountEl) kbCountEl.textContent = state.kbEntries.length;
  const lfcEl = document.getElementById('localFileCount');
  if (lfcEl) lfcEl.textContent = state.localFiles.length;
}

function switchStep(step) { state.currentStep = step; saveState(); renderStep(); updateSidebar(); }

function renderStep() {
  const c = document.getElementById('mainContent');
  const s = state.currentStep;
  if (s === -4) return renderAdminDashboard(c);
  if (s === -3) return renderLocalFiles(c);
  if (s === -2) return renderSearchPanel(c);
  if (s === -1) { state.currentStep = -3; return renderLocalFiles(c); } // redirect legacy KB
  if (s === 0) return renderApiConfig(c);
  if (s === 1) return renderProjectInput(c);
  if (s >= 2 && s <= 11) return renderModuleStep(c, s - 2);
  if (s === 12) return renderModuleStep(c, 10);
  if (s === 13) return renderModuleStep(c, 11);
}

function renderAdminDashboard(container) {
  const docs = state.knowledgeDocuments || [];
  const history = state.adminKnowledgeHistory || [];
  const nodes = state.adminWorkflowNodes || [];
  const implementedCount = nodes.filter(node => node.implemented).length;
  const missingNodes = nodes.filter(node => !node.implemented);
  const counts = docs.reduce((acc, doc) => {
    acc[doc.status || 'unknown'] = (acc[doc.status || 'unknown'] || 0) + 1;
    return acc;
  }, {});
  const nodeRows = nodes.length ? nodes.map(node => `
    <tr>
      <td>${escapeHtml(node.node_id)}</td>
      <td>${escapeHtml(node.title || '')}</td>
      <td>${node.implemented ? '<span style="color:var(--success);font-weight:600;">已接入</span>' : '<span style="color:var(--danger);font-weight:600;">未接入</span>'}</td>
      <td>${escapeHtml(node.prompt_file || '-')}</td>
      <td>${escapeHtml(node.next_node || '-')}</td>
    </tr>`).join('') : '<tr><td colspan="5" style="color:#999;text-align:center;">暂无节点数据</td></tr>';
  const historyRows = history.length ? history.slice(0, 80).map(item => `
    <tr>
      <td>${escapeHtml(item.reviewed_at ? new Date(item.reviewed_at).toLocaleString() : '')}</td>
      <td>${escapeHtml(item.document_title || item.document_id || '')}</td>
      <td>${escapeHtml(item.status || '')}</td>
      <td>${escapeHtml(item.validity || '')}</td>
      <td>${escapeHtml(item.reviewer || '')}</td>
      <td>${escapeHtml(item.note || '')}</td>
    </tr>`).join('') : '<tr><td colspan="6" style="color:#999;text-align:center;">暂无审核历史</td></tr>';

  container.innerHTML = `
    <div class="card">
      <h2>后台管理 <span class="badge badge-core">系统状态</span></h2>
      <div class="kb-stats">
        <span class="kb-stat"><strong>${docs.length}</strong> 知识库文件</span>
        <span class="kb-stat"><strong>${counts.candidate || 0}</strong> 候选</span>
        <span class="kb-stat"><strong>${counts.verified || 0}</strong> 正式</span>
        <span class="kb-stat"><strong>${history.length}</strong> 审核记录</span>
        <span class="kb-stat"><strong>${implementedCount}/${nodes.length || BACKEND_IMPLEMENTED_NODES.length}</strong> 节点接入</span>
      </div>
      <div class="btn-group">
        <button class="btn btn-primary btn-sm" onclick="refreshAdminData().catch(err => toast(err.message, 'error'))">刷新后台数据</button>
        <button class="btn btn-outline btn-sm" onclick="switchStep(-3)">进入知识库管理</button>
        <button class="btn btn-outline btn-sm" onclick="openTaskManifest()">查看当前任务 Manifest</button>
      </div>
      ${missingNodes.length ? `<div class="kb-select-bar" style="background:#fff8e1;border-color:#ffe082;margin-top:12px;">未接入节点：${missingNodes.map(node => escapeHtml(node.node_id)).join('、')}。这些左侧步骤当前只能查看说明，不能运行后端 Agent。</div>` : ''}
    </div>
    <div class="card">
      <h2>工作流节点接入状态</h2>
      <div style="overflow-x:auto;">
        <table class="admin-table">
          <thead><tr><th>节点</th><th>名称</th><th>状态</th><th>提示词文件</th><th>下一节点</th></tr></thead>
          <tbody>${nodeRows}</tbody>
        </table>
      </div>
    </div>
    <div class="card">
      <h2>知识库审核历史</h2>
      <div style="overflow-x:auto;max-height:420px;overflow-y:auto;">
        <table class="admin-table">
          <thead><tr><th>时间</th><th>文件</th><th>状态</th><th>有效性</th><th>审核人</th><th>备注</th></tr></thead>
          <tbody>${historyRows}</tbody>
        </table>
      </div>
    </div>
    ${renderKnowledgeDocumentsHtml()}
  `;
  if (!nodes.length && !history.length && !docs.length) {
    refreshAdminData({ rerender: true }).catch(err => toast(`后台数据加载失败：${err.message}`, 'error'));
  }
}

// ============ LOCAL FILES ============
function renderLocalFiles(container) {
  const files = state.localFiles;
  const totalSize = files.reduce((s, f) => s + (f.size || 0), 0);
  
  // 按分类标签分组
  const groups = {};
  files.forEach(f => {
    const label = f.folderLabel || '未分类';
    if (!groups[label]) groups[label] = [];
    groups[label].push(f);
  });
  
  const listHtml = files.length === 0
    ? `<div class="kb-empty">尚未加载本地文件。点击下方按钮或拖拽文件到此处。</div>`
    : Object.entries(groups).map(([label, groupFiles]) => `
      <div style="margin-bottom:10px;">
        <div style="font-size:12px;font-weight:600;color:var(--primary-light);padding:4px 0;display:flex;align-items:center;gap:8px;">
          <span style="background:#e0f2f1;padding:2px 10px;border-radius:10px;">${escapeHtml(label)}</span>
          <span style="color:#999;font-weight:normal;">${groupFiles.length} 个文件</span>
          <button class="btn btn-xs btn-outline" onclick="removeLocalFileGroup('${escapeHtml(label)}')" style="margin-left:auto;">移除此组</button>
        </div>
        ${groupFiles.map(f => `
          <div class="kb-item">
            <div class="kb-info">
              <div class="kb-name">${fileIcon(f.type)} ${escapeHtml(f.name)} ${validityBadge(f.validity ? f.validity.status : null)}</div>
              <div class="kb-meta">
                ${formatSize(f.size)} · ${f.type.toUpperCase()} · 加载于 ${f.loadedAt || '未知'}
                ${f.validity ? ` · 文号：${escapeHtml(f.validity.docNumber || '')} · 发布日期：${escapeHtml(f.validity.publishDate || '')}` : ''}
              </div>
            </div>
            <div class="kb-actions">
              <button class="btn btn-xs btn-outline" onclick="previewLocalFile('${f.id}')">预览</button>
              <button class="btn btn-xs btn-outline" onclick="recheckFileValidity('${f.id}')">重新检查</button>
              <button class="btn btn-xs btn-danger" onclick="removeLocalFile('${f.id}')">移除</button>
            </div>
          </div>`).join('')}
      </div>
    `).join('');

  const labels = [...new Set(files.map(f => f.folderLabel || '未分类'))];
  const statsHtml = labels.map(l => {
    const count = files.filter(f => (f.folderLabel || '未分类') === l).length;
    return `<span class="kb-stat"><strong>${count}</strong> ${escapeHtml(l)}</span>`;
  }).join('');

  let validityTableHtml = '';
  const checkedFiles = files.filter(f => f.validity);
  if (checkedFiles.length > 0) {
    const invalidCount = checkedFiles.filter(f => f.validity.status && (f.validity.status.includes('废止') || f.validity.status.includes('替代') || f.validity.status.includes('疑似'))).length;
    const validCount = checkedFiles.filter(f => f.validity.status && f.validity.status.includes('有效')).length;
    const unknownCount = checkedFiles.length - invalidCount - validCount;
    
    validityTableHtml = `
      <div class="card" style="margin-bottom:12px;">
        <h2>政策有效性检查结果 <span class="badge badge-new">自动检查</span></h2>
        <div class="kb-stats" style="margin-bottom:8px;">
          <span class="kb-stat" style="color:#27ae60;">现行有效 <strong>${validCount}</strong></span>
          ${invalidCount > 0 ? `<span class="kb-stat" style="color:#e74c3c;">有风险 <strong>${invalidCount}</strong></span>` : ''}
          ${unknownCount > 0 ? `<span class="kb-stat" style="color:#888;">无法判断 <strong>${unknownCount}</strong></span>` : ''}
        </div>
        <div style="overflow-x:auto;">
          <table style="width:100%;border-collapse:collapse;font-size:12px;">
            <thead>
              <tr style="background:#f5f5f5;text-align:left;">
                <th style="padding:6px 8px;border-bottom:1px solid #ddd;">文件名称</th>
                <th style="padding:6px 8px;border-bottom:1px solid #ddd;">文号</th>
                <th style="padding:6px 8px;border-bottom:1px solid #ddd;">发布日期</th>
                <th style="padding:6px 8px;border-bottom:1px solid #ddd;">有效性状态</th>
                <th style="padding:6px 8px;border-bottom:1px solid #ddd;">判断依据</th>
              </tr>
            </thead>
            <tbody>
              ${checkedFiles.map(f => {
                const v = f.validity;
                let statusColor = '#888';
                if (v.status.includes('有效')) statusColor = '#27ae60';
                else if (v.status.includes('废止') || v.status.includes('替代')) statusColor = '#e74c3c';
                else if (v.status.includes('疑似')) statusColor = '#f39c12';
                return `<tr>
                  <td style="padding:4px 8px;border-bottom:1px solid #eee;">${escapeHtml(f.name)}</td>
                  <td style="padding:4px 8px;border-bottom:1px solid #eee;">${escapeHtml(v.docNumber || '')}</td>
                  <td style="padding:4px 8px;border-bottom:1px solid #eee;">${escapeHtml(v.publishDate || '')}</td>
                  <td style="padding:4px 8px;border-bottom:1px solid #eee;color:${statusColor};font-weight:600;">${escapeHtml(v.status)}</td>
                  <td style="padding:4px 8px;border-bottom:1px solid #eee;font-size:11px;color:#666;">${escapeHtml(v.basis || '')}</td>
                </tr>`;
              }).join('')}
            </tbody>
          </table>
        </div>
        <div style="margin-top:8px;font-size:11px;color:#888;">检查时间：${checkedFiles[0].validity ? checkedFiles[0].validity.checkedAt : ''} · 上传文件后自动检查，无需手动操作</div>
      </div>`;
  }

  container.innerHTML = `
    ${renderKnowledgeDocumentsHtml()}
    ${validityTableHtml}
    <div class="card">
      <h2>参考资料库</h2>
      <p style="color:#888;font-size:13px;margin-bottom:12px;">统一管理参考文件和政策法规线索。当前页面只记录本地资料元数据；政策有效性和是否可用于项目分析请通过后端 Agent 验证或候选依据审核流程完成。</p>
      <div class="kb-stats">
        <span class="kb-stat"><strong>${files.length}</strong> 个条目</span>
        <span class="kb-stat"><strong>${formatSize(totalSize)}</strong> 总计</span>
        ${statsHtml}
      </div>
      <div class="btn-group" style="margin-bottom:10px;">
        <button class="btn btn-primary btn-sm" onclick="showManualAddModal()">+ 手动添加文本</button>
        <button class="btn btn-outline btn-sm" onclick="pickFolder()">选择文件夹</button>
        ${files.length > 0 ? '<button class="btn btn-outline btn-sm" onclick="exportKb()">导出</button>' : ''}
        ${files.length > 0 ? '<button class="btn btn-outline btn-sm" onclick="importKbFile()">导入</button>' : ''}
      </div>
      <div class="file-drop-zone" id="localFileDropZone" onclick="document.getElementById('localFileInput').click()">
        <p>点击选择文件，或拖拽文件到此处</p>
        <p style="font-size:11px;color:#999;">支持格式：.docx / .pdf / .txt / .html</p>
        <input type="file" id="localFileInput" multiple accept=".docx,.pdf,.txt,.html,.htm" onchange="handleLocalFiles(this.files)" style="display:none;">
      </div>
      <div id="folderFileList" style="margin-top:8px;font-size:12px;"></div>
      <div id="localFileProgress" style="font-size:12px;margin-top:8px;"></div>
      <div class="kb-list" style="margin-top:12px;">${listHtml}</div>
      ${files.length > 0 ? `<div class="btn-group" style="margin-top:12px;"><button class="btn btn-danger btn-sm" onclick="clearAllLocalFiles()">清空全部本地文件</button></div>` : ''}
    </div>
    <div class="card">
      <h2>文件内容预览</h2>
      <div class="result-box" style="max-height:400px;font-size:12px;" id="localFilePreview">点击文件列表中的"预览"查看内容</div>
    </div>
  `;

  // Drag & drop
  setTimeout(() => {
    const dropZone = document.getElementById('localFileDropZone');
    if (dropZone) {
      dropZone.addEventListener('dragover', e => { e.preventDefault(); dropZone.classList.add('dragover'); });
      dropZone.addEventListener('dragleave', () => dropZone.classList.remove('dragover'));
      dropZone.addEventListener('drop', e => { e.preventDefault(); dropZone.classList.remove('dragover'); handleLocalFiles(e.dataTransfer.files); });
    }
  }, 0);
}

function fileIcon(type) {
  const icons = { docx: '📄', pdf: '📕', txt: '📝', html: '🌐', htm: '🌐' };
  return icons[type] || '📎';
}

function formatSize(bytes) {
  if (!bytes || bytes === 0) return '0 B';
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

async function handleLocalFiles(fileList, folderLabel) {
  if (!fileList || fileList.length === 0) return;
  const progressEl = document.getElementById('localFileProgress');
  const label = folderLabel || '未分类';
  let recorded = 0;
  
  for (const file of Array.from(fileList)) {
    const ext = file.name.split('.').pop().toLowerCase();
    const supported = ['docx', 'pdf', 'txt', 'html', 'htm', 'png', 'jpg', 'jpeg', 'webp'];
    if (!supported.includes(ext)) {
      toast(`不支持的文件格式：${file.name}`, 'error');
      continue;
    }

    const content = [
      '该文件仅在前端记录元数据，未进行浏览器端文本解析。',
      '项目资料请在“项目信息输入”页上传，由后端 PREP-INGEST Agent 读取。',
      '政策依据请通过后端知识库候选入库、人工确认后使用。',
    ].join('\n');
    const existingIdx = state.localFiles.findIndex(f => f.name === file.name);
    if (existingIdx >= 0) {
      state.localFiles[existingIdx] = {
        id: state.localFiles[existingIdx].id,
        name: file.name,
        type: ext,
        size: file.size,
        content,
        folderLabel: label,
        loadedAt: new Date().toLocaleString('zh-CN'),
      };
    } else {
      state.localFiles.push({
        id: Date.now().toString(36) + Math.random().toString(36).slice(2, 6),
        name: file.name,
        type: ext,
        size: file.size,
        content,
        folderLabel: label,
        loadedAt: new Date().toLocaleString('zh-CN'),
      });
    }
    recorded++;
  }
  
  saveState();
  renderLocalFiles(document.getElementById('mainContent'));
  updateSidebar();
  if (progressEl) progressEl.textContent = `已记录 ${recorded} 个文件元数据；未在前端解析正文。`;
  toast(`已记录 ${recorded} 个文件元数据`, 'success');
  
  // 政策有效性检查已迁移到后端 Agent/知识库流程，不在前端直连模型。
}

function previewLocalFile(id) {
  const file = state.localFiles.find(f => f.id === id);
  const previewEl = document.getElementById('localFilePreview');
  if (file && previewEl) {
    previewEl.textContent = file.content;
    previewEl.scrollTop = 0;
  }
}

function removeLocalFile(id) {
  state.localFiles = state.localFiles.filter(f => f.id !== id);
  saveState();
  renderLocalFiles(document.getElementById('mainContent'));
  updateSidebar();
  toast('已移除文件', 'info');
}

function clearAllLocalFiles() {
  if (!confirm('确定要清空全部参考资料吗？此操作不可恢复。')) return;
  state.localFiles = [];
  saveState();
  renderLocalFiles(document.getElementById('mainContent'));
  updateSidebar();
  toast('已清空全部参考资料', 'info');
}

// 手动添加文本条目
function showManualAddModal() {
  const modal = document.getElementById('modalContainer');
  modal.innerHTML = `
    <div class="modal-overlay">
      <div class="modal" style="max-width:500px;">
        <button class="close" onclick="closeModal()">&times;</button>
        <h3>手动添加参考资料</h3>
        <div class="form-group"><label>条目名称</label><input type="text" id="manualName" placeholder="例如：环评分类管理名录2021年版"></div>
        <div class="form-group"><label>分类标签</label><input type="text" id="manualLabel" placeholder="例如：政策法规、技术导则、审批原则" value="政策法规"></div>
        <div class="form-group"><label>内容</label><textarea id="manualContent" style="min-height:150px;" placeholder="粘贴政策文件内容..."></textarea></div>
        <div class="btn-group">
          <button class="btn btn-primary" onclick="saveManualEntry()">保存</button>
          <button class="btn btn-outline" onclick="closeModal()">取消</button>
        </div>
      </div>
    </div>`;
}

function saveManualEntry() {
  const name = document.getElementById('manualName')?.value.trim();
  const label = document.getElementById('manualLabel')?.value.trim() || '未分类';
  const content = document.getElementById('manualContent')?.value.trim();
  if (!name) { toast('请输入条目名称', 'error'); return; }
  if (!content) { toast('请输入内容', 'error'); return; }

  state.localFiles.push({
    id: Date.now().toString(36) + Math.random().toString(36).slice(2, 6),
    name: name,
    type: 'txt',
    size: new Blob([content]).size,
    content: content,
    folderLabel: label,
    loadedAt: new Date().toLocaleString('zh-CN'),
    validity: null, // 也会自动检查
  });
  saveState();
  closeModal();
  renderLocalFiles(document.getElementById('mainContent'));
  updateSidebar();
  toast(`已添加"${name}"到参考资料库`, 'success');
  
  // 政策有效性检查已迁移到后端 Agent/知识库流程，不在前端直连模型。
}

// 迁移旧知识库条目到参考资料库（一次性）
function migrateOldKbEntries() {
  if (!state.kbEntries || state.kbEntries.length === 0) return;
  const existingNames = new Set(state.localFiles.map(f => f.name));
  let migrated = 0;
  state.kbEntries.forEach(entry => {
    if (!existingNames.has(entry.name)) {
      state.localFiles.push({
        id: entry.id || Date.now().toString(36) + Math.random().toString(36).slice(2, 6),
        name: entry.name,
        type: 'txt',
        size: new Blob([entry.content || '']).size,
        content: entry.content || '',
        folderLabel: entry.category || '知识库迁移',
        loadedAt: entry.createdAt || new Date().toLocaleString('zh-CN'),
        validity: null,
      });
      migrated++;
    }
  });
  if (migrated > 0) {
    state.kbEntries = [];
    saveState();
    toast(`已将 ${migrated} 条旧知识库条目迁移到参考资料库`, 'info');
  }
}

// 自动检查所有本地文件的政策有效性
async function autoCheckLocalFilesValidity() {
  toast('政策有效性检查已迁移到后端 Agent/知识库流程', 'info');
  return;
  const files = state.localFiles.filter(f => !f.validity); // 只检查未检查过的
  if (files.length === 0) return;
  
  const listEl = document.getElementById('localFileProgress');
  let checked = 0;
  
  for (const file of files) {
    if (listEl) listEl.textContent = `正在检查政策有效性 (${checked + 1}/${files.length})：${file.name}...`;
    
    try {
      const result = await checkSingleFileValidity(file);
      // 找到并更新
      const idx = state.localFiles.findIndex(f => f.id === file.id);
      if (idx >= 0) {
        state.localFiles[idx].validity = result;
      }
      checked++;
      saveState();
    } catch (err) {
      const idx = state.localFiles.findIndex(f => f.id === file.id);
      if (idx >= 0) {
        state.localFiles[idx].validity = { status: '检查失败', error: err.message, checkedAt: new Date().toLocaleString('zh-CN') };
      }
      checked++;
      saveState();
    }
    
    // 避免API限流
    if (checked < files.length) await new Promise(r => setTimeout(r, 500));
  }
  
  if (listEl) listEl.textContent = checked > 0 ? `有效性检查完成：${checked} 个文件` : '';
  renderLocalFiles(document.getElementById('mainContent'));
}

async function checkSingleFileValidity(file) {
  const prompt = `请检查以下政策文件/技术规范是否仍然现行有效，提取关键信息。

文件名称：${file.name}
文件内容（前2000字）：${file.content.substring(0, 2000)}

请严格按以下格式回复（每行一项，不要添加额外说明）：
文件名称：{文件全称}
文号：{从内容中提取，如无则填"未提及"}
发布日期：{从内容中提取，如无则填"未提及"}
有效性状态：{现行有效/疑似废止/已废止/已被替代/部分条款失效/无法判断}
判断依据：{一句话说明判断理由，如"该文件为现行有效的国家标准，未有废止公告"或"无法确认有效性，建议人工核实"}

注意：仅基于你已知的信息和文件内容判断，如无法确认请标注"无法判断"，不要编造信息。`;

  const response = await callDeepSeek(SYSTEM_PROMPT, prompt);
  
  // 解析回复
  const nameMatch = response.match(/文件名称[：:]\s*(.+)/);
  const docMatch = response.match(/文号[：:]\s*(.+)/);
  const dateMatch = response.match(/发布日期[：:]\s*(.+)/);
  const statusMatch = response.match(/有效性状态[：:]\s*(.+)/);
  const basisMatch = response.match(/判断依据[：:]\s*(.+)/);
  
  return {
    fileName: nameMatch ? nameMatch[1].trim() : file.name,
    docNumber: docMatch ? docMatch[1].trim() : '未提及',
    publishDate: dateMatch ? dateMatch[1].trim() : '未提及',
    status: statusMatch ? statusMatch[1].trim() : '无法判断',
    basis: basisMatch ? basisMatch[1].trim() : '未提供判断依据',
    checkedAt: new Date().toLocaleString('zh-CN'),
    raw: response,
  };
}

function validityBadge(status) {
  if (!status) return '<span style="font-size:10px;color:#999;background:#f0f0f0;padding:1px 6px;border-radius:8px;">未检查</span>';
  if (status === '检查中') return '<span style="font-size:10px;color:#1976d2;background:#e3f2fd;padding:1px 6px;border-radius:8px;">检查中</span>';
  if (status === '检查失败') return '<span style="font-size:10px;color:#e74c3c;background:#fce4ec;padding:1px 6px;border-radius:8px;">检查失败</span>';
  if (status.includes('有效')) return `<span style="font-size:10px;color:#27ae60;background:#e8f5e9;padding:1px 6px;border-radius:8px;" title="现行有效">${status}</span>`;
  if (status.includes('废止') || status.includes('替代')) return `<span style="font-size:10px;color:#e74c3c;background:#fce4ec;padding:1px 6px;border-radius:8px;" title="${status}">${status}</span>`;
  if (status.includes('疑似')) return `<span style="font-size:10px;color:#f39c12;background:#fff8e1;padding:1px 6px;border-radius:8px;" title="${status}">${status}</span>`;
  if (status.includes('无法判断')) return `<span style="font-size:10px;color:#888;background:#f5f5f5;padding:1px 6px;border-radius:8px;">${status}</span>`;
  return `<span style="font-size:10px;color:#888;background:#f5f5f5;padding:1px 6px;border-radius:8px;">${status}</span>`;
}

function removeLocalFileGroup(label) {
  if (!confirm(`确定要移除"${label}"分类下的全部文件吗？`)) return;
  state.localFiles = state.localFiles.filter(f => (f.folderLabel || '未分类') !== label);
  saveState();
  renderLocalFiles(document.getElementById('mainContent'));
  updateSidebar();
  toast(`已移除"${label}"分类`, 'info');
}

async function recheckFileValidity(id) {
  toast('政策有效性检查已迁移到后端 Agent/知识库流程', 'info');
  return;
  const file = state.localFiles.find(f => f.id === id);
  if (!file) return;
  if (!state.apiKey) { toast('请先配置API Key', 'error'); return; }
  
  const listEl = document.getElementById('localFileProgress');
  if (listEl) listEl.textContent = `正在重新检查：${file.name}...`;
  
  try {
    const result = await checkSingleFileValidity(file);
    const idx = state.localFiles.findIndex(f => f.id === id);
    if (idx >= 0) {
      state.localFiles[idx].validity = result;
    }
    saveState();
    if (listEl) listEl.textContent = `已重新检查：${file.name} → ${result.status}`;
    renderLocalFiles(document.getElementById('mainContent'));
    toast(`重新检查完成：${result.status}`, result.status.includes('有效') ? 'success' : 'info');
  } catch (err) {
    toast(`检查失败：${err.message}`, 'error');
    if (listEl) listEl.textContent = '';
  }
}

// 临时存储文件夹中的文件列表
let folderFilesCache = [];

async function pickFolder() {
  // 检查浏览器是否支持 File System Access API
  if (typeof window.showDirectoryPicker !== 'function') {
    toast('当前浏览器不支持"选择文件夹"功能，请使用 Chrome/Edge 浏览器，或使用拖拽上传', 'error');
    return;
  }
  
  try {
    const dirHandle = await window.showDirectoryPicker();
    const folderName = dirHandle.name || '未命名文件夹';
    folderFilesCache = [];
    const listEl = document.getElementById('folderFileList');
    if (listEl) listEl.innerHTML = '<div style="color:#888;padding:8px;">正在扫描文件夹...</div>';
    
    // 递归扫描文件夹中的文件
    await scanDirectory(dirHandle, '');
    
    if (folderFilesCache.length === 0) {
      if (listEl) listEl.innerHTML = '<div style="color:#888;padding:8px;">该文件夹中没有支持的文档文件（.docx/.pdf/.txt/.html）</div>';
      return;
    }
    
    // 显示文件列表，带分类标签输入
    const existingNames = new Set(state.localFiles.map(f => f.name));
    const html = `
      <div style="border:1px solid #ddd;border-radius:6px;padding:8px;max-height:360px;overflow-y:auto;">
        <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;padding-bottom:8px;border-bottom:1px solid #eee;flex-wrap:wrap;">
          <label style="cursor:pointer;font-size:12px;color:var(--primary-light);">
            <input type="checkbox" onchange="toggleAllFolderFiles(this.checked)"> 全选
          </label>
          <span style="font-size:11px;color:#888;">找到 ${folderFilesCache.length} 个文件</span>
          <span style="font-size:11px;color:#888;">分类标签：</span>
          <input type="text" id="folderLabelInput" value="${escapeHtml(folderName)}" style="width:140px;padding:3px 8px;font-size:12px;border:1px solid #ccc;border-radius:4px;" placeholder="输入分类名">
          <button class="btn btn-xs btn-primary" onclick="loadSelectedFolderFiles()" style="margin-left:auto;">加载选中文件</button>
        </div>
        ${folderFilesCache.map((f, i) => `
          <div style="display:flex;align-items:center;gap:6px;padding:3px 0;font-size:12px;${existingNames.has(f.name) ? 'color:#999;' : ''}">
            <input type="checkbox" class="folder-file-check" data-index="${i}" ${existingNames.has(f.name) ? 'disabled' : ''}>
            <span>${fileIcon(f.type)} ${escapeHtml(f.name)}</span>
            <span style="color:#999;font-size:10px;">${formatSize(f.size)}</span>
            ${existingNames.has(f.name) ? '<span style="color:#27ae60;font-size:10px;">(已加载)</span>' : ''}
          </div>
        `).join('')}
      </div>`;
    if (listEl) listEl.innerHTML = html;
  } catch (err) {
    if (err.name !== 'AbortError') {
      toast(`文件夹选择失败：${err.message}`, 'error');
    }
  }
}

async function scanDirectory(dirHandle, path) {
  for await (const entry of dirHandle.values()) {
    if (entry.kind === 'file') {
      const ext = entry.name.split('.').pop().toLowerCase();
      if (['docx', 'pdf', 'txt', 'html', 'htm'].includes(ext)) {
        const file = await entry.getFile();
        folderFilesCache.push({
          name: entry.name,
          type: ext,
          size: file.size,
          handle: entry,
          file: file,
        });
      }
    } else if (entry.kind === 'directory') {
      // 递归扫描子文件夹（最多一层）
      await scanDirectory(entry, path + entry.name + '/');
    }
  }
}

function toggleAllFolderFiles(checked) {
  document.querySelectorAll('.folder-file-check').forEach(cb => {
    if (!cb.disabled) cb.checked = checked;
  });
}

async function loadSelectedFolderFiles() {
  const checked = document.querySelectorAll('.folder-file-check:checked');
  if (checked.length === 0) {
    toast('请至少选择一个文件', 'info');
    return;
  }
  
  const labelInput = document.getElementById('folderLabelInput');
  const folderLabel = labelInput ? labelInput.value.trim() || '未分类' : '未分类';
  
  const filesToLoad = [];
  checked.forEach(cb => {
    const idx = parseInt(cb.dataset.index);
    if (folderFilesCache[idx]) {
      filesToLoad.push(folderFilesCache[idx].file);
    }
  });
  
  if (filesToLoad.length > 0) {
    const listEl = document.getElementById('localFileProgress');
    if (listEl) listEl.textContent = `正在加载 ${filesToLoad.length} 个文件到"${folderLabel}"...`;
    await handleLocalFiles(filesToLoad, folderLabel);
    folderFilesCache = [];
    const folderListEl = document.getElementById('folderFileList');
    if (folderListEl) folderListEl.innerHTML = '';
  }
}
function renderKbManager(container) {
  const searchTerm = (container.dataset.kbSearch || '').toLowerCase();
  const filterCat = container.dataset.kbFilter || '';
  let entries = state.kbEntries;
  if (searchTerm) entries = entries.filter(e => e.name.toLowerCase().includes(searchTerm) || e.content.toLowerCase().includes(searchTerm));
  if (filterCat) entries = entries.filter(e => e.category === filterCat);

  const statsHtml = KB_CATEGORIES.map(cat => {
    const count = state.kbEntries.filter(e => e.category === cat).length;
    return `<span class="kb-stat"><strong>${count}</strong> ${cat}</span>`;
  }).join('');

  const listHtml = entries.length === 0 ? `<div class="kb-empty">${state.kbEntries.length === 0 ? '知识库为空，点击下方按钮添加第一条知识' : '没有匹配的知识条目'}</div>` :
    entries.map(e => {
      const sel = state.selectedKbIds.includes(e.id);
      return `<div class="kb-item${sel ? ' selected' : ''}" onclick="toggleKbSelect('${e.id}')">
        <div class="kb-check">${sel ? '✓' : ''}</div>
        <div class="kb-info">
          <div class="kb-name"><span class="kb-tag kb-tag-${e.category}">${e.category}</span>${escapeHtml(e.name)}</div>
          <div class="kb-meta">${e.content.length} 字 · ${e.createdAt}</div>
        </div>
        <div class="kb-actions" onclick="event.stopPropagation()">
          <button class="btn btn-xs btn-outline" onclick="editKbEntry('${e.id}')">编辑</button>
          <button class="btn btn-xs btn-danger" onclick="deleteKbEntry('${e.id}')">删除</button>
        </div>
      </div>`;
    }).join('');

  const selectedCount = state.selectedKbIds.length;

  container.innerHTML = `
    <div class="card">
      <h2>知识库管理 <span class="badge badge-core">${state.kbEntries.length} 条</span></h2>
      <p style="color:#888;font-size:13px;margin-bottom:12px;">收集存放固定的政策法规、技术导则、审批原则等文件。研判时勾选需要的条目，AI会自动引用。</p>
      <div class="kb-stats">${statsHtml}</div>
      ${selectedCount > 0 ? `<div class="kb-select-bar">当前已勾选 <span class="count">${selectedCount}</span> 条知识，研判时将自动作为AI的参考依据。 <button class="btn btn-xs btn-outline" onclick="clearKbSelection()">取消全选</button></div>` : ''}
      <input type="text" class="kb-search" id="kbSearch" placeholder="搜索知识条目..." value="${escapeHtml(searchTerm)}" oninput="document.getElementById('mainContent').dataset.kbSearch=this.value;renderKbManager(document.getElementById('mainContent'))">
      <div style="margin-bottom:10px;display:flex;gap:6px;flex-wrap:wrap;">
        <button class="btn btn-xs ${filterCat === '' ? 'btn-primary' : 'btn-outline'}" onclick="document.getElementById('mainContent').dataset.kbFilter='';renderKbManager(document.getElementById('mainContent'))">全部</button>
        ${KB_CATEGORIES.map(cat => `<button class="btn btn-xs ${filterCat === cat ? 'btn-primary' : 'btn-outline'}" onclick="document.getElementById('mainContent').dataset.kbFilter='${cat}';renderKbManager(document.getElementById('mainContent'))">${cat}</button>`).join('')}
      </div>
      <div class="kb-list">${listHtml}</div>
      <div class="btn-group">
        <button class="btn btn-primary" onclick="showKbModal()">+ 添加知识</button>
        <button class="btn btn-outline" onclick="showBatchImport()">批量导入（TXT文件）</button>
        ${state.kbEntries.length > 0 ? '<button class="btn btn-outline btn-sm" onclick="exportKb()">导出知识库</button>' : ''}
        ${state.kbEntries.length > 0 ? '<button class="btn btn-outline btn-sm" onclick="importKbFile()">导入知识库</button>' : ''}
        ${state.kbEntries.length > 0 ? '<button class="btn btn-warning btn-sm" onclick="checkKbValidity()" style="background:#f39c12;color:#fff;border:none;">有效性检查</button>' : ''}
      </div>
    </div>
    <div class="card">
      <h2>当前选中知识预览</h2>
      <div class="result-box" style="max-height:300px;font-size:12px;color:#666;">${selectedCount > 0 ? escapeHtml(getSelectedKbContent()) : '尚未勾选任何知识条目。点击上方条目左侧勾选框选择。'}</div>
    </div>
  `;
}

function toggleKbSelect(id) {
  const idx = state.selectedKbIds.indexOf(id);
  if (idx >= 0) state.selectedKbIds.splice(idx, 1);
  else state.selectedKbIds.push(id);
  saveState();
  renderKbManager(document.getElementById('mainContent'));
}

function clearKbSelection() { state.selectedKbIds = []; saveState(); renderKbManager(document.getElementById('mainContent')); }

function showKbModal(editId) {
  const entry = editId ? state.kbEntries.find(e => e.id === editId) : null;
  const modal = document.getElementById('modalContainer');
  modal.innerHTML = `
    <div class="modal-overlay" onclick="if(event.target===this)closeModal()">
      <div class="modal">
        <button class="close" onclick="closeModal()">&times;</button>
        <h3>${entry ? '编辑知识条目' : '添加知识条目'}</h3>
        <div class="form-group">
          <label>名称</label>
          <input type="text" id="kbName" placeholder="例如：《建设项目环境影响评价分类管理名录》（2021年版）" value="${escapeHtml(entry ? entry.name : '')}">
        </div>
        <div class="form-group">
          <label>分类</label>
          <select id="kbCategory">${KB_CATEGORIES.map(c => `<option value="${c}" ${entry && entry.category === c ? 'selected' : ''}>${c}</option>`).join('')}</select>
        </div>
        <div class="form-group">
          <label>内容</label>
          <textarea id="kbContent" style="min-height:200px;" placeholder="粘贴政策法规、技术导则等文件的完整或关键内容...">${escapeHtml(entry ? entry.content : '')}</textarea>
        </div>
        <div class="btn-group">
          <button class="btn btn-primary" onclick="saveKbEntry('${editId || ''}')">保存</button>
          <button class="btn btn-outline" onclick="closeModal()">取消</button>
        </div>
      </div>
    </div>`;
}

function closeModal() { document.getElementById('modalContainer').innerHTML = ''; }

function saveKbEntry(editId) {
  const name = document.getElementById('kbName').value.trim();
  const category = document.getElementById('kbCategory').value;
  const content = document.getElementById('kbContent').value.trim();
  if (!name) { toast('请输入知识条目名称', 'error'); return; }
  if (!content) { toast('请输入知识条目内容', 'error'); return; }
  if (editId) {
    const idx = state.kbEntries.findIndex(e => e.id === editId);
    if (idx >= 0) { state.kbEntries[idx].name = name; state.kbEntries[idx].category = category; state.kbEntries[idx].content = content; }
  } else {
    state.kbEntries.push({ id: Date.now().toString(36) + Math.random().toString(36).slice(2, 6), name, category, content, createdAt: new Date().toLocaleDateString('zh-CN') });
  }
  saveState();
  closeModal();
  renderKbManager(document.getElementById('mainContent'));
  toast('知识条目已保存', 'success');
}

function editKbEntry(id) { showKbModal(id); }

function deleteKbEntry(id) {
  if (!confirm('确定要删除这条知识吗？此操作不可恢复。')) return;
  state.kbEntries = state.kbEntries.filter(e => e.id !== id);
  state.selectedKbIds = state.selectedKbIds.filter(i => i !== id);
  saveState();
  renderKbManager(document.getElementById('mainContent'));
  toast('已删除', 'info');
}

function showBatchImport() {
  const modal = document.getElementById('modalContainer');
  modal.innerHTML = `
    <div class="modal-overlay" onclick="if(event.target===this)closeModal()">
      <div class="modal">
        <button class="close" onclick="closeModal()">&times;</button>
        <h3>批量导入TXT文件</h3>
        <p style="color:#888;font-size:13px;margin-bottom:12px;">选择多个TXT文件，每个文件将作为一条知识条目导入。文件名作为条目名称，文件内容作为条目内容。</p>
        <div class="form-group">
          <label>分类</label>
          <select id="batchCategory">${KB_CATEGORIES.map(c => `<option value="${c}">${c}</option>`).join('')}</select>
        </div>
        <div class="file-drop-zone" id="dropZone" onclick="document.getElementById('batchFileInput').click()">
          <p>点击选择TXT文件，或拖拽文件到此处</p>
          <input type="file" id="batchFileInput" multiple accept=".txt" onchange="handleBatchFiles(this.files)">
        </div>
        <div id="batchFileList" style="font-size:12px;max-height:200px;overflow-y:auto;"></div>
        <div class="btn-group" style="margin-top:12px;">
          <button class="btn btn-primary" id="btnBatchImport" disabled onclick="doBatchImport()">导入</button>
          <button class="btn btn-outline" onclick="closeModal()">取消</button>
        </div>
      </div>
    </div>`;
  
  // Drag & drop
  const dropZone = document.getElementById('dropZone');
  dropZone.addEventListener('dragover', e => { e.preventDefault(); dropZone.classList.add('dragover'); });
  dropZone.addEventListener('dragleave', () => dropZone.classList.remove('dragover'));
  dropZone.addEventListener('drop', e => { e.preventDefault(); dropZone.classList.remove('dragover'); handleBatchFiles(e.dataTransfer.files); });
}

let batchFilesData = [];
function handleBatchFiles(files) {
  batchFilesData = [];
  const list = document.getElementById('batchFileList');
  const btn = document.getElementById('btnBatchImport');
  if (!files || files.length === 0) { list.innerHTML = ''; btn.disabled = true; return; }
  
  let loaded = 0;
  Array.from(files).forEach(file => {
    const reader = new FileReader();
    reader.onload = function(e) {
      batchFilesData.push({ name: file.name.replace(/\.txt$/i, ''), content: e.target.result });
      loaded++;
      if (loaded === files.length) {
        list.innerHTML = batchFilesData.map(f => `<div style="padding:4px 0;">${escapeHtml(f.name)} (${f.content.length} 字)</div>`).join('');
        btn.disabled = false;
      }
    };
    reader.readAsText(file, 'UTF-8');
  });
}

function doBatchImport() {
  const cat = document.getElementById('batchCategory').value;
  batchFilesData.forEach(f => {
    state.kbEntries.push({ id: Date.now().toString(36) + Math.random().toString(36).slice(2, 6), name: f.name, category: cat, content: f.content, createdAt: new Date().toLocaleDateString('zh-CN') });
  });
  saveState();
  closeModal();
  renderKbManager(document.getElementById('mainContent'));
  toast(`已导入 ${batchFilesData.length} 条知识`, 'success');
}

function exportKb() {
  const data = JSON.stringify(state.kbEntries, null, 2);
  const blob = new Blob([data], { type: 'application/json;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a'); a.href = url; a.download = `环评知识库_${new Date().toISOString().slice(0,10)}.json`; a.click();
  URL.revokeObjectURL(url);
  toast('知识库已导出', 'success');
}

function importKbFile() {
  const input = document.createElement('input'); input.type = 'file'; input.accept = '.json';
  input.onchange = function(e) {
    const file = e.target.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = function(ev) {
      try {
        const data = JSON.parse(ev.target.result);
        if (!Array.isArray(data)) { toast('文件格式不正确', 'error'); return; }
        const existingIds = new Set(state.kbEntries.map(e => e.id));
        let added = 0;
        data.forEach(item => {
          if (!existingIds.has(item.id)) { state.kbEntries.push(item); added++; }
        });
        saveState();
        renderKbManager(document.getElementById('mainContent'));
        toast(`已导入 ${added} 条新知识（跳过 ${data.length - added} 条重复）`, 'success');
      } catch (err) { toast('文件解析失败', 'error'); }
    };
    reader.readAsText(file);
  };
  input.click();
}

// ============ WEB SEARCH PANEL ============
function renderSearchPanel(container) {
  const hasSearchContext = !!state.searchContext;
  const results = state.searchResults;
  
  let resultsHtml = '';
  if (results && results.length > 0) {
    resultsHtml = `<div class="kb-list" style="margin-top:12px;">${results.map((r, i) => {
      const isSelected = state.searchContext && state.searchContext.includes(r.snippet || r.content || '');
      return `<div class="kb-item${isSelected ? ' selected' : ''}" style="cursor:pointer;" onclick="toggleSearchResult(${i})">
        <div class="kb-check">${isSelected ? '✓' : ''}</div>
        <div class="kb-info">
          <div class="kb-name">${escapeHtml(r.title || '无标题')}</div>
          <div class="kb-meta">${escapeHtml((r.snippet || r.content || '').substring(0, 200))}...</div>
          ${r.url ? `<div class="kb-meta" style="color:var(--primary-light);">${escapeHtml(r.url)}</div>` : ''}
        </div>
      </div>`;
    }).join('')}</div>`;
  }

  container.innerHTML = `
    <div class="card">
      <h2>联网检索 <span class="badge badge-new">后端Agent</span></h2>
      <p style="color:#888;font-size:13px;margin-bottom:12px;">在研判过程中遇到模棱两可、依据不足或文件有效性存疑时，可在此单独检索官方回复、政策解读、规划环评、审批原则和同类项目资料。检索结果进入候选依据库，人工审核后才能作为正式依据使用。</p>
      <div class="kb-select-bar" style="background:#eef7ff;border-color:#bbdefb;">前端不再配置搜索 API，也不限定检索词。后端 Hermes Agent 会根据问题自行组织关键词和来源优先级，并记录真实 URL。</div>
      <div style="display:flex;align-items:center;gap:12px;margin-bottom:12px;padding:10px 14px;background:#f0f7ff;border:1px solid #bbdefb;border-radius:6px;">
        <label style="display:flex;align-items:center;gap:8px;cursor:pointer;font-size:13px;font-weight:600;">
          <input type="checkbox" id="autoSearchToggle" ${state.autoSearch ? 'checked' : ''} onchange="toggleAutoSearch(this.checked)" style="width:18px;height:18px;">
          节点内自主联网检索
        </label>
        <span style="font-size:12px;color:#888;">开启表示允许后端节点运行时自主检索；本页用于手动发起独立检索。</span>
      </div>
      ${hasSearchContext ? `<div class="kb-select-bar">当前已有检索摘要。正式用于研判前，请在知识库管理中审核候选依据。 <button class="btn btn-xs btn-outline" onclick="clearSearchContext()">清除摘要</button></div>` : ''}
      <div style="display:flex;gap:10px;align-items:flex-end;">
        <div class="form-group" style="flex:1;margin-bottom:0;">
          <label>检索问题</label>
          <div class="hint">可直接写自然语言问题，例如“水性涂料项目环评类别和审批原则有哪些官方依据”。</div>
          <input type="text" id="searchQuery" placeholder="例如：水性涂料项目环评类别和审批原则官方依据" onkeydown="if(event.key==='Enter')doSearch()">
        </div>
        <div class="form-group" style="flex:0;margin-bottom:0;">
          <label>&nbsp;</label>
          <button class="btn btn-primary" id="btnSearch" onclick="doSearch()">后端检索</button>
        </div>
      </div>
      <div style="margin-top:8px;font-size:11px;color:#888;">
        快捷搜索：
        <button class="btn btn-xs btn-outline" onclick="quickSearch('行业类别')">行业类别判定</button>
        <button class="btn btn-xs btn-outline" onclick="quickSearch('环评类别')">环评类别判定</button>
        <button class="btn btn-xs btn-outline" onclick="quickSearch('审批权限')">审批权限</button>
        <button class="btn btn-xs btn-outline" onclick="quickSearch('政策有效性')">政策有效性</button>
      </div>
      ${resultsHtml}
      ${results && results.length === 0 ? `<div class="kb-empty" style="margin-top:12px;">未找到相关结果，请尝试更换关键词</div>` : ''}
      ${results && results.length > 0 ? `<div class="btn-group" style="margin-top:12px;"><button class="btn btn-success" onclick="injectSearchToAnalysis()">查看候选依据审核</button></div>` : ''}
    </div>
    <div class="card">
      <h2>检索结果预览</h2>
      <div class="word-view" style="max-height:360px;overflow:auto;">${hasSearchContext ? renderMarkdownBody(state.searchContext) : '<p style="color:#999;">尚未发起独立检索。</p>'}</div>
    </div>
    <div class="card">
      <h2>后端事件</h2>
	      <div class="result-box" id="eventLog" data-autoscroll-key="eventLog" style="max-height:260px;">${renderEventLogHtml()}</div>
    </div>
  `;
  setTimeout(bindAutoScrollContainers, 0);
}

function toggleAutoSearch(val) {
  state.autoSearch = val;
  saveState();
  toast(val ? '自动联网检索已开启' : '自动联网检索已关闭', 'info');
}

// 根据模块代码和项目信息智能生成搜索关键词
function generateAutoSearchQuery(code) {
  const projectOverview = state.results['HB-PT-001'] || state.projectInfo || '';
  // 提取项目关键信息（取前200字作为行业关键词来源）
  const shortInfo = projectOverview.substring(0, 200);
  
  const queries = {
    'HB-PT-002': `${shortInfo} 行业类别 国民经济行业分类 环评类别 生态环境部 回复`,
    'HB-PT-003': `${shortInfo} 产业结构调整指导目录 产业政策 行业准入 发改委`,
    'HB-PT-004': `${shortInfo} 规划环评 园区规划 符合性`,
    'HB-PT-005': `${shortInfo} 三线一单 生态环境分区管控 环境管控单元`,
    'HB-PT-006': `${shortInfo} 长江保护法 岸线管控 长江经济带`,
    'HB-PT-007': `${shortInfo} 两高项目 化工项目 环保管理要求`,
    'HB-PT-008': `${shortInfo} 环评审批原则 行业准入条件`,
    'HB-PT-009': `${shortInfo} 污染节点 治理措施 同类项目`,
  };
  
  return queries[code] || `${shortInfo} 环评 政策 回复`;
}

// 核心：自动执行搜索，返回搜索结果文本
async function autoSearch(code) {
  if (!state.autoSearch) return null;
  if (!state.searchApiUrl) return null;
  
  const query = generateAutoSearchQuery(code);
  if (!query) return null;
  
  try {
    let url = state.searchApiUrl;
    if (url.includes('{query}')) {
      url = url.replace('{query}', encodeURIComponent(query));
    } else {
      url += encodeURIComponent(query);
    }
    
    const headers = { 'Accept': 'application/json' };
    if (state.searchApiKey) {
      headers['Authorization'] = `Bearer ${state.searchApiKey}`;
      headers['X-API-Key'] = state.searchApiKey;
    }

    const response = await fetch(url, { headers });
    if (!response.ok) return null;
    
    const data = await response.json();
    const results = parseSearchResults(data);
    if (results.length === 0) return null;
    
    // 取前5条结果，构造上下文
    const context = results.slice(0, 5).map(r => 
      `【来源】${r.title}\n【链接】${r.url || '无'}\n【内容】${r.snippet || r.content || ''}`
    ).join('\n\n---\n\n');
    
    return { query, context, count: results.length };
  } catch (err) {
    return null;
  }
}

function quickSearch(topic) {
  const input = document.getElementById('searchQuery');
  if (input) {
    input.value = topic + ' ' + (state.projectInfo ? state.projectInfo.substring(0, 50) : '');
    doSearch();
  }
}

async function doSearch() {
  const query = document.getElementById('searchQuery')?.value.trim();
  if (!query) { toast('请输入搜索关键词', 'error'); return; }
  
  const btn = document.getElementById('btnSearch');
  if (btn) { btn.disabled = true; btn.textContent = '检索中...'; }
  
  try {
    const data = await apiFetch('/api/search', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query, task_id: state.taskId || undefined, purpose: 'manual_search' }),
    });
    const structuredResults = data.result?.structured?.results || [];
    const evidenceResults = (data.result?.evidence_refs || []).map(ref => ({
      title: ref.title || ref.source_url || '候选依据',
      url: ref.source_url || '',
      snippet: ref.quote || ref.confidence || '',
      content: ref.quote || ref.confidence || '',
    }));
    state.searchResults = (structuredResults.length ? structuredResults : evidenceResults).map(r => ({
      title: r.title || r.name || r.url || '候选依据',
      url: r.url || r.source_url || r.link || '',
      snippet: r.snippet || r.summary || r.relevance || r.suggested_use || '',
      content: r.snippet || r.summary || r.relevance || r.suggested_use || '',
    }));
    state.searchContext = data.result?.markdown || '';
    if (data.documents && data.documents.length) {
      state.knowledgeDocuments = data.documents;
    }
    saveState();
    renderSearchPanel(document.getElementById('mainContent'));
    await refreshAdminData({ rerender: false }).catch(() => {});
    
    if (state.searchResults.length === 0) {
      toast('检索完成，但未抽取到结构化候选 URL，请查看检索摘要', 'info');
    } else {
      toast(`检索完成：发现 ${state.searchResults.length} 条候选结果`, 'success');
    }
  } catch (err) {
    toast(`检索失败：${err.message}`, 'error');
  } finally {
    if (btn) { btn.disabled = false; btn.textContent = '后端检索'; }
  }
}

function parseSearchResults(data) {
  // Try multiple common response formats
  let results = [];
  
  // SearXNG format
  if (data.results && Array.isArray(data.results)) {
    results = data.results.map(r => ({
      title: r.title || '',
      url: r.url || '',
      snippet: r.content || r.snippet || '',
      content: r.content || r.snippet || '',
    }));
  }
  // SerpAPI / Google format
  else if (data.organic_results && Array.isArray(data.organic_results)) {
    results = data.organic_results.map(r => ({
      title: r.title || '',
      url: r.link || r.url || '',
      snippet: r.snippet || '',
      content: r.snippet || '',
    }));
  }
  // SearchApi format
  else if (data.organic_results && Array.isArray(data.organic_results)) {
    results = data.organic_results.map(r => ({
      title: r.title || '',
      url: r.link || '',
      snippet: r.snippet || r.description || '',
      content: r.snippet || r.description || '',
    }));
  }
  // DuckDuckGo format
  else if (data.RelatedTopics && Array.isArray(data.RelatedTopics)) {
    results = data.RelatedTopics.filter(r => r.Text).map(r => ({
      title: r.Text.substring(0, 80),
      url: r.FirstURL || '',
      snippet: r.Text || '',
      content: r.Text || '',
    }));
  }
  // Generic: try to find any array of results
  else {
    for (const key of Object.keys(data)) {
      if (Array.isArray(data[key]) && data[key].length > 0 && data[key][0].title) {
        results = data[key].map(r => ({
          title: r.title || r.name || '',
          url: r.url || r.link || r.href || '',
          snippet: r.snippet || r.description || r.content || r.summary || '',
          content: r.snippet || r.description || r.content || r.summary || '',
        }));
        break;
      }
    }
  }
  
  return results.slice(0, 20);
}

function toggleSearchResult(index) {
  if (!state.searchResults || !state.searchResults[index]) return;
  const r = state.searchResults[index];
  const text = `【来源】${r.title}\n【链接】${r.url || '无'}\n【内容】${r.snippet || r.content || ''}`;
  
  if (state.searchContext && state.searchContext.includes(r.snippet || r.content || '')) {
    // Remove this result
    state.searchContext = state.searchContext.replace(
      new RegExp(`【来源】${escapeRegex(r.title)}[\\s\\S]*?(?=【来源】|$)`, 'g'), ''
    ).trim();
  } else {
    // Add this result
    state.searchContext = (state.searchContext ? state.searchContext + '\n\n---\n\n' : '') + text;
  }
  saveState();
  renderSearchPanel(document.getElementById('mainContent'));
}

function injectSearchToAnalysis() {
  switchStep(-4);
  toast('请在知识库管理中审核候选依据，确认后加入本任务', 'info');
}

function clearSearchContext() {
  state.searchContext = '';
  state.searchResults = null;
  saveState();
  renderSearchPanel(document.getElementById('mainContent'));
  toast('已清除检索上下文', 'info');
}

function escapeRegex(str) {
  return (str || '').replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

// ============ KB VALIDITY CHECKER ============
async function checkKbValidity() {
  toast('知识库有效性检查已迁移到后端 Agent/知识库流程', 'info');
  return;
  if (!state.apiKey) { toast('请先在"API配置"中设置AI模型API Key', 'error'); switchStep(0); return; }
  const entries = state.kbEntries;
  if (entries.length === 0) { toast('知识库为空，无需检查', 'info'); return; }
  
  const modal = document.getElementById('modalContainer');
  modal.innerHTML = `
    <div class="modal-overlay">
      <div class="modal" style="max-width:800px;">
        <button class="close" onclick="closeModal()">&times;</button>
        <h3>知识库有效性检查</h3>
        <p style="color:#888;font-size:13px;margin-bottom:12px;">正在逐条检查知识库中的文件是否废止、失效或被替代，请稍候...</p>
        <div id="validityProgress" style="max-height:400px;overflow-y:auto;font-size:12px;"></div>
        <div class="btn-group" style="margin-top:12px;">
          <button class="btn btn-primary" id="btnApplyValidity" onclick="applyValidityResults()" disabled>应用检查结果</button>
          <button class="btn btn-outline" onclick="closeModal()">关闭</button>
        </div>
      </div>
    </div>`;
  
  const progressEl = document.getElementById('validityProgress');
  const results = {};
  let total = entries.length;
  let done = 0;
  
  for (let i = 0; i < entries.length; i++) {
    const entry = entries[i];
    progressEl.innerHTML += `<div style="padding:4px 0;color:#888;">正在检查 (${i+1}/${total})：${escapeHtml(entry.name)}...</div>`;
    progressEl.scrollTop = progressEl.scrollHeight;
    
    try {
      const prompt = `请检查以下政策文件/技术规范是否仍然现行有效，分析其废止、失效或被替代的风险。

文件名称：${entry.name}
文件分类：${entry.category}
文件内容摘要：${entry.content.substring(0, 2000)}

请按以下格式回复（简洁，每项一行）：
状态：{现行有效/疑似废止/已废止/已被替代/部分条款失效/无法判断}
文件名称：{文件全称}
文号：{从内容中提取，如无则填"未提及"}
废止/替代文件：{如有，填写替代文件名称；如无则填"无"}
风险等级：{高/中/低/无}
建议：{一句话建议}

注意：仅基于你已知的信息判断，如无法确认请标注"无法判断"，不要编造信息。`;

      const response = await callDeepSeek(SYSTEM_PROMPT, prompt);
      results[entry.id] = {
        checkedAt: new Date().toLocaleString('zh-CN'),
        name: entry.name,
        result: response,
      };
      
      // Extract status for display
      let statusMatch = response.match(/状态[：:]\s*(.+)/);
      let status = statusMatch ? statusMatch[1].trim() : '无法判断';
      let color = status.includes('有效') ? '#27ae60' : status.includes('废止') || status.includes('替代') ? '#e74c3c' : status.includes('疑似') ? '#f39c12' : '#888';
      
      progressEl.innerHTML = progressEl.innerHTML.replace(
        `正在检查 (${i+1}/${total})：${escapeHtml(entry.name)}...</div>`,
        `</div><div style="padding:4px 0;">${i+1}/${total}：${escapeHtml(entry.name)} — <span style="color:${color};font-weight:600;">${status}</span></div>`
      );
    } catch (err) {
      results[entry.id] = { checkedAt: new Date().toLocaleString('zh-CN'), name: entry.name, result: `检查失败：${err.message}`, error: true };
      progressEl.innerHTML = progressEl.innerHTML.replace(
        `正在检查 (${i+1}/${total})：${escapeHtml(entry.name)}...</div>`,
        `</div><div style="padding:4px 0;color:#e74c3c;">${i+1}/${total}：${escapeHtml(entry.name)} — 检查失败</div>`
      );
    }
    
    done++;
    // Avoid rate limiting
    if (i < entries.length - 1) await new Promise(r => setTimeout(r, 500));
  }
  
  state.kbValidityResults = results;
  saveState();
  progressEl.innerHTML += `<div style="padding:8px 0;color:#27ae60;font-weight:600;margin-top:8px;">检查完成！共检查 ${total} 条，结果已暂存。点击"应用检查结果"将更新知识库标记。</div>`;
  document.getElementById('btnApplyValidity').disabled = false;
}

function applyValidityResults() {
  const results = state.kbValidityResults;
  if (!results || Object.keys(results).length === 0) { toast('没有可应用的检查结果', 'info'); return; }
  
  let updated = 0;
  state.kbEntries = state.kbEntries.map(entry => {
    const check = results[entry.id];
    if (!check || check.error) return entry;
    
    const response = check.result;
    let statusMatch = response.match(/状态[：:]\s*(.+)/);
    let status = statusMatch ? statusMatch[1].trim() : '';
    
    if (status && !status.includes('有效') && !status.includes('无法判断')) {
      // Add validity warning to the entry name
      if (!entry.name.includes('【')) {
        entry.name = entry.name + ` 【${status}】`;
      }
      updated++;
    }
    
    // Add validity check result to content
    if (!entry.content.includes('【有效性检查】')) {
      entry.content += `\n\n【有效性检查 - ${check.checkedAt}】\n${response}`;
    }
    
    return entry;
  });
  
  saveState();
  closeModal();
  renderKbManager(document.getElementById('mainContent'));
  toast(`已更新 ${updated} 条知识条目的有效性标记`, 'success');
}
function renderApiConfig(container) {
  const taskActions = state.taskId ? `
      <div class="btn-group" style="margin-top:12px;">
        <button class="btn btn-outline btn-sm" onclick="refreshTask({ rerender: true }).then(() => toast('任务状态已刷新', 'success')).catch(err => toast(err.message, 'error'))">刷新任务</button>
        <button class="btn btn-outline btn-sm" onclick="openTaskManifest()">查看 Manifest</button>
        <button class="btn btn-outline btn-sm" onclick="exportReport()">下载报告 MD</button>
        <button class="btn btn-outline btn-sm" onclick="exportArchive()">下载归档 ZIP</button>
      </div>` : '';
  container.innerHTML = `
    <div class="card">
      <h2>后端连接与任务状态</h2>
      <div class="api-config">
        <div class="form-group"><label>后端地址</label><input type="text" id="backendBase" value="${escapeHtml(state.backendBase)}" placeholder="http://127.0.0.1:8501"></div>
        <div class="form-group" style="flex:0;"><label>&nbsp;</label><button class="btn btn-primary" onclick="testBackendConnection().catch(err => toast(err.message, 'error'))">测试连接</button></div>
        <div class="form-group" style="flex:0;"><label>&nbsp;</label><button class="btn btn-outline" onclick="resetBackendTask()">清空任务绑定</button></div>
      </div>
      <div style="margin-top:12px;font-size:12px;color:#666;line-height:1.7;">
        当前任务：${state.taskId ? `<code>${escapeHtml(state.taskId)}</code>` : '未创建'}<br>
        任务状态：${escapeHtml(state.taskStatus || '未开始')}；下一节点：${escapeHtml(state.nextNode || '无')}
      </div>
      ${taskActions}
    </div>
    <div class="card">
      <h2>后端事件</h2>
	      <div class="result-box" id="eventLog" data-autoscroll-key="eventLog" style="max-height:360px;">${renderEventLogHtml()}</div>
	    </div>
	  `;
	  setTimeout(bindAutoScrollContainers, 0);
	}

function renderProjectInput(container) {
  const hasSearchContext = !!state.searchContext;
  const localFileCount = state.localFiles.length;
  const uploadCount = state.projectUploadFiles?.length || 0;
  const prepCode = 'PREP-INGEST';
  const prepResult = state.results[prepCode] || '';
  const prepLiveText = state.liveOutput[prepCode] || '';
  const validationCode = 'FILE-VALIDATION';
  const validationResult = state.results[validationCode] || '';
  container.innerHTML = `
    <div class="card">
      <h2>项目信息输入</h2>
      <div class="kb-select-bar" style="background:#eef7ff;border-color:#bbdefb;">
        后端任务：${state.taskId ? `<code>${escapeHtml(state.taskId)}</code>` : '未初始化'}；状态：${escapeHtml(state.taskStatus || '未开始')}；下一节点：${escapeHtml(state.nextNode || 'PREP-INGEST')}
      </div>
      ${localFileCount > 0 ? `<div class="kb-select-bar" style="background:#e0f2f1;border-color:#80cbc4;">参考资料库已加载 <span class="count" style="color:#00695c;">${localFileCount}</span> 个条目。当前版本由后端 Agent 自主读取任务资料，参考资料库后续接入政策库。</div>` : `<div style="margin-bottom:12px;font-size:12px;color:var(--text-muted);">提示：项目简介可直接粘贴自然语言文本，不要求固定格式；PDF/Word/TXT/图片可上传，正式读取和归纳由后端 Agent 在 PREP-INGEST 节点完成。</div>`}
      ${hasSearchContext ? `<div class="kb-select-bar" style="background:#fff8e1;border-color:#ffe082;">当前已从联网检索注入参考内容。 <a href="javascript:void(0)" onclick="switchStep(-2)" style="color:var(--primary-light);">管理检索结果</a></div>` : ''}
      <div class="form-group">
        <label>项目原始材料</label>
        <div class="hint">可直接粘贴文本，也可以上传文件。浏览器只负责提交原始资料；PDF、扫描件、图片、Word 的正式读取由后端 Agent 完成。</div>
        <div class="file-drop-zone" id="projectFileDropZone" onclick="document.getElementById('projectFileInput').click()" style="padding:16px;">
          <p>点击上传项目文件，或拖拽文件到此处</p>
          <p style="font-size:11px;color:#999;">支持格式：.pdf / .docx / .txt / .html / 图片；已选择 ${uploadCount} 个原始文件</p>
          <input type="file" id="projectFileInput" multiple accept=".pdf,.docx,.txt,.html,.htm,.png,.jpg,.jpeg,.webp" onchange="handleProjectUploads(this.files)" style="display:none;">
        </div>
        <div id="projectFileProgress" style="font-size:12px;margin:4px 0;"></div>
        <textarea id="projectInfo" placeholder="可粘贴项目备案证、可研报告、项目简介等原始文本；上传文件不会自动填充到这里。">${escapeHtml(state.projectInfo)}</textarea>
      </div>
      <div class="form-group">
        <label>临时补充材料（可选）</label>
        <div class="hint">此处粘贴的内容仅本次项目使用，不会存入知识库。如需长期保存，请添加到知识库。</div>
        <textarea id="knowledgeBase" placeholder="粘贴本次项目特有的补充材料...">${escapeHtml(state.knowledgeBase)}</textarea>
      </div>
      <div class="btn-group">
        <button class="btn btn-primary" onclick="saveProjectInfo()">保存并初始化任务</button>
        ${state.taskId ? '<button class="btn btn-outline" onclick="runFileValidation().catch(err => toast(err.message, \'error\'))">AI验证上传资料</button>' : ''}
        ${state.taskId && state.nextNode === 'PREP-INGEST' ? '<button class="btn btn-primary" onclick="runPrepIngest().catch(err => toast(err.message, \'error\'))">运行资料读取Agent</button>' : ''}
        ${state.taskId && state.taskStatus !== 'running' ? '<button class="btn btn-outline" onclick="runBackendAll().catch(err => toast(err.message, \'error\'))">一键分析全部流程</button>' : ''}
        ${state.taskStatus === 'running' ? '<button class="btn btn-outline" onclick="pauseBackendTask().catch(err => toast(err.message, \'error\'))">暂停</button>' : ''}
        ${state.taskId ? '<button class="btn btn-outline" onclick="refreshTask({ rerender: true }).then(() => toast(\'任务状态已刷新\', \'success\')).catch(err => toast(err.message, \'error\'))">刷新任务</button>' : ''}
        <button class="btn btn-outline" onclick="clearProjectInfo()">清空</button>
      </div>
      <div style="margin-top:14px;">
        <h3 style="font-size:14px;margin-bottom:8px;">上传资料有效性验证（FILE-VALIDATION）</h3>
	        ${validationResult ? renderResultBox(validationResult) : renderResultBox('', { placeholder: '初始化任务后可点击“AI验证上传资料”，检查文件可读性、项目相关性、政策有效性和可用于哪些研判模块', placeholderStyle: 'color:#bbb;text-align:center;padding:28px;' })}
	        ${state.taskId && validationResult ? `<div class="btn-group" style="margin-top:8px;"><button class="btn btn-outline btn-sm" onclick="downloadWordResult('${validationCode}')">下载Word</button><button class="btn btn-outline btn-sm" onclick="downloadNodeOutput('${validationCode}', 'md')">下载验证MD</button><button class="btn btn-outline btn-sm" onclick="downloadNodeOutput('${validationCode}', 'json')">下载JSON</button><button class="btn btn-outline btn-sm" onclick="downloadNodeOutput('${validationCode}', 'tool_trace.json')">工具轨迹</button></div>` : ''}
      </div>
      <div style="margin-top:14px;">
        <h3 style="font-size:14px;margin-bottom:8px;">项目档案（PREP-INGEST）</h3>
	        ${prepLiveText ? renderResultBox(prepLiveText, { loading: true }) : (prepResult ? renderResultBox(prepResult) : renderResultBox('', { placeholder: '初始化任务后运行资料读取 Agent，生成带来源索引的项目档案', placeholderStyle: 'color:#bbb;text-align:center;padding:32px;' }))}
	        ${state.taskId && prepResult ? `<div class="btn-group" style="margin-top:8px;"><button class="btn btn-outline btn-sm" onclick="downloadWordResult('${prepCode}')">下载Word</button><button class="btn btn-outline btn-sm" onclick="downloadNodeOutput('${prepCode}', 'md')">下载项目档案MD</button><button class="btn btn-outline btn-sm" onclick="downloadNodeOutput('${prepCode}', 'json')">下载JSON</button><button class="btn btn-outline btn-sm" onclick="downloadNodeOutput('${prepCode}', 'tool_trace.json')">工具轨迹</button></div>` : ''}
      </div>
    </div>
    <div class="card">
      <h2>后端事件</h2>
	      <div class="result-box" id="eventLog" data-autoscroll-key="eventLog" style="max-height:300px;">${renderEventLogHtml()}</div>
	    </div>
	  `;
	  setTimeout(bindAutoScrollContainers, 0);

  // Drag & drop for project files
  setTimeout(() => {
    const dropZone = document.getElementById('projectFileDropZone');
    if (dropZone) {
      dropZone.addEventListener('dragover', e => { e.preventDefault(); dropZone.classList.add('dragover'); });
      dropZone.addEventListener('dragleave', () => dropZone.classList.remove('dragover'));
      dropZone.addEventListener('drop', e => { e.preventDefault(); dropZone.classList.remove('dragover'); handleProjectUploads(e.dataTransfer.files); });
    }
  }, 0);
}

// ============ MODULE STEP ============
function renderModuleStep(container, moduleIndex) {
  const code = `HB-PT-${String(moduleIndex).padStart(3, '0')}`;
  const label = MODULE_LABELS[code] || code;
  const result = state.results[code] || '';
  const isNew = ['HB-PT-000', 'HB-PT-010', 'HB-PT-011'].includes(code);
  const selectedCount = state.localFiles.length;
  const hasSearchContext = !!state.searchContext;
  const localFileCount = state.localFiles.length;
  const implemented = BACKEND_IMPLEMENTED_NODES.includes(code);
  const autoSearchInfo = '<div class="kb-select-bar" style="background:#eef7ff;border-color:#bbdefb;">文档读取、图片识别和联网检索由后端 Hermes Agent 在节点内部自主执行；前端只负责提交任务、显示事件和结果。</div>';
  const liveText = state.liveOutput[code] || '';
  const hasSpecialtyResults = SPECIALTY_NODES.some(nodeId => Object.prototype.hasOwnProperty.call(state.results, nodeId));

  container.innerHTML = `
    <div class="card">
      <h2>${code} ${label} ${isNew ? '<span class="badge badge-new">核心模块</span>' : '<span class="badge badge-core">专项研判</span>'}</h2>
      ${localFileCount > 0 ? `<div class="kb-select-bar" style="background:#e0f2f1;border-color:#80cbc4;">参考资料库已加载 <span class="count" style="color:#00695c;">${localFileCount}</span> 个条目，内容将自动注入研判 <a href="javascript:void(0)" onclick="switchStep(-3)" style="color:var(--primary-light);">管理</a></div>` : ''}
      ${autoSearchInfo}
      ${!implemented ? `<div class="kb-select-bar" style="background:#fff0f0;border-color:#f5c6cb;color:#9f2d20;">${code} 目前还没有后端提示词和 Agent 节点，不能运行。请在后台管理查看节点接入状态。</div>` : ''}
      ${hasSearchContext ? `<div class="kb-select-bar" style="background:#fff8e1;border-color:#ffe082;">上次检索结果已保存在检索面板中，可随时查看。 <a href="javascript:void(0)" onclick="switchStep(-2)" style="color:var(--primary-light);">查看检索结果</a></div>` : ''}
      ${code === 'HB-PT-000' ? '<div style="margin-bottom:12px;font-size:12px;color:#888;">此模块基于 PREP-INGEST 生成的项目档案审查资料完整性，并给出建议启动的模块清单。</div>' : ''}
      ${code === 'HB-PT-010' ? '<div style="margin-bottom:12px;font-size:12px;color:#888;">此模块将各专项研判结果整合为完整的研判报告。请先完成HB-PT-001至HB-PT-009后再运行。</div>' : ''}
      ${code === 'HB-PT-011' ? '<div style="margin-bottom:12px;font-size:12px;color:#888;">此模块检查各模块输出之间的逻辑一致性，生成人工复核清单。建议在HB-PT-010完成后运行。</div>' : ''}
      ${code === 'HB-PT-002' || code === 'HB-PT-003' ? `<div style="margin-bottom:12px;font-size:12px;color:#e67e22;background:#fff8e1;padding:8px 12px;border-radius:6px;">提示：此模块容易遇到模棱两可的情况。后端 Agent 会根据节点目标自行组织检索并记录真实依据。</div>` : ''}
      ${code !== 'HB-PT-000' && code !== 'HB-PT-010' && code !== 'HB-PT-011' ? `<div class="form-group"><label>模块输入信息</label><div class="hint">后端节点默认读取 PREP-INGEST 项目档案和已完成模块输出；此处仅作为人工补充草稿。</div><textarea id="moduleInput" style="min-height:80px;">${escapeHtml(code === 'HB-PT-001' ? (state.results['PREP-INGEST'] || state.projectInfo) : (state.results['HB-PT-001'] || state.results['PREP-INGEST'] || state.projectInfo))}</textarea></div>` : ''}
      <div class="btn-group">
        <button class="btn btn-primary" id="btnRun" onclick="runModule('${code}')" ${implemented ? '' : 'disabled'}>${implemented ? '运行分析' : '未接入'}</button>
        ${implemented && state.taskStatus !== 'running' ? '<button class="btn btn-outline btn-sm" onclick="runBackendAll().catch(err => toast(err.message, \'error\'))">一键分析全部流程</button>' : ''}
        ${state.taskStatus === 'running' ? '<button class="btn btn-outline btn-sm" onclick="pauseBackendTask().catch(err => toast(err.message, \'error\'))">暂停</button>' : ''}
	        ${result ? '<button class="btn btn-outline btn-sm" onclick="copyResult(\'' + code + '\')">复制结果</button>' : ''}
	        ${result ? '<button class="btn btn-outline btn-sm" onclick="showFeedbackModal(\'' + code + '\')" style="color:#e67e22;">反馈修正</button>' : ''}
	        ${result ? '<button class="btn btn-outline btn-sm" onclick="clearResult(\'' + code + '\')">清除结果</button>' : ''}
	        ${result ? '<button class="btn btn-outline btn-sm" onclick="downloadWordResult(\'' + code + '\')">下载Word</button>' : ''}
	        ${state.taskId && result ? '<button class="btn btn-outline btn-sm" onclick="downloadNodeOutput(\'' + code + '\', \'md\')">下载MD</button>' : ''}
        ${state.taskId && result ? '<button class="btn btn-outline btn-sm" onclick="downloadNodeOutput(\'' + code + '\', \'json\')">下载JSON</button>' : ''}
        ${state.taskId && result ? '<button class="btn btn-outline btn-sm" onclick="downloadNodeOutput(\'' + code + '\', \'tool_trace.json\')">工具轨迹</button>' : ''}
        ${state.taskId && ['HB-PT-010', 'HB-PT-011'].includes(code) ? '<button class="btn btn-outline btn-sm" onclick="exportReport()">报告MD</button>' : ''}
      </div>
	      ${liveText ? renderResultBox(liveText, { loading: true }) : (result ? renderResultBox(result) : renderResultBox('', { placeholder: '点击"运行分析"启动后端 Agent 节点', placeholderStyle: 'color:#bbb;text-align:center;padding:40px;' }))}
      ${code === 'HB-PT-001' && result && state.taskStatus !== 'running' ? `
        <div style="margin-top:16px;padding:14px;background:#f0f7ff;border:1px solid #bbdefb;border-radius:8px;text-align:center;">
          <p style="font-size:13px;color:#1976d2;margin-bottom:10px;">${hasSpecialtyResults ? '项目概况已保留，可以清理旧专项结果并从 HB-PT-002 重新运行。' : '项目概况已提取完成，可以一键运行专项研判模块（HB-PT-002 ~ HB-PT-009）。'}</p>
          <button class="btn btn-primary" onclick="runSpecialModules().catch(err => toast(err.message, 'error'))" style="font-size:14px;padding:10px 28px;">${hasSpecialtyResults ? '重新一键运行全部专项研判' : '一键运行全部专项研判'}</button>
          <p style="font-size:11px;color:#888;margin-top:8px;">${hasSpecialtyResults ? '不会重新读取上传资料或提取项目概况；旧专项、综合报告和交叉核查结果会被清理。' : '完成后停在综合报告前，可逐个查看结果、反馈修正或继续生成报告。'}</p>
        </div>
      ` : ''}
      <div style="margin-top:14px;">
        <h3 style="font-size:14px;margin-bottom:8px;">节点依据记录</h3>
        <div class="result-box" style="max-height:220px;font-size:12px;">${renderEvidenceRefsHtml(code)}</div>
      </div>
    </div>
    <div class="card">
      <h2>后端事件</h2>
	      <div class="result-box" style="max-height:260px;font-size:12px;color:#666;" id="eventLog" data-autoscroll-key="eventLog">${renderEventLogHtml()}</div>
	    </div>
	  `;
	  setTimeout(bindAutoScrollContainers, 0);
	}

// ============ ACTIONS ============
function saveApiConfig() {
  toast('模型 API 配置由后端环境变量和 Hermes 服务管理', 'info');
}

function saveSearchApiConfig() {
  toast('联网检索由后端 Agent 自主执行，前端不再配置搜索 API', 'info');
}

async function saveProjectInfo() {
  const btn = window.event?.target || null;
  if (btn) { btn.disabled = true; btn.textContent = '正在初始化...'; }
  try {
    state.projectInfo = document.getElementById('projectInfo').value.trim();
    state.knowledgeBase = document.getElementById('knowledgeBase').value.trim();
    saveState();
    await createBackendTask();
    toast('原始资料已保存，后端任务已初始化；请先运行资料读取 Agent', 'success');
    switchStep(1);
  } catch (err) {
    toast(`初始化失败：${err.message}`, 'error');
  } finally {
    if (btn) { btn.disabled = false; btn.textContent = '保存并初始化任务'; }
  }
}

function clearProjectInfo() {
  state.projectInfo = ''; state.knowledgeBase = ''; state.results = {};
  state.projectUploadFiles = [];
  resetBackendTask();
  saveState(); switchStep(1); toast('已清空项目信息和所有研判结果', 'info');
}

async function handleProjectUploads(fileList) {
  if (!fileList || fileList.length === 0) return;
  const progressEl = document.getElementById('projectFileProgress');
  let added = 0;
  
  for (const file of Array.from(fileList)) {
    const ext = file.name.split('.').pop().toLowerCase();
    const supported = ['docx', 'pdf', 'txt', 'html', 'htm', 'png', 'jpg', 'jpeg', 'webp'];
    if (!supported.includes(ext)) {
      toast(`不支持的文件格式：${file.name}`, 'error');
      continue;
    }
    if (!state.projectUploadFiles.some(f => f.name === file.name && f.size === file.size && f.lastModified === file.lastModified)) {
      state.projectUploadFiles.push(file);
      added++;
    }
  }
  saveState();
  if (progressEl) progressEl.textContent = `已加入上传队列 ${state.projectUploadFiles.length} 个文件；正式读取将在 PREP-INGEST 节点由后端 Agent 完成。`;
  toast(added ? `已加入 ${added} 个原始资料文件` : '文件已在上传队列中', 'success');
  renderStep();
}

async function handleProjectFiles(fileList) {
  return handleProjectUploads(fileList);
}

function clearResult(code) { delete state.results[code]; saveState(); renderStep(); updateSidebar(); }
function copyResult(code) { const text = state.results[code] || ''; navigator.clipboard.writeText(text).then(() => toast('已复制到剪贴板', 'success')); }

async function runModule(code) {
  if (!BACKEND_IMPLEMENTED_NODES.includes(code)) {
    toast(`${code} 还没有接入后端 Agent 节点`, 'error');
    return;
  }
  const btn = document.getElementById('btnRun'); if (btn) { btn.disabled = true; btn.textContent = '分析中...'; }
  const resultBox = document.getElementById('resultBox');
  if (resultBox) setResultBoxMarkdown('正在启动后端 Agent 节点...', { loading: true });

  try {
    await runBackendStep(code);
    await refreshTask({ rerender: true });
    if (code === 'HB-PT-000') toast('资料审查完成', 'success');
    else toast(`${code} 已提交后端`, 'success');
  } catch (err) {
    if (resultBox) { resultBox.className = 'result-box error'; resultBox.textContent = `错误：${err.message}`; }
    toast(`分析失败：${err.message}`, 'error');
  } finally { if (btn) { btn.disabled = false; btn.textContent = '运行分析'; } }
}

async function runSpecialModules() {
  await ensureBackendTask();
  await refreshTask();
  if (!state.results['HB-PT-001']) {
    throw new Error('请先完成 HB-PT-001 项目概况提取');
  }
  const needsReset = state.nextNode !== 'HB-PT-002'
    || SPECIALTY_NODES.some(code => Object.prototype.hasOwnProperty.call(state.results, code));
  if (needsReset) {
    await apiFetch(`/api/tasks/${state.taskId}/rerun/HB-PT-002`, { method: 'POST' });
    await refreshTask();
  }
  connectTaskEvents(state.taskId);
  const response = await apiFetch(`/api/tasks/${state.taskId}/run-until`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ stop_after_node: 'HB-PT-009' }),
  });
  state.taskStatus = response.status;
  state.nextNode = response.next_node || '';
  saveState();
  renderStep();
  updateSidebar();
  toast(needsReset
    ? '已保留项目概况，并从 HB-PT-002 重新运行全部专项研判'
    : '已启动专项一键分析，完成后会停在综合报告前', 'success');
}

function showFeedbackModal(code) {
  const label = MODULE_LABELS[code] || code;
  const currentResult = state.results[code] || '';
  const modal = document.getElementById('modalContainer');
  modal.innerHTML = `
    <div class="modal-overlay">
      <div class="modal" style="max-width:640px;">
        <button class="close" onclick="closeModal()">&times;</button>
        <h3>反馈修正 — ${escapeHtml(code)} ${escapeHtml(label)}</h3>
        <p style="color:#888;font-size:13px;margin-bottom:8px;">请指出 AI 分析结果中的错误、缺漏或需要调整的结论。后端 Agent 会结合项目资料和真实依据重新核对。</p>
        <div style="background:#f8f9fa;padding:10px;border-radius:6px;margin-bottom:10px;max-height:140px;overflow-y:auto;font-size:12px;color:#666;">
          <b>当前分析结论摘要：</b><br>${escapeHtml(currentResult.substring(0, 500))}${currentResult.length > 500 ? '...' : ''}
        </div>
        <div class="form-group">
          <label>修正意见</label>
          <textarea id="feedbackInput" style="min-height:130px;" placeholder="例如：行业类别应按 C2641 涂料制造判断；环评类别不是报告表而是报告书；该政策已被新文件替代，请重新检索官方依据。"></textarea>
        </div>
        <div class="btn-group">
          <button class="btn btn-primary" onclick="submitFeedbackRevision('${code}')">根据反馈重新分析</button>
          <button class="btn btn-outline" onclick="analyzeFeedbackError('${code}')" style="color:#e74c3c;">分析错误原因</button>
          <button class="btn btn-outline" onclick="closeModal()">取消</button>
        </div>
      </div>
    </div>`;
}

async function submitFeedbackRevision(code) {
  const feedback = document.getElementById('feedbackInput')?.value.trim();
  if (!feedback) { toast('请输入修正意见', 'error'); return; }
  closeModal();
  const resultBox = document.getElementById('resultBox');
  if (resultBox) setResultBoxMarkdown('正在根据反馈重新分析...', { loading: true });
  connectTaskEvents(state.taskId);
  const result = await apiFetch(`/api/tasks/${state.taskId}/feedback/${code}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ feedback, action: 'revise' }),
  });
  if (result.status && result.status !== 'completed') {
    throw new Error(result.error || result.markdown || '反馈修正未完成，原节点结果已保留');
  }
  if (result.markdown) state.results[code] = result.markdown;
  state.nodeStatuses[code] = result.status || 'completed';
  state.nodeEvidenceRefs[code] = result.evidence_refs || [];
  saveState();
  await refreshTask({ rerender: true });
  toast('已根据反馈修正，受影响的下游节点已清理', 'success');
}

async function analyzeFeedbackError(code) {
  const feedback = document.getElementById('feedbackInput')?.value.trim();
  if (!feedback) { toast('请输入修正意见', 'error'); return; }
  closeModal();
  const resultBox = document.getElementById('resultBox');
  if (resultBox) setResultBoxMarkdown('正在分析错误原因...', { loading: true });
  connectTaskEvents(state.taskId);
  const result = await apiFetch(`/api/tasks/${state.taskId}/feedback/${code}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ feedback, action: 'analyze_error' }),
  });
  if (result.status && result.status !== 'completed') {
    throw new Error(result.error || result.markdown || '错误原因分析未完成');
  }
  if (result.markdown) {
    setResultBoxMarkdown(result.markdown);
    toast('错误原因分析完成，正式节点结果未被替换', 'success');
  }
}

function resetAll() {
  if (confirm('确定要重置所有数据吗？这将清除项目信息、研判结果和当前任务绑定。知识库和检索结果不会受影响。')) {
    state.apiKey = ''; state.apiBase = 'https://api.deepseek.com/v1'; state.model = 'deepseek-chat';
    state.projectInfo = ''; state.knowledgeBase = ''; state.extraFiles = { planning: '', threeLines: '', industryPrinciple: '', similarReport: '' };
    state.results = {}; state.currentStep = 0; state.selectedKbIds = [];
    state.searchContext = ''; state.searchResults = null;
    state.taskId = ''; state.taskStatus = ''; state.nextNode = ''; state.nodeStatuses = {}; state.nodeEvidenceRefs = {}; state.evidenceRefs = []; state.taskKnowledgeDocIds = []; state.selectedKnowledgeDocIds = []; state.eventLog = []; state.liveOutput = {}; state.projectUploadFiles = [];
    if (state.eventSource) state.eventSource.close();
    saveState(); renderStep(); updateSidebar(); toast('已重置（知识库、本地文件和检索结果保留）', 'info');
  }
}

function exportReport() {
  if (state.taskId) {
    downloadBackendFile(`/api/tasks/${state.taskId}/report.md`, `环评前期研判报告_${state.taskId}.md`);
    toast('正在下载后端报告', 'success');
    return;
  }
  const report = state.results['HB-PT-010'];
  if (!report) { toast('请先生成综合研判报告（HB-PT-010）', 'error'); return; }
  let fullText = '═══════════════════════════════════\n  环评前期研判报告（AI辅助生成）\n═══════════════════════════════════\n';
  fullText += `生成时间：${new Date().toLocaleString()}\n团队：环评研审先锋队 / 湖北君邦环境技术有限责任公司\n\n${report}\n\n---\n`;
  if (state.results['HB-PT-011']) fullText += '\n═══════════════════════════════════\n  交叉一致性核查报告\n═══════════════════════════════════\n\n' + state.results['HB-PT-011'];
  const blob = new Blob([fullText], { type: 'text/plain;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a'); a.href = url; a.download = `环评前期研判报告_${new Date().toISOString().slice(0,10)}.txt`; a.click();
  URL.revokeObjectURL(url); toast('报告已导出', 'success');
}

function exportArchive() {
  if (!state.taskId) { toast('请先初始化任务', 'error'); return; }
  downloadBackendFile(`/api/tasks/${state.taskId}/export.zip`, `环评前期研判归档_${state.taskId}.zip`);
  toast('正在下载任务归档', 'success');
}

function escapeHtml(str) { if (!str) return ''; return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;'); }

// ============ INIT ============
function init() {
  migrateOldKbEntries();
  renderStep();
  updateSidebar();
  if (state.taskId) {
    connectTaskEvents(state.taskId);
    refreshTask({ rerender: true }).catch(err => toast(`恢复任务失败：${err.message}`, 'error'));
  }
}
init();
