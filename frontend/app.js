/**
 * Meesho Reseller Intelligence — Executive Dashboard Frontend Application
 */

const STATE = {
  activeTab: 'tab-overview',
  activeSqlTab: 'sql-monthly',
  activeScenario: 'may',
  lastLogId: 0,
  pollTimer: null,
  isPipelineRunning: false,
  processData: null,
  autoScroll: true,
};

// Format currency in Indian Rupees
function formatINR(amount) {
  if (amount === undefined || amount === null || isNaN(amount)) return '₹0.00';
  return '₹' + Number(amount).toLocaleString('en-IN', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

// Format percentages
function formatPct(val) {
  if (val === 'new_revenue') return '+100.00% (New Baseline)';
  if (val === undefined || val === null || isNaN(val)) return '0.00%';
  const num = Number(val);
  return (num >= 0 ? '+' : '') + num.toFixed(2) + '%';
}

document.addEventListener('DOMContentLoaded', () => {
  initTabs();
  initActions();
  initMaskSandbox();
  startPolling();
  fetchProcessData();
});

/* ==========================================================================
   Tab Navigation Handling
   ========================================================================== */
function initTabs() {
  // Main Process Tabs
  const tabBtns = document.querySelectorAll('.tab-btn');
  tabBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      tabBtns.forEach(b => b.classList.remove('active'));
      document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));

      btn.classList.add('active');
      const targetId = btn.getAttribute('data-tab');
      const targetContent = document.getElementById(targetId);
      if (targetContent) {
        targetContent.classList.add('active');
        STATE.activeTab = targetId;
      }
    });
  });

  // SQL Query Subtabs
  const sqlBtns = document.querySelectorAll('.subtab-btn');
  sqlBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      sqlBtns.forEach(b => b.classList.remove('active'));
      document.querySelectorAll('.sql-tab-panel').forEach(p => p.classList.remove('active'));

      btn.classList.add('active');
      const targetId = btn.getAttribute('data-sqltab');
      const targetPanel = document.getElementById(targetId);
      if (targetPanel) {
        targetPanel.classList.add('active');
        STATE.activeSqlTab = targetId;
      }
    });
  });

  // Agent Scenario Toggles
  const scenarioBtns = document.querySelectorAll('.scenario-btn');
  scenarioBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      scenarioBtns.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      STATE.activeScenario = btn.getAttribute('data-scenario');
      renderAgentBoard();
    });
  });
}

/* ==========================================================================
   Button Actions & Event Listeners
   ========================================================================== */
function initActions() {
  // Run Full Pipeline
  document.getElementById('btn-run-all').addEventListener('click', () => {
    runPipeline({ regenerate: false });
  });

  // Regenerate Dataset & Run Pipeline
  document.getElementById('btn-regenerate').addEventListener('click', () => {
    runPipeline({ regenerate: true });
  });

  // Individual Step Triggers
  document.querySelectorAll('[data-step-trigger]').forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      const step = btn.getAttribute('data-step-trigger');
      runStep(step);
    });
  });

  // Clear Console
  document.getElementById('btn-clear-console').addEventListener('click', async () => {
    await fetch('/api/clear-logs', { method: 'POST' });
    document.getElementById('console-output').innerHTML = '';
    STATE.lastLogId = 0;
  });

  // Autoscroll toggle
  const autoscrollChk = document.getElementById('chk-autoscroll');
  autoscrollChk.addEventListener('change', () => {
    STATE.autoScroll = autoscrollChk.checked;
  });

  // Reseller Table Search
  const searchInput = document.getElementById('reseller-search-input');
  if (searchInput) {
    searchInput.addEventListener('input', (e) => {
      filterResellersTable(e.target.value.toLowerCase());
    });
  }

  // Copy Agent JSON
  document.getElementById('btn-copy-json').addEventListener('click', () => {
    const code = document.getElementById('agent-json-code').innerText;
    navigator.clipboard.writeText(code).then(() => {
      const btn = document.getElementById('btn-copy-json');
      const orig = btn.innerText;
      btn.innerText = 'Copied!';
      setTimeout(() => { btn.innerText = orig; }, 1500);
    });
  });
}

/* ==========================================================================
   API Calls & Pipeline Execution
   ========================================================================== */
async function runPipeline(options = {}) {
  try {
    const res = await fetch('/api/run', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(options),
    });
    const data = await res.json();
    if (res.ok) {
      appendLogMessage({
        time: new Date().toLocaleTimeString(),
        level: 'info',
        message: options.regenerate ? 'Initiated full pipeline with dataset regeneration...' : 'Initiated full pipeline run...',
      });
    } else {
      appendLogMessage({
        time: new Date().toLocaleTimeString(),
        level: 'warning',
        message: data.message || 'Pipeline run already active',
      });
    }
  } catch (err) {
    console.error('Failed to trigger pipeline run:', err);
  }
}

async function runStep(stepKey) {
  try {
    const res = await fetch('/api/run-step', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ step: stepKey }),
    });
    const data = await res.json();
    if (res.ok) {
      appendLogMessage({
        time: new Date().toLocaleTimeString(),
        level: 'info',
        message: `Step '${stepKey}' triggered manually.`,
      });
    }
  } catch (err) {
    console.error(`Failed to trigger step ${stepKey}:`, err);
  }
}

/* ==========================================================================
   Log Polling & Status Updates
   ========================================================================== */
function startPolling() {
  if (STATE.pollTimer) clearInterval(STATE.pollTimer);
  STATE.pollTimer = setInterval(pollServer, 900);
}

async function pollServer() {
  try {
    // 1. Fetch Pipeline Status
    const statusRes = await fetch('/api/status');
    if (statusRes.ok) {
      const statusData = await statusRes.json();
      updateStatusUI(statusData);
    }

    // 2. Fetch Incremental Logs
    const logsRes = await fetch(`/api/logs?since=${STATE.lastLogId}`);
    if (logsRes.ok) {
      const logsData = await logsRes.json();
      if (logsData.logs && logsData.logs.length > 0) {
        logsData.logs.forEach(log => {
          appendLogMessage(log);
          if (log.id > STATE.lastLogId) {
            STATE.lastLogId = log.id;
          }
        });
      }
    }
  } catch (err) {
    // Server might be busy or restarting
    console.debug('Polling error:', err);
  }
}

function updateStatusUI(status) {
  const pill = document.getElementById('system-status-pill');
  const text = document.getElementById('system-status-text');
  const dbBadge = document.getElementById('db-status-badge');
  const runTimeLabel = document.getElementById('pipeline-run-time');

  dbBadge.innerText = status.db_initialized ? 'Connected' : 'Uninitialized';
  dbBadge.className = status.db_initialized ? 'meta-val text-green' : 'meta-val text-amber';

  if (status.last_run_timestamp) {
    runTimeLabel.innerText = `Last Run: ${status.last_run_timestamp}`;
  }

  // Detect state transition from running to idle to refresh data
  if (STATE.isPipelineRunning && !status.is_running) {
    fetchProcessData();
  }
  STATE.isPipelineRunning = status.is_running;

  if (status.is_running) {
    pill.className = 'status-pill running';
    text.innerText = `Running (${status.current_step || 'Processing'})...`;
  } else {
    pill.className = 'status-pill';
    text.innerText = 'System Ready';
  }

  // Update Stepper Nodes
  if (status.step_statuses) {
    for (const [stepKey, stepInfo] of Object.entries(status.step_statuses)) {
      const nodeEl = document.getElementById(`node-${stepKey}`);
      const tagEl = document.getElementById(`tag-${stepKey}`);
      if (nodeEl && tagEl) {
        nodeEl.className = `step-node ${stepInfo.status}`;
        let tagText = stepInfo.status;
        if (stepInfo.duration) {
          tagText += ` (${stepInfo.duration}s)`;
        }
        tagEl.innerText = tagText;
      }
    }
  }
}

function appendLogMessage(log) {
  const consoleEl = document.getElementById('console-output');
  const row = document.createElement('div');
  row.className = `term-row ${log.level || 'info'}`;

  const timeSpan = document.createElement('span');
  timeSpan.className = 'term-time';
  timeSpan.innerText = `[${log.time || '00:00:00'}]`;

  const levelSpan = document.createElement('span');
  levelSpan.className = 'term-level';
  levelSpan.innerText = `[${(log.level || 'INFO').toUpperCase()}]`;

  const msgSpan = document.createElement('span');
  msgSpan.className = 'term-msg';
  msgSpan.innerText = log.message || '';

  row.appendChild(timeSpan);
  row.appendChild(levelSpan);
  row.appendChild(msgSpan);
  consoleEl.appendChild(row);

  if (STATE.autoScroll) {
    consoleEl.scrollTop = consoleEl.scrollHeight;
  }
}

/* ==========================================================================
   Data Fetching & Section Renderers
   ========================================================================== */
async function fetchProcessData() {
  try {
    const res = await fetch('/api/data');
    if (!res.ok) return;
    const data = await res.json();
    STATE.processData = data;

    renderOverviewMetrics(data);
    renderProcess1(data.process1_dataset);
    renderProcess2(data.process2_sql);
    renderProcess3(data.process3_growth);
    renderProcess4(data.process4_narrative);
    renderProcess5(data.process5_agent);
  } catch (err) {
    console.error('Failed to load process data:', err);
  }
}

/* 0. Overview Metrics */
function renderOverviewMetrics(data) {
  if (data.process1_dataset) {
    const p1 = data.process1_dataset;
    document.getElementById('metric-resellers-count').innerText = p1.total_resellers || 24;
    document.getElementById('metric-orders-count').innerText = p1.total_orders || 900;
  }
}

/* 1. Process 1: Dataset & SQLite */
function renderProcess1(p1) {
  if (!p1) return;

  // Render Monthly Orders Bar
  const distContainer = document.getElementById('orders-distribution-view');
  if (distContainer && p1.month_distribution) {
    let html = '';
    const months = ['April', 'May', 'June'];
    months.forEach(m => {
      const count = p1.month_distribution[m] || 0;
      const pct = (count / 300) * 100;
      html += `
        <div class="bar-row">
          <div class="bar-meta">
            <span>${m} 2024</span>
            <span>${count} orders (${pct.toFixed(0)}%)</span>
          </div>
          <div class="bar-track">
            <div class="bar-fill" style="width: ${pct}%"></div>
          </div>
        </div>
      `;
    });
    distContainer.innerHTML = html;
  }

  // Render Status Distribution
  const statusContainer = document.getElementById('status-distribution-view');
  if (statusContainer && p1.status_distribution) {
    statusContainer.innerHTML = `
      <div class="status-item">
        <div class="label">Delivered</div>
        <div class="count" style="color: var(--accent-emerald)">${p1.status_distribution.Delivered || 0}</div>
      </div>
      <div class="status-item">
        <div class="label">Cancelled</div>
        <div class="count" style="color: var(--accent-rose)">${p1.status_distribution.Cancelled || 0}</div>
      </div>
      <div class="status-item">
        <div class="label">Returned</div>
        <div class="count" style="color: var(--accent-amber)">${p1.status_distribution.Returned || 0}</div>
      </div>
    `;
  }

  // Render Resellers Table
  const tbody = document.getElementById('resellers-tbody');
  if (tbody && p1.resellers) {
    let html = '';
    p1.resellers.forEach(r => {
      const isZero = r.reseller_id === 'RS024';
      const statusBadge = isZero
        ? `<span class="badge badge-red">0 Orders (Edge Case)</span>`
        : `<span class="badge badge-green">Active</span>`;
      
      html += `
        <tr class="${isZero ? 'highlight-zero' : ''}">
          <td><code>${r.reseller_id}</code></td>
          <td><strong>${r.reseller_name}</strong></td>
          <td><code>${maskResellerNameClient(r.reseller_name)}</code></td>
          <td>${r.region}</td>
          <td>${statusBadge}</td>
        </tr>
      `;
    });
    tbody.innerHTML = html;
  }
}

function filterResellersTable(query) {
  const rows = document.querySelectorAll('#resellers-tbody tr');
  rows.forEach(row => {
    const text = row.innerText.toLowerCase();
    row.style.display = text.includes(query) ? '' : 'none';
  });
}

/* 2. Process 2: SQL Analytics */
function renderProcess2(p2) {
  if (!p2) return;

  // Query 1: Monthly Category Revenue
  const tbodyQ1 = document.querySelector('#table-sql-monthly tbody');
  if (tbodyQ1 && p2.monthly_category_revenue) {
    tbodyQ1.innerHTML = p2.monthly_category_revenue.map(r => `
      <tr>
        <td><span class="badge badge-purple">${r.month}</span></td>
        <td><strong>${r.category}</strong></td>
        <td>${formatINR(r.revenue)}</td>
        <td>${r.n_orders}</td>
      </tr>
    `).join('');
  }

  // Query 2: Regional Revenue
  const tbodyQ2 = document.querySelector('#table-sql-region tbody');
  if (tbodyQ2 && p2.region_revenue) {
    tbodyQ2.innerHTML = p2.region_revenue.map(r => `
      <tr>
        <td><strong>${r.region} Region</strong></td>
        <td>${formatINR(r.revenue)}</td>
        <td>${r.n_orders}</td>
      </tr>
    `).join('');
  }

  // Query 3: Top Resellers
  const tbodyQ3 = document.querySelector('#table-sql-top tbody');
  if (tbodyQ3 && p2.top_resellers) {
    tbodyQ3.innerHTML = p2.top_resellers.map((r, idx) => `
      <tr>
        <td><code>${r.reseller_id}</code></td>
        <td><strong>${r.reseller_name}</strong> (Rank #${idx + 1})</td>
        <td>${r.region}</td>
        <td><strong style="color: var(--accent-emerald)">${formatINR(r.delivered_revenue)}</strong></td>
        <td>${r.delivered_orders}</td>
      </tr>
    `).join('');
  }

  // Query 4: Zero Order LEFT JOIN demo
  const tbodyQ4 = document.querySelector('#table-sql-zero-demo tbody');
  if (tbodyQ4 && p2.zero_order_count_demo) {
    tbodyQ4.innerHTML = p2.zero_order_count_demo.map(r => {
      const isZero = r.count_order_id === '0';
      const obs = isZero
        ? `<strong style="color: var(--accent-rose)">Discrepancy: COUNT(*) evaluates 1 joined row, but COUNT(order_id) evaluates 0 non-null values</strong>`
        : `Normal matching (${r.count_order_id} orders)`;

      return `
        <tr class="${isZero ? 'highlight-zero' : ''}">
          <td><code>${r.reseller_id}</code></td>
          <td>${r.reseller_name}</td>
          <td><code>COUNT(*) = ${r.count_star}</code></td>
          <td><code>COUNT(order_id) = ${r.count_order_id}</code></td>
          <td>${obs}</td>
        </tr>
      `;
    }).join('');
  }

  // Query 5: June AOV
  const tbodyQ5 = document.querySelector('#table-sql-aov tbody');
  if (tbodyQ5 && p2.june_aov) {
    tbodyQ5.innerHTML = p2.june_aov.map(r => `
      <tr>
        <td><span class="badge badge-blue">${r.month}</span></td>
        <td>${formatINR(r.delivered_revenue)}</td>
        <td>${r.delivered_orders}</td>
        <td><strong style="color: var(--accent-emerald); font-size: 1.05rem;">${formatINR(r.aov)}</strong></td>
      </tr>
    `).join('');
  }
}

/* 3. Process 3: Growth Engine */
function renderProcess3(p3) {
  if (!p3) return;

  // Feed status
  const pill = document.getElementById('feed-valid-pill');
  const errBox = document.getElementById('feed-errors-box');
  if (p3.feed_validation) {
    if (p3.feed_validation.is_valid) {
      pill.className = 'badge badge-green';
      pill.innerText = 'VALID (5 Categories Present)';
      errBox.style.display = 'none';
    } else {
      pill.className = 'badge badge-red';
      pill.innerText = 'INVALID FEED';
      errBox.style.display = 'block';
      errBox.innerHTML = `<strong>Errors:</strong> ${p3.feed_validation.errors.join(', ')}`;
    }
  }

  // May vs April Growth Table
  const tbodyMay = document.querySelector('#table-growth-may tbody');
  if (tbodyMay && p3.may_growth) {
    tbodyMay.innerHTML = p3.may_growth.map(r => {
      const classBadge = getClassificationBadge(r.classification);
      return `
        <tr>
          <td><strong>${r.category}</strong></td>
          <td>${formatINR(r.prev_revenue)}</td>
          <td>${formatINR(r.curr_revenue)}</td>
          <td><strong>${formatPct(r.mom_pct)}</strong></td>
          <td>${classBadge}</td>
        </tr>
      `;
    }).join('');
  }

  // June vs May Growth Table
  const tbodyJun = document.querySelector('#table-growth-june tbody');
  if (tbodyJun && p3.june_growth) {
    tbodyJun.innerHTML = p3.june_growth.map(r => {
      const classBadge = getClassificationBadge(r.classification);
      return `
        <tr>
          <td><strong>${r.category}</strong></td>
          <td>${formatINR(r.prev_revenue)}</td>
          <td>${formatINR(r.curr_revenue)}</td>
          <td><strong>${formatPct(r.mom_pct)}</strong></td>
          <td>${classBadge}</td>
        </tr>
      `;
    }).join('');
  }
}

function getClassificationBadge(classification) {
  if (classification === 'flagged') {
    return `<span class="badge badge-red">FLAGGED (&gt;8%)</span>`;
  } else if (classification === 'escalated') {
    return `<span class="badge badge-amber">ESCALATED (==8%)</span>`;
  } else {
    return `<span class="badge badge-blue">NORMAL (&lt;8%)</span>`;
  }
}

/* 4. Process 4: PII & Narratives */
function renderProcess4(p4) {
  if (!p4) return;

  const container = document.getElementById('narratives-container');
  if (container && p4.narratives) {
    container.innerHTML = p4.narratives.map(item => {
      const parts = item.narrative.split('\n');
      const contextLine = parts[0] || '';
      const insightLine = parts[1] || '';
      const implicationLine = parts[2] || '';

      const validPill = item.is_valid
        ? `<span class="badge badge-green">✔ Rules Passed</span>`
        : `<span class="badge badge-red">✖ Invalid: ${item.errors.join(', ')}</span>`;

      return `
        <div class="narrative-card">
          <div class="narrative-card-header">
            <div class="narrative-title">${item.category} (${formatPct(item.mom_pct)})</div>
            ${validPill}
          </div>
          <div class="narrative-section">
            <span class="narrative-tag tag-context">CONTEXT</span>
            <span>${contextLine.replace('CONTEXT: ', '')}</span>
          </div>
          <div class="narrative-section">
            <span class="narrative-tag tag-insight">INSIGHT</span>
            <span>${insightLine.replace('INSIGHT: ', '')}</span>
          </div>
          <div class="narrative-section">
            <span class="narrative-tag tag-implication">IMPLICATION (HYPOTHESIS)</span>
            <span>${implicationLine.replace('IMPLICATION (HYPOTHESIS): ', '')}</span>
          </div>
        </div>
      `;
    }).join('');
  }
}

function initMaskSandbox() {
  const btn = document.getElementById('btn-test-mask');
  const input = document.getElementById('mask-input');
  const resultBox = document.getElementById('mask-result-box');
  const origVal = document.getElementById('mask-original-val');
  const resVal = document.getElementById('mask-result-val');

  btn.addEventListener('click', async () => {
    const rawName = input.value.trim();
    if (!rawName) return;

    try {
      const res = await fetch('/api/mask', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: rawName }),
      });
      const data = await res.json();
      if (res.ok) {
        origVal.innerText = data.original;
        resVal.innerText = data.masked;
        resultBox.style.display = 'flex';
      }
    } catch (err) {
      console.error('Mask sandbox error:', err);
    }
  });

  input.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') btn.click();
  });
}

function maskResellerNameClient(name) {
  // Simple deterministic client preview hash matching backend
  if (!name) return 'Reseller R000';
  let hash = 0;
  for (let i = 0; i < name.length; i++) {
    hash = ((hash << 5) - hash) + name.charCodeAt(i);
    hash |= 0;
  }
  const idx = (Math.abs(hash) % 999) + 1;
  return `Reseller R${String(idx).padStart(3, '0')}`;
}

/* 5. Process 5: Autonomous AI Agent */
function renderProcess5(p5) {
  if (!p5) return;
  renderAgentBoard();
}

function renderAgentBoard() {
  if (!STATE.processData || !STATE.processData.process5_agent) return;
  const p5 = STATE.processData.process5_agent;
  const scenarioData = STATE.activeScenario === 'may' ? p5.may_scenario : p5.june_scenario;

  const boardEl = document.getElementById('agent-board-view');
  const jsonEl = document.getElementById('agent-json-code');

  if (!scenarioData) {
    boardEl.innerHTML = `<div class="callout-box warning">Agent scenario not yet executed. Run the full pipeline to generate agent decisions.</div>`;
    jsonEl.innerText = '{ "status": "No data available" }';
    return;
  }

  jsonEl.innerText = JSON.stringify(scenarioData, null, 2);

  const drafted = scenarioData.drafted_categories || [];
  const suppressed = scenarioData.suppressed_categories || [];
  const escalated = scenarioData.escalated_categories || [];

  let html = `
    <!-- Left Column: Drafted for Approval -->
    <div class="agent-decision-col">
      <h4>
        <span>Drafted for Executive Approval (Top 3)</span>
        <span class="badge badge-green">${drafted.length} Categories</span>
      </h4>
      ${drafted.map(c => `
        <div class="agent-category-card drafted">
          <div class="agent-category-top">
            <h5>${c.category}</h5>
            <span class="badge badge-red">${formatPct(c.mom_pct)}</span>
          </div>
          <div class="agent-category-details">
            <span>Prior: ${formatINR(c.previous_revenue)}</span>
            <span>Current: ${formatINR(c.current_revenue)}</span>
          </div>
        </div>
      `).join('')}
    </div>

    <!-- Right Column: Suppressed & Escalated -->
    <div class="agent-decision-col">
      <h4>
        <span>Suppressed & Escalated Categories</span>
        <span class="badge badge-purple">${suppressed.length + escalated.length} Items</span>
      </h4>

      ${escalated.length > 0 ? `
        <div class="mb-4">
          <div style="font-size: 0.8rem; font-weight: 700; color: var(--accent-amber); margin-bottom: 0.5rem;">
            ⚠️ Boundary Escalations (|MoM| == 8.0%):
          </div>
          ${escalated.map(c => `
            <div class="agent-category-card escalated">
              <div class="agent-category-top">
                <h5>${c.category}</h5>
                <span class="badge badge-amber">${formatPct(c.mom_pct)}</span>
              </div>
              <div class="agent-category-details">
                <span>Prior: ${formatINR(c.previous_revenue)}</span>
                <span>Current: ${formatINR(c.current_revenue)}</span>
              </div>
            </div>
          `).join('')}
        </div>
      ` : ''}

      <div>
        <div style="font-size: 0.8rem; font-weight: 700; color: var(--text-muted); margin-bottom: 0.5rem;">
          Suppressed (Lower Priority or Within ±8% Threshold):
        </div>
        ${suppressed.length === 0 ? '<p style="font-size: 0.8rem; color: var(--text-muted);">None</p>' : ''}
        ${suppressed.map(c => `
          <div class="agent-category-card suppressed">
            <div class="agent-category-top">
              <h5>${c.category}</h5>
              <span class="badge badge-blue">${formatPct(c.mom_pct)}</span>
            </div>
            <div class="agent-category-details">
              <span>Prior: ${formatINR(c.previous_revenue)}</span>
              <span>Current: ${formatINR(c.current_revenue)}</span>
            </div>
          </div>
        `).join('')}
      </div>
    </div>
  `;

  boardEl.innerHTML = html;
}
