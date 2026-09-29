/**
 * Datasets and Synthetic Ledger Explorer Page Component
 */

import { ApiClient } from '../api.js';

export async function renderDatasetsPage(container) {
  container.innerHTML = `
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
      <div>
        <h2 style="font-size: 18px; font-weight: 600; color: var(--text-primary);">Synthetic Financial Ledgers</h2>
        <p style="font-size: 12px; color: var(--text-muted);">
          Deterministic, mathematically balanced double-entry ledgers with reconciling sub-ledgers and treasury data.
        </p>
      </div>
      <div>
        <button id="open-gen-modal-btn" class="btn btn-primary btn-sm">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 5v14M5 12h14"/></svg>
          Generate Baseline Dataset
        </button>
      </div>
    </div>

    <!-- Generator Modal -->
    <div id="gen-modal" style="display:none; position:fixed; top:0; left:0; width:100%; height:100%; background:rgba(0,0,0,0.7); z-index:9999; align-items:center; justify-content:center;">
      <div class="card" style="width:520px; max-width:92%; max-height:90vh; overflow-y:auto; border-color:var(--border-strong);">
        <div class="card-header">
          <div class="card-title">Generate Synthetic Ledger Baseline</div>
          <button id="close-gen-modal-btn" class="btn btn-secondary btn-sm">Cancel</button>
        </div>

        <form id="gen-dataset-form">
          <div class="form-group">
            <label class="form-label" for="ds-name">Dataset Name</label>
            <input type="text" id="ds-name" class="form-control" required value="Global Banking Baseline 2025" />
          </div>

          <div style="display:grid; grid-template-columns: 1fr 1fr; gap:12px;">
            <div class="form-group">
              <label class="form-label" for="ds-seed">Deterministic Seed</label>
              <div style="display:flex; gap:6px;">
                <input type="number" id="ds-seed" class="form-control" required value="42" min="0" />
                <button type="button" id="random-seed-btn" class="btn btn-secondary btn-sm" title="Randomize seed">🎲</button>
              </div>
            </div>
            <div class="form-group">
              <label class="form-label" for="ds-entities">Entities Count</label>
              <input type="number" id="ds-entities" class="form-control" required value="3" min="1" max="10" />
            </div>
          </div>

          <div style="display:grid; grid-template-columns: 1fr 1fr; gap:12px;">
            <div class="form-group">
              <label class="form-label" for="ds-months">Period Duration (Months)</label>
              <select id="ds-months" class="form-control">
                <option value="3">3 Months (Quarterly)</option>
                <option value="6">6 Months (Half-Year)</option>
                <option value="12" selected>12 Months (Full Year)</option>
                <option value="24">24 Months (Two Years)</option>
              </select>
            </div>
            <div class="form-group">
              <label class="form-label" for="ds-volume">Transaction Volume</label>
              <select id="ds-volume" class="form-control">
                <option value="low" selected>Low (~500 batches/yr)</option>
                <option value="medium">Medium (~2,500 batches/yr)</option>
                <option value="high">High (~6,000 batches/yr)</option>
              </select>
            </div>
          </div>

          <div class="form-group">
            <label class="form-label" for="ds-profile">Industry Profile</label>
            <select id="ds-profile" class="form-control">
              <option value="bank" selected>Global Commercial & Investment Bank</option>
              <option value="asset_manager">Institutional Asset Manager</option>
              <option value="wealth_manager">Private Wealth Management</option>
            </select>
          </div>

          <div class="form-group" style="display:flex; align-items:center; gap:8px;">
            <input type="checkbox" id="ds-decoys" checked style="accent-color:var(--accent-blue); width:16px; height:16px;" />
            <label for="ds-decoys" style="font-size:12px; color:var(--text-primary); cursor:pointer;">
              Embed Legitimate Decoy Anomalies (for False Positive testing)
            </label>
          </div>

          <div id="gen-progress-box" style="display:none; margin: 16px 0;">
            <div style="display:flex; justify-content:space-between; font-size:12px; margin-bottom:4px;">
              <span id="gen-step-label">Generating balanced double-entry batches...</span>
              <span id="gen-pct" class="num">0%</span>
            </div>
            <div style="width:100%; height:6px; background:var(--bg-tertiary); border-radius:3px; overflow:hidden;">
              <div id="gen-bar" style="width:0%; height:100%; background:var(--accent-blue); transition:width 0.3s ease;"></div>
            </div>
          </div>

          <button type="submit" id="start-gen-btn" class="btn btn-primary" style="width:100%; padding:10px;">
            Start Dataset Generation Job
          </button>
        </form>
      </div>
    </div>

    <!-- Active Datasets List -->
    <div class="card">
      <div class="card-header">
        <div class="card-title">Available Datasets</div>
        <button id="refresh-ds-btn" class="btn btn-secondary btn-sm">Refresh</button>
      </div>

      <div class="table-responsive">
        <table class="table">
          <thead>
            <tr>
              <th>Dataset Name</th>
              <th>Type</th>
              <th>Period Range</th>
              <th>Seed</th>
              <th>GL Entries</th>
              <th>Status</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody id="datasets-table-body">
            <tr><td colspan="7" style="text-align:center; padding:30px; color:var(--text-muted);">Loading datasets...</td></tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Drilldown Viewer Area (Initially hidden) -->
    <div id="drilldown-area" style="display:none; margin-top:24px;">
      <div class="card">
        <div style="display:flex; justify-content:space-between; align-items:center; border-bottom:1px solid var(--border-subtle); padding-bottom:12px; margin-bottom:16px;">
          <div>
            <h3 id="selected-ds-title" style="font-size:16px; font-weight:600; color:var(--text-primary);">Dataset Detail</h3>
            <span id="selected-ds-sub" style="font-size:12px; color:var(--text-muted);">Period: 2025-01 to 2025-12</span>
          </div>
          <div style="display:flex; gap:8px;">
            <button class="btn btn-secondary btn-sm drill-tab-btn active" data-tab="tb">Trial Balance</button>
            <button class="btn btn-secondary btn-sm drill-tab-btn" data-tab="gl">GL Entries</button>
            <button class="btn btn-secondary btn-sm drill-tab-btn" data-tab="sl">Sub-Ledgers</button>
            <button class="btn btn-secondary btn-sm drill-tab-btn" data-tab="decoys">Decoy Anomalies</button>
          </div>
        </div>

        <div id="tab-content-area"></div>
      </div>
    </div>
  `;

  // UI Element References
  const modal = document.getElementById('gen-modal');
  const openModalBtn = document.getElementById('open-gen-modal-btn');
  const closeModalBtn = document.getElementById('close-gen-modal-btn');
  const randomSeedBtn = document.getElementById('random-seed-btn');
  const genForm = document.getElementById('gen-dataset-form');
  const startGenBtn = document.getElementById('start-gen-btn');
  const progressBox = document.getElementById('gen-progress-box');
  const progressBar = document.getElementById('gen-bar');
  const progressPct = document.getElementById('gen-pct');
  const progressLabel = document.getElementById('gen-step-label');
  const tbody = document.getElementById('datasets-table-body');
  const refreshBtn = document.getElementById('refresh-ds-btn');
  const drilldownArea = document.getElementById('drilldown-area');
  const selectedDsTitle = document.getElementById('selected-ds-title');
  const selectedDsSub = document.getElementById('selected-ds-sub');
  const tabContent = document.getElementById('tab-content-area');

  let activeDatasetId = null;

  // Modal Open/Close
  openModalBtn.addEventListener('click', () => { modal.style.display = 'flex'; });
  closeModalBtn.addEventListener('click', () => { modal.style.display = 'none'; });
  randomSeedBtn.addEventListener('click', () => {
    document.getElementById('ds-seed').value = Math.floor(Math.random() * 900000) + 100000;
  });

  // Load Datasets List
  async function loadDatasets() {
    try {
      const res = await ApiClient.request('/datasets');
      if (!res.datasets || res.datasets.length === 0) {
        tbody.innerHTML = `<tr><td colspan="7" style="text-align:center; padding:30px; color:var(--text-muted);">No datasets generated yet. Click "Generate Baseline Dataset" to create one.</td></tr>`;
        return;
      }

      tbody.innerHTML = res.datasets.map((d) => {
        const glCount = d.params?.summary?.total_gl_entries || '—';
        const isBase = d.is_baseline;
        return `
          <tr>
            <td><strong>${d.name}</strong></td>
            <td><span class="badge ${isBase ? 'badge-success' : 'badge-warning'}">${isBase ? 'Baseline' : 'Mutated'}</span></td>
            <td class="num">${d.period_start} → ${d.period_end}</td>
            <td class="num">${d.seed}</td>
            <td class="num">${typeof glCount === 'number' ? glCount.toLocaleString() : glCount}</td>
            <td><span class="badge badge-info">${d.status}</span></td>
            <td>
              <button class="btn btn-secondary btn-sm inspect-ds-btn" data-id="${d.id}" data-name="${d.name}" data-periods="${d.period_start} to ${d.period_end}">
                Inspect
              </button>
            </td>
          </tr>
        `;
      }).join('');

      container.querySelectorAll('.inspect-ds-btn').forEach((btn) => {
        btn.addEventListener('click', () => {
          activeDatasetId = btn.dataset.id;
          selectedDsTitle.textContent = btn.dataset.name;
          selectedDsSub.textContent = `Period: ${btn.dataset.periods}`;
          drilldownArea.style.display = 'block';
          loadTabContent('tb');
        });
      });

    } catch (err) {
      tbody.innerHTML = `<tr><td colspan="7" style="color:var(--status-danger-text); padding:20px; text-align:center;">Failed to load datasets: ${err.message}</td></tr>`;
    }
  }

  // Load Drilldown Tabs
  async function loadTabContent(tabKey) {
    if (!activeDatasetId) return;

    container.querySelectorAll('.drill-tab-btn').forEach((btn) => {
      btn.classList.toggle('active', btn.dataset.tab === tabKey);
    });

    if (tabKey === 'tb') {
      tabContent.innerHTML = `<p style="padding:20px; text-align:center; color:var(--text-muted);">Calculating trial balance aggregation...</p>`;
      try {
        const tb = await ApiClient.request(`/datasets/${activeDatasetId}/trial-balance`);
        tabContent.innerHTML = `
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
            <div style="display:flex; gap:16px;">
              <span>Total Debits: <strong class="num">$${tb.sum_debit.toLocaleString(undefined, {minimumFractionDigits: 2})}</strong></span>
              <span>Total Credits: <strong class="num">$${tb.sum_credit.toLocaleString(undefined, {minimumFractionDigits: 2})}</strong></span>
            </div>
            <span class="badge ${tb.is_balanced ? 'badge-success' : 'badge-danger'}">
              <span class="badge-dot"></span> ${tb.is_balanced ? 'Zero-Sum Balanced (Δ = $0.00)' : 'Unbalanced Break!'}
            </span>
          </div>

          <div class="table-responsive">
            <table class="table">
              <thead>
                <tr>
                  <th>Code</th>
                  <th>Account Name</th>
                  <th>Type</th>
                  <th>Normal Bal</th>
                  <th style="text-align:right;">Debit</th>
                  <th style="text-align:right;">Credit</th>
                  <th style="text-align:right;">Net Balance</th>
                </tr>
              </thead>
              <tbody>
                ${tb.items.map((i) => `
                  <tr>
                    <td class="num"><strong>${i.account_code}</strong></td>
                    <td>${i.account_name}</td>
                    <td><span class="badge badge-info" style="font-size:10px;">${i.account_type.toUpperCase()}</span></td>
                    <td>${i.normal_balance}</td>
                    <td class="num" style="text-align:right;">$${i.total_debit.toLocaleString(undefined, {minimumFractionDigits: 2})}</td>
                    <td class="num" style="text-align:right;">$${i.total_credit.toLocaleString(undefined, {minimumFractionDigits: 2})}</td>
                    <td class="num" style="text-align:right; font-weight:600;">$${i.net_balance.toLocaleString(undefined, {minimumFractionDigits: 2})}</td>
                  </tr>
                `).join('')}
              </tbody>
            </table>
          </div>
        `;
      } catch (err) {
        tabContent.innerHTML = `<p style="color:var(--status-danger-text); padding:20px;">Failed to load trial balance: ${err.message}</p>`;
      }
    } else if (tabKey === 'gl') {
      tabContent.innerHTML = `<p style="padding:20px; text-align:center; color:var(--text-muted);">Loading general ledger sample...</p>`;
      try {
        const entries = await ApiClient.request(`/datasets/${activeDatasetId}/gl-entries?limit=50`);
        tabContent.innerHTML = `
          <div class="table-responsive">
            <table class="table">
              <thead>
                <tr>
                  <th>Date</th>
                  <th>Batch ID</th>
                  <th>Account</th>
                  <th style="text-align:right;">Debit</th>
                  <th style="text-align:right;">Credit</th>
                  <th>Description</th>
                  <th>Source</th>
                  <th>Maker / Checker</th>
                </tr>
              </thead>
              <tbody>
                ${entries.map((e) => `
                  <tr>
                    <td class="num" style="font-size:12px;">${e.posting_date}</td>
                    <td class="num" style="font-size:11px; color:var(--text-muted);">${e.batch_id}</td>
                    <td class="num"><strong>${e.account_code}</strong></td>
                    <td class="num" style="text-align:right; color:${e.debit > 0 ? 'var(--text-primary)' : 'var(--text-muted)'};">$${Number(e.debit).toLocaleString(undefined, {minimumFractionDigits: 2})}</td>
                    <td class="num" style="text-align:right; color:${e.credit > 0 ? 'var(--text-primary)' : 'var(--text-muted)'};">$${Number(e.credit).toLocaleString(undefined, {minimumFractionDigits: 2})}</td>
                    <td style="font-size:12px;">${e.description}</td>
                    <td><span class="badge badge-info" style="font-size:10px;">${e.source_system}</span></td>
                    <td style="font-size:11px; color:var(--text-muted);">${e.created_by.split('@')[0]} / ${e.approved_by.split('@')[0]}</td>
                  </tr>
                `).join('')}
              </tbody>
            </table>
          </div>
        `;
      } catch (err) {
        tabContent.innerHTML = `<p style="color:var(--status-danger-text); padding:20px;">Failed to load GL entries: ${err.message}</p>`;
      }
    } else if (tabKey === 'sl') {
      tabContent.innerHTML = `<p style="padding:20px; text-align:center; color:var(--text-muted);">Loading sub-ledger entries...</p>`;
      try {
        const slEntries = await ApiClient.request(`/datasets/${activeDatasetId}/subledger-entries?limit=50`);
        tabContent.innerHTML = `
          <div class="table-responsive">
            <table class="table">
              <thead>
                <tr>
                  <th>Ref ID</th>
                  <th>Subledger Type</th>
                  <th>Counterparty</th>
                  <th style="text-align:right;">Amount</th>
                  <th>Value Date</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                ${slEntries.map((s) => `
                  <tr>
                    <td class="num" style="font-size:11px;">${s.ref_id}</td>
                    <td><span class="badge badge-info">${s.subledger_type.toUpperCase()}</span></td>
                    <td><strong>${s.counterparty}</strong></td>
                    <td class="num" style="text-align:right;">$${Number(s.amount).toLocaleString(undefined, {minimumFractionDigits: 2})}</td>
                    <td class="num">${s.value_date}</td>
                    <td><span class="badge badge-success">${s.status}</span></td>
                  </tr>
                `).join('')}
              </tbody>
            </table>
          </div>
        `;
      } catch (err) {
        tabContent.innerHTML = `<p style="color:var(--status-danger-text); padding:20px;">Failed to load subledger entries: ${err.message}</p>`;
      }
    } else if (tabKey === 'decoys') {
      try {
        const dData = await ApiClient.request(`/datasets/${activeDatasetId}/decoys`);
        if (!dData.decoys || dData.decoys.length === 0) {
          tabContent.innerHTML = `<p style="padding:20px; color:var(--text-muted); text-align:center;">No decoy anomalies embedded in this dataset.</p>`;
          return;
        }

        tabContent.innerHTML = `
          <p style="font-size:12px; color:var(--text-muted); margin-bottom:12px;">
            These transactions are <strong>legitimate anomalies</strong> (large, authorized one-offs). They test whether variance and outlier controls cause false positives.
          </p>
          <div class="table-responsive">
            <table class="table">
              <thead>
                <tr>
                  <th>Decoy ID</th>
                  <th>Period</th>
                  <th>Account</th>
                  <th style="text-align:right;">Amount</th>
                  <th>Description</th>
                  <th>Documented Justification</th>
                </tr>
              </thead>
              <tbody>
                ${dData.decoys.map((d) => `
                  <tr>
                    <td><span class="badge badge-warning">${d.decoy_id}</span></td>
                    <td class="num">${d.period}</td>
                    <td class="num"><strong>${d.account_code}</strong></td>
                    <td class="num" style="text-align:right; font-weight:600;">$${Number(d.amount).toLocaleString(undefined, {minimumFractionDigits: 2})}</td>
                    <td>${d.description}</td>
                    <td style="color:var(--status-success-text); font-size:12px;">${d.reason_valid}</td>
                  </tr>
                `).join('')}
              </tbody>
            </table>
          </div>
        `;
      } catch (err) {
        tabContent.innerHTML = `<p style="color:var(--status-danger-text); padding:20px;">Failed to load decoys: ${err.message}</p>`;
      }
    }
  }

  // Handle Tab Switching
  container.querySelectorAll('.drill-tab-btn').forEach((btn) => {
    btn.addEventListener('click', () => loadTabContent(btn.dataset.tab));
  });

  // Handle Form Submission & Job Polling
  genForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    startGenBtn.disabled = true;
    progressBox.style.display = 'block';
    progressBar.style.width = '10%';
    progressPct.textContent = '10%';
    progressLabel.textContent = 'Submitting dataset generation job...';

    const payload = {
      name: document.getElementById('ds-name').value.trim(),
      seed: parseInt(document.getElementById('ds-seed').value, 10),
      entities_count: parseInt(document.getElementById('ds-entities').value, 10),
      months: parseInt(document.getElementById('ds-months').value, 10),
      volume: document.getElementById('ds-volume').value,
      industry_profile: document.getElementById('ds-profile').value,
      include_decoys: document.getElementById('ds-decoys').checked,
    };

    try {
      const job = await ApiClient.request('/datasets/generate', {
        method: 'POST',
        body: JSON.stringify(payload),
      });

      const jobId = job.id;

      // Poll job status every 1.5s
      const pollInterval = setInterval(async () => {
        try {
          const statusRes = await ApiClient.request(`/datasets/jobs/${jobId}`);
          const p = statusRes.progress || 10;
          progressBar.style.width = `${p}%`;
          progressPct.textContent = `${p}%`;

          if (p < 50) {
            progressLabel.textContent = 'Generating double-entry journal batches...';
          } else if (p < 80) {
            progressLabel.textContent = 'Writing sub-ledgers, budget, and treasury buffers...';
          } else {
            progressLabel.textContent = 'Finalizing trial balance and audit record...';
          }

          if (statusRes.status === 'completed') {
            clearInterval(pollInterval);
            progressBar.style.width = '100%';
            progressPct.textContent = '100%';
            progressLabel.textContent = 'Generation completed successfully!';
            setTimeout(() => {
              modal.style.display = 'none';
              startGenBtn.disabled = false;
              progressBox.style.display = 'none';
              loadDatasets();
            }, 800);
          } else if (statusRes.status === 'failed') {
            clearInterval(pollInterval);
            progressLabel.textContent = `Failed: ${statusRes.error}`;
            startGenBtn.disabled = false;
          }
        } catch (_) {}
      }, 1500);

    } catch (err) {
      alert(`Generation failed: ${err.message}`);
      startGenBtn.disabled = false;
      progressBox.style.display = 'none';
    }
  });

  refreshBtn.addEventListener('click', loadDatasets);

  // Initial Load
  await loadDatasets();
}
