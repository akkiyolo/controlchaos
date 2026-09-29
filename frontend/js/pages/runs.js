/**
 * Runs & Scorecard Page Component for ControlChaos
 * Displays test runs, detection matching scorecards, leave-one-out marginal values,
 * and the interactive blind-spot heatmap.
 */

import { api } from '../services/api.js';

export function renderRunsPage(container) {
  container.innerHTML = `
    <div class="page-header" style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:1.5rem;">
      <div>
        <h1 style="font-size:1.75rem; font-weight:700; color:var(--text-main); margin-bottom:0.25rem;">Runs & Detection Scorecards</h1>
        <p style="color:var(--text-muted); font-size:0.9rem;">
          Rigorous mutation testing scorecards, detection matching, leave-one-out marginal value, and blind-spot heatmaps.
        </p>
      </div>
      <div style="display:flex; gap:0.75rem; flex-wrap:wrap;">
        <button id="btn-export-excel" class="btn btn-secondary" style="display:flex; align-items:center; gap:0.5rem;">
          <svg width="15" height="15" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M7 10l5 5 5-5M12 15V3"/></svg>
          Export Excel (.xlsx)
        </button>
        <button id="btn-powerbi-queries" class="btn btn-secondary" style="display:flex; align-items:center; gap:0.5rem;">
          Power BI M-Queries
        </button>
        <button id="btn-audit-pack" class="btn btn-secondary" style="display:flex; align-items:center; gap:0.5rem;">
          Audit Proof (.json)
        </button>
        <button id="btn-launch-run" class="btn btn-primary" style="display:flex; align-items:center; gap:0.5rem;">
          <svg width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><polygon points="5 3 19 12 5 21 5 3"/></svg>
          Execute New Test Run
        </button>
      </div>
    </div>

    <!-- Active Run Selector / Runs List -->
    <div class="card" style="padding:1rem 1.25rem; margin-bottom:1.5rem; background:var(--bg-surface); border:1px solid var(--border-color); border-radius:10px; display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:1rem;">
      <div style="display:flex; align-items:center; gap:1rem;">
        <span style="font-size:0.85rem; font-weight:600; color:var(--text-muted);">Select Run:</span>
        <select id="select-active-run" style="padding:0.4rem 0.75rem; border-radius:6px; border:1px solid var(--border-color); background:var(--bg-input); color:var(--text-main); font-size:0.85rem; min-width:280px;">
          <option value="">Loading runs...</option>
        </select>
      </div>
      <div id="run-status-badge"></div>
    </div>

    <!-- Scorecard Content Container -->
    <div id="scorecard-container">
      <div style="color:var(--text-muted); padding:3rem; text-align:center;">Select or execute a run to view its Scorecard.</div>
    </div>

    <!-- Launch Run Modal -->
    <div id="launch-run-modal" class="modal" style="display:none; position:fixed; inset:0; background:rgba(0,0,0,0.6); z-index:1000; align-items:center; justify-content:center;">
      <div class="card" style="width:100%; max-width:520px; padding:1.75rem; background:var(--bg-surface); border:1px solid var(--border-color); border-radius:12px;">
        <h3 style="font-size:1.2rem; font-weight:600; margin-bottom:1rem;">Execute Financial Control Run</h3>
        
        <form id="form-launch-run">
          <div class="form-group" style="margin-bottom:1rem;">
            <label style="display:block; font-size:0.85rem; font-weight:600; margin-bottom:0.25rem;">Target Dataset</label>
            <select id="run-target-dataset" required style="width:100%; padding:0.6rem; border:1px solid var(--border-color); border-radius:6px; background:var(--bg-input); color:var(--text-main);">
              <option value="">Loading datasets...</option>
            </select>
          </div>

          <div class="form-group" style="margin-bottom:1.25rem;">
            <label style="display:block; font-size:0.85rem; font-weight:600; margin-bottom:0.25rem;">Detection Matching Mode</label>
            <select id="run-match-mode" style="width:100%; padding:0.6rem; border:1px solid var(--border-color); border-radius:6px; background:var(--bg-input); color:var(--text-main);">
              <option value="strict_row" selected>Strict Row Overlap (Audit-Grade)</option>
              <option value="account_period">Account & Period Overlap (Partial Credit)</option>
            </select>
          </div>

          <div style="display:flex; justify-content:flex-end; gap:0.75rem;">
            <button type="button" id="btn-cancel-launch-run" class="btn btn-secondary">Cancel</button>
            <button type="submit" id="btn-submit-launch-run" class="btn btn-primary">Start Run</button>
          </div>
        </form>
      </div>
    </div>

    <!-- Power BI M-Queries Modal -->
    <div id="powerbi-modal" class="modal" style="display:none; position:fixed; inset:0; background:rgba(0,0,0,0.6); z-index:1000; align-items:center; justify-content:center;">
      <div class="card" style="width:100%; max-width:680px; padding:1.75rem; background:var(--bg-surface); border:1px solid var(--border-color); border-radius:12px;">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:1rem;">
          <h3 style="font-size:1.2rem; font-weight:600; margin:0;">Power BI Power Query (M) Formulas</h3>
          <button id="btn-close-powerbi" class="btn btn-ghost btn-sm">&times;</button>
        </div>
        <p style="font-size:0.85rem; color:var(--text-muted); margin-bottom:1rem;">Copy and paste into Power BI Desktop &gt; Advanced Editor to pull live ControlChaos telemetry.</p>
        <pre id="powerbi-m-code" style="background:var(--bg-card); padding:1rem; border-radius:8px; font-size:0.8rem; max-height:300px; overflow-y:auto; border:1px solid var(--border-color); font-family:monospace; white-space:pre-wrap;"></pre>
        <div style="display:flex; justify-content:flex-end; gap:0.75rem; margin-top:1rem;">
          <button id="btn-copy-powerbi" class="btn btn-primary">Copy Code</button>
        </div>
      </div>
    </div>
  `;

  initRunsView(container);
}

async function initRunsView(container) {
  let runsList = [];

  async function loadRuns() {
    try {
      const res = await api.get('/runs');
      runsList = res.runs || [];
      const select = container.querySelector('#select-active-run');

      if (runsList.length === 0) {
        select.innerHTML = `<option value="">No runs found. Execute your first run!</option>`;
        container.querySelector('#scorecard-container').innerHTML = `
          <div class="card" style="padding:3rem; text-align:center; background:var(--bg-surface); border:1px dashed var(--border-color); border-radius:10px;">
            <h3 style="font-size:1.1rem; font-weight:600; margin-bottom:0.5rem;">No Test Runs Yet</h3>
            <p style="color:var(--text-muted); font-size:0.85rem; margin-bottom:1.25rem;">Execute the 15 financial controls against a mutated dataset to generate detection metrics, blind-spot maps, and marginal values.</p>
            <button id="btn-empty-launch" class="btn btn-primary">Execute New Run</button>
          </div>
        `;
        container.querySelector('#btn-empty-launch')?.addEventListener('click', openLaunchModal);
        return;
      }

      select.innerHTML = runsList.map(r => {
        const rate = r.overall_detection_rate != null ? `${(r.overall_detection_rate * 100).toFixed(1)}%` : 'Pending';
        const dStr = new Date(r.started_at).toLocaleTimeString();
        return `<option value="${r.id}">${dStr} — Run ${r.id.slice(0, 8)} (${rate} Caught, ${r.total_findings} Findings)</option>`;
      }).join('');

      await loadScorecard(runsList[0].id);
    } catch (err) {
      container.querySelector('#scorecard-container').innerHTML = `
        <div class="alert alert-danger">Failed to load runs: ${err.message}</div>
      `;
    }
  }

  async function loadScorecard(runId) {
    if (!runId) return;
    const containerEl = container.querySelector('#scorecard-container');
    containerEl.innerHTML = `<div style="padding:2rem; text-align:center; color:var(--text-muted);">Loading Scorecard metrics...</div>`;

    try {
      const sc = await api.get(`/runs/${runId}/scorecard`);
      renderScorecard(sc);
    } catch (err) {
      containerEl.innerHTML = `<div class="alert alert-danger">Failed to load scorecard: ${err.message}</div>`;
    }
  }

  function renderScorecard(sc) {
    const containerEl = container.querySelector('#scorecard-container');
    const detRate = (sc.overall_detection_rate * 100).toFixed(1);
    const wRate = (sc.weighted_detection_rate * 100).toFixed(1);
    const prec = (sc.precision * 100).toFixed(1);
    const rec = (sc.recall * 100).toFixed(1);
    const f1 = sc.f1.toFixed(2);
    const missCost = sc.cost_of_misses.toLocaleString(undefined, { minimumFractionDigits: 2 });

    containerEl.innerHTML = `
      <!-- KPI Overview Cards -->
      <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(180px, 1fr)); gap:1rem; margin-bottom:1.5rem;">
        <div class="card" style="padding:1.25rem; background:var(--bg-surface); border:1px solid var(--border-color); border-radius:10px;">
          <div style="font-size:0.75rem; font-weight:600; color:var(--text-muted); text-transform:uppercase; margin-bottom:0.25rem;">Overall Detection</div>
          <div style="font-size:1.75rem; font-weight:700; color:${sc.overall_detection_rate >= 0.8 ? 'var(--success-color)' : 'var(--warning-color)'}; font-family:var(--font-mono);">
            ${detRate}%
          </div>
          <div style="font-size:0.75rem; color:var(--text-muted); margin-top:0.25rem;">Mutations caught</div>
        </div>

        <div class="card" style="padding:1.25rem; background:var(--bg-surface); border:1px solid var(--border-color); border-radius:10px;">
          <div style="font-size:0.75rem; font-weight:600; color:var(--text-muted); text-transform:uppercase; margin-bottom:0.25rem;">Weighted Score</div>
          <div style="font-size:1.75rem; font-weight:700; color:var(--accent-primary); font-family:var(--font-mono);">
            ${wRate}%
          </div>
          <div style="font-size:0.75rem; color:var(--text-muted); margin-top:0.25rem;">Severity-weighted</div>
        </div>

        <div class="card" style="padding:1.25rem; background:var(--bg-surface); border:1px solid var(--border-color); border-radius:10px;">
          <div style="font-size:0.75rem; font-weight:600; color:var(--text-muted); text-transform:uppercase; margin-bottom:0.25rem;">Precision / Recall</div>
          <div style="font-size:1.4rem; font-weight:700; color:var(--text-main); font-family:var(--font-mono);">
            ${prec}% / ${rec}%
          </div>
          <div style="font-size:0.75rem; color:var(--text-muted); margin-top:0.25rem;">F1 Score: ${f1}</div>
        </div>

        <div class="card" style="padding:1.25rem; background:var(--bg-surface); border:1px solid var(--border-color); border-radius:10px;">
          <div style="font-size:0.75rem; font-weight:600; color:var(--text-muted); text-transform:uppercase; margin-bottom:0.25rem;">Cost of Misses</div>
          <div style="font-size:1.5rem; font-weight:700; color:${sc.cost_of_misses > 0 ? 'var(--danger-color)' : 'var(--success-color)'}; font-family:var(--font-mono);">
            $${missCost}
          </div>
          <div style="font-size:0.75rem; color:var(--text-muted); margin-top:0.25rem;">Unflagged risk exposure</div>
        </div>
      </div>

      <!-- Main Columns: Marginal Values + Blind-Spot Heatmap -->
      <div style="display:grid; grid-template-columns:1fr 1fr; gap:1.5rem; margin-bottom:1.5rem;">
        
        <!-- Leave-One-Out Marginal Value -->
        <div class="card" style="padding:1.5rem; background:var(--bg-surface); border:1px solid var(--border-color); border-radius:10px;">
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:1rem;">
            <h3 style="font-size:1.05rem; font-weight:600; color:var(--text-main);">Control Marginal Value (Leave-One-Out)</h3>
            <span style="font-size:0.75rem; color:var(--text-muted);">Impact if control is removed</span>
          </div>

          <div style="display:flex; flex-direction:column; gap:0.75rem;">
            ${(sc.marginal_values || []).map(m => `
              <div>
                <div style="display:flex; justify-content:space-between; font-size:0.8rem; margin-bottom:0.25rem;">
                  <span style="font-family:var(--font-mono); font-weight:500;">${m.control_id}</span>
                  <span style="font-family:var(--font-mono); font-weight:600; color:${m.is_critical ? 'var(--danger-color)' : 'var(--text-muted)'};">
                    -${m.marginal_value_pct}% (${m.unique_catches} unique)
                  </span>
                </div>
                <div style="width:100%; height:8px; background:var(--bg-card); border-radius:4px; overflow:hidden;">
                  <div style="width:${Math.max(4, m.marginal_value_pct)}%; height:100%; background:${m.is_critical ? 'var(--accent-primary)' : 'var(--text-muted)'}; border-radius:4px;"></div>
                </div>
              </div>
            `).join('') || '<div style="color:var(--text-muted); font-size:0.85rem;">No marginal data available.</div>'}
          </div>
        </div>

        <!-- Blind-Spot Heatmap Matrix -->
        <div class="card" style="padding:1.5rem; background:var(--bg-surface); border:1px solid var(--border-color); border-radius:10px;">
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:1rem;">
            <h3 style="font-size:1.05rem; font-weight:600; color:var(--text-main);">Institutional Blind-Spot Heatmap</h3>
            <span style="font-size:0.75rem; color:var(--text-muted);">Mutation Class x Stealth x Magnitude</span>
          </div>

          <div style="max-height:320px; overflow-y:auto;">
            <table class="table" style="font-size:0.8rem; width:100%;">
              <thead>
                <tr>
                  <th>Class</th>
                  <th>Stealth / Mag</th>
                  <th>Tested</th>
                  <th>Detection Rate</th>
                </tr>
              </thead>
              <tbody>
                ${(sc.blindspot_map || []).map(b => `
                  <tr>
                    <td style="font-family:var(--font-mono); font-weight:500;">${b.class_name}</td>
                    <td><span style="font-size:0.75rem; color:var(--text-muted);">${b.stealth} / ${b.magnitude}</span></td>
                    <td>${b.tested}</td>
                    <td>
                      <span class="badge ${b.status === 'caught' ? 'badge-success' : b.status === 'partial' ? 'badge-warning' : 'badge-danger'}" style="font-family:var(--font-mono); font-size:0.75rem;">
                        ${b.detection_rate_pct}%
                      </span>
                    </td>
                  </tr>
                `).join('') || '<tr><td colspan="4" style="color:var(--text-muted);">No blindspot cells.</td></tr>'}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <!-- Injected Mutations Detection Breakdown -->
      <div class="card" style="padding:1.5rem; background:var(--bg-surface); border:1px solid var(--border-color); border-radius:10px;">
        <h3 style="font-size:1.05rem; font-weight:600; color:var(--text-main); margin-bottom:1rem;">Ground Truth Detection Ledger</h3>
        <div style="max-height:300px; overflow-y:auto;">
          <table class="table" style="font-size:0.82rem; width:100%;">
            <thead>
              <tr>
                <th>Mutation ID</th>
                <th>Status</th>
                <th>Detected By</th>
                <th>Partial Credit</th>
              </tr>
            </thead>
            <tbody>
              ${(sc.detections || []).map(d => `
                <tr>
                  <td style="font-family:var(--font-mono); font-weight:500;">${d.mutation_id}</td>
                  <td>
                    <span class="badge ${d.detected ? 'badge-success' : 'badge-danger'}" style="font-size:0.75rem;">
                      ${d.detected ? 'CAUGHT' : 'SLIPPED THROUGH'}
                    </span>
                  </td>
                  <td style="font-family:var(--font-mono); font-size:0.75rem;">
                    ${d.detected_by.length ? d.detected_by.join(', ') : '—'}
                  </td>
                  <td style="font-family:var(--font-mono);">${d.partial_credit * 100}%</td>
                </tr>
              `).join('') || '<tr><td colspan="4" style="color:var(--text-muted); text-align:center;">No detection items.</td></tr>'}
            </tbody>
          </table>
        </div>
      </div>
    `;
  }

  // Active run selection change
  container.querySelector('#select-active-run').addEventListener('change', (e) => {
    loadScorecard(e.target.value);
  });

  // Launch modal open / close
  async function openLaunchModal() {
    try {
      const res = await api.get('/datasets');
      const all = res.datasets || [];
      const select = container.querySelector('#run-target-dataset');

      select.innerHTML = all.length
        ? all.map(d => `<option value="${d.id}">${d.name} (${d.is_baseline ? 'Baseline' : 'Mutated'})</option>`).join('')
        : `<option value="">No datasets available</option>`;

      container.querySelector('#launch-run-modal').style.display = 'flex';
    } catch (err) {
      alert(`Failed to load datasets: ${err.message}`);
    }
  }

  container.querySelector('#btn-launch-run').addEventListener('click', openLaunchModal);
  container.querySelector('#btn-cancel-launch-run').addEventListener('click', () => {
    container.querySelector('#launch-run-modal').style.display = 'none';
  });

  // Launch Run Submit
  container.querySelector('#form-launch-run').addEventListener('submit', async (e) => {
    e.preventDefault();
    const datasetId = container.querySelector('#run-target-dataset').value;
    const matchMode = container.querySelector('#run-match-mode').value;

    if (!datasetId) {
      alert('Please select a target dataset');
      return;
    }

    const submitBtn = container.querySelector('#btn-submit-launch-run');
    submitBtn.disabled = true;
    submitBtn.textContent = 'Executing Suite & Scoring...';

    try {
      const newScorecard = await api.post('/runs', {
        dataset_id: datasetId,
        match_mode: matchMode,
      });

      container.querySelector('#launch-run-modal').style.display = 'none';
      alert(`Run completed! Overall Detection Rate: ${(newScorecard.overall_detection_rate * 100).toFixed(1)}%`);
      await loadRuns();
    } catch (err) {
      alert(`Run execution failed: ${err.message}`);
    } finally {
      submitBtn.disabled = false;
      submitBtn.textContent = 'Start Run';
    }
  });

  // Export buttons
  container.querySelector('#btn-export-excel').addEventListener('click', () => {
    const runId = container.querySelector('#select-active-run').value;
    if (!runId) {
      alert('Please select a completed run first.');
      return;
    }
    window.location.href = `/api/v1/exports/excel?run_id=${runId}`;
  });

  container.querySelector('#btn-powerbi-queries').addEventListener('click', async () => {
    try {
      const res = await api.get('/exports/powerbi/m-queries');
      const modal = container.querySelector('#powerbi-modal');
      const codeBlock = container.querySelector('#powerbi-m-code');
      const queries = res.m_queries || {};
      codeBlock.textContent = Object.entries(queries)
        .map(([k, v]) => `// --- Table: ${k} ---\n${v}\n`)
        .join('\n\n');
      modal.style.display = 'flex';
    } catch (err) {
      alert(`Failed to load Power BI queries: ${err.message}`);
    }
  });

  container.querySelector('#btn-close-powerbi').addEventListener('click', () => {
    container.querySelector('#powerbi-modal').style.display = 'none';
  });

  container.querySelector('#btn-copy-powerbi').addEventListener('click', () => {
    const text = container.querySelector('#powerbi-m-code').textContent;
    navigator.clipboard.writeText(text);
    alert('Power BI M-Queries copied to clipboard!');
  });

  container.querySelector('#btn-audit-pack').addEventListener('click', async () => {
    const runId = container.querySelector('#select-active-run').value;
    if (!runId) {
      alert('Please select a run first.');
      return;
    }
    try {
      const res = await api.get(`/exports/audit-pack?run_id=${runId}`);
      const blob = new Blob([JSON.stringify(res, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `Audit_Pack_Run_${runId.slice(0, 8)}.json`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      alert(`Failed to download audit pack: ${err.message}`);
    }
  });

  await loadRuns();
}
