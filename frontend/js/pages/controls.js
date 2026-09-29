/**
 * Controls Page Component for ControlChaos
 * Displays the catalog of 15 financial controls, parameter versioning,
 * maker-checker diff approval workflow, and on-demand suite execution.
 */

import { api } from '../services/api.js';

export function renderControls(container) {
  container.innerHTML = `
    <div class="page-header" style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:1.5rem;">
      <div>
        <h1 style="font-size:1.75rem; font-weight:700; color:var(--text-main); margin-bottom:0.25rem;">Financial Controls Suite</h1>
        <p style="color:var(--text-muted); font-size:0.9rem;">
          15 regulatory & institutional controls with typed parameters, immutable version history, and maker-checker approval.
        </p>
      </div>
      <div style="display:flex; gap:0.75rem;">
        <button id="btn-run-suite" class="btn btn-primary" style="display:flex; align-items:center; gap:0.5rem;">
          <svg width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><polygon points="5 3 19 12 5 21 5 3"/></svg>
          Run Suite
        </button>
      </div>
    </div>

    <!-- Category Filter Tabs -->
    <div style="display:flex; gap:0.5rem; flex-wrap:wrap; margin-bottom:1.5rem;" id="control-category-filters">
      <button class="filter-chip active" data-cat="all">All (15)</button>
      <button class="filter-chip" data-cat="reconciliation">Reconciliation</button>
      <button class="filter-chip" data-cat="integrity">Integrity</button>
      <button class="filter-chip" data-cat="cutoff">Cutoff</button>
      <button class="filter-chip" data-cat="variance">Variance</button>
      <button class="filter-chip" data-cat="policy">Policy & SOD</button>
      <button class="filter-chip" data-cat="forensic">Forensics & Benford</button>
      <button class="filter-chip" data-cat="treasury">Treasury</button>
      <button class="filter-chip" data-cat="market_data">Market Data</button>
    </div>

    <!-- Controls Grid -->
    <div id="controls-grid" style="display:grid; grid-template-columns:repeat(auto-fill, minmax(360px, 1fr)); gap:1.25rem;">
      <div style="color:var(--text-muted); padding:2rem; text-align:center;">Loading controls...</div>
    </div>

    <!-- Edit / Propose Drawer Modal -->
    <div id="edit-control-modal" class="modal" style="display:none; position:fixed; inset:0; background:rgba(0,0,0,0.6); z-index:1000; align-items:center; justify-content:center;">
      <div class="card" style="width:100%; max-width:550px; max-height:90vh; overflow-y:auto; padding:1.75rem; background:var(--bg-surface); border:1px solid var(--border-color); border-radius:12px;">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:1rem;">
          <h3 id="edit-modal-title" style="font-size:1.2rem; font-weight:600;">Edit Control Parameters</h3>
          <button id="btn-close-edit-modal" style="background:none; border:none; color:var(--text-muted); cursor:pointer; font-size:1.25rem;">&times;</button>
        </div>
        <div id="edit-control-desc" style="font-size:0.85rem; color:var(--text-muted); margin-bottom:1rem;"></div>
        
        <form id="form-propose-edit">
          <input type="hidden" id="edit-control-key" />
          <div class="form-group" style="margin-bottom:1rem;">
            <label style="display:block; font-size:0.85rem; font-weight:600; margin-bottom:0.25rem;">Parameters (JSON)</label>
            <textarea id="edit-params-json" rows="6" style="width:100%; font-family:var(--font-mono); font-size:0.85rem; padding:0.6rem; border:1px solid var(--border-color); border-radius:6px; background:var(--bg-input); color:var(--text-main);"></textarea>
          </div>
          <div class="form-group" style="margin-bottom:1.25rem;">
            <label style="display:block; font-size:0.85rem; font-weight:600; margin-bottom:0.25rem;">Business Rationale (Required for Maker-Checker)</label>
            <textarea id="edit-rationale" rows="3" required placeholder="Reason for adjusting tolerance or threshold..." style="width:100%; font-size:0.85rem; padding:0.6rem; border:1px solid var(--border-color); border-radius:6px; background:var(--bg-input); color:var(--text-main);"></textarea>
          </div>
          <div style="display:flex; justify-content:flex-end; gap:0.75rem;">
            <button type="button" id="btn-cancel-edit" class="btn btn-secondary">Cancel</button>
            <button type="submit" class="btn btn-primary">Submit for Checker Review</button>
          </div>
        </form>
      </div>
    </div>

    <!-- Run Controls Modal -->
    <div id="run-controls-modal" class="modal" style="display:none; position:fixed; inset:0; background:rgba(0,0,0,0.6); z-index:1000; align-items:center; justify-content:center;">
      <div class="card" style="width:100%; max-width:500px; padding:1.75rem; background:var(--bg-surface); border:1px solid var(--border-color); border-radius:12px;">
        <h3 style="font-size:1.2rem; font-weight:600; margin-bottom:1rem;">Execute Financial Controls Suite</h3>
        <div class="form-group" style="margin-bottom:1.25rem;">
          <label style="display:block; font-size:0.85rem; font-weight:600; margin-bottom:0.25rem;">Select Target Dataset</label>
          <select id="run-dataset-select" style="width:100%; padding:0.6rem; border:1px solid var(--border-color); border-radius:6px; background:var(--bg-input); color:var(--text-main);">
            <option value="">Loading datasets...</option>
          </select>
        </div>
        <div style="display:flex; justify-content:flex-end; gap:0.75rem;">
          <button type="button" id="btn-cancel-run" class="btn btn-secondary">Cancel</button>
          <button type="button" id="btn-confirm-run" class="btn btn-primary">Start Execution</button>
        </div>
      </div>
    </div>

    <!-- Findings Modal -->
    <div id="findings-modal" class="modal" style="display:none; position:fixed; inset:0; background:rgba(0,0,0,0.6); z-index:1000; align-items:center; justify-content:center;">
      <div class="card" style="width:100%; max-width:850px; max-height:85vh; display:flex; flex-direction:column; padding:1.75rem; background:var(--bg-surface); border:1px solid var(--border-color); border-radius:12px;">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:1rem;">
          <h3 id="findings-title" style="font-size:1.25rem; font-weight:600;">Control Run Findings</h3>
          <button id="btn-close-findings" style="background:none; border:none; color:var(--text-muted); cursor:pointer; font-size:1.25rem;">&times;</button>
        </div>
        <div id="findings-summary" style="display:flex; gap:1rem; margin-bottom:1rem; font-size:0.85rem;"></div>
        <div id="findings-table-container" style="flex:1; overflow-y:auto;"></div>
      </div>
    </div>
  `;

  initControlsView(container);
}

async function initControlsView(container) {
  let allControls = [];
  let currentCategory = 'all';

  async function loadControls() {
    try {
      const res = await api.get('/controls');
      allControls = res.controls || [];
      renderGrid();
    } catch (err) {
      container.querySelector('#controls-grid').innerHTML = `
        <div class="alert alert-danger" style="grid-column:1/-1;">Failed to load controls: ${err.message}</div>
      `;
    }
  }

  function renderGrid() {
    const grid = container.querySelector('#controls-grid');
    const filtered = currentCategory === 'all'
      ? allControls
      : allControls.filter(c => {
          if (currentCategory === 'policy') return c.category === 'policy' || c.category === 'compliance';
          if (currentCategory === 'forensic') return c.category === 'forensic' || c.category === 'classification';
          return c.category === currentCategory;
        });

    if (filtered.length === 0) {
      grid.innerHTML = `<div style="color:var(--text-muted); grid-column:1/-1; text-align:center; padding:3rem;">No controls in this category.</div>`;
      return;
    }

    grid.innerHTML = filtered.map(c => {
      const hasPending = !!c.pending_version;
      const pendingDiff = hasPending ? JSON.stringify(c.pending_version.diff || {}) : '';

      return `
        <div class="card" style="display:flex; flex-direction:column; justify-content:space-between; padding:1.25rem; border:1px solid ${hasPending ? 'var(--warning-color, #eab308)' : 'var(--border-color)'}; border-radius:10px; background:var(--bg-surface);">
          <div>
            <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:0.5rem;">
              <span class="badge" style="background:var(--bg-card); color:var(--text-muted); font-size:0.75rem; text-transform:uppercase;">
                ${c.category}
              </span>
              <span class="badge badge-success" style="font-size:0.75rem;">
                v${c.version} Active
              </span>
            </div>
            <h3 style="font-size:1.05rem; font-weight:600; margin-bottom:0.4rem; color:var(--text-main);">${c.name}</h3>
            <p style="font-size:0.82rem; color:var(--text-muted); line-height:1.4; margin-bottom:0.75rem; height:45px; overflow:hidden; text-overflow:ellipsis;">
              ${c.description}
            </p>

            <!-- Intended Error Classes -->
            <div style="display:flex; gap:0.35rem; flex-wrap:wrap; margin-bottom:0.75rem;">
              ${(c.intended_error_classes || []).map(e => `
                <span style="font-size:0.7rem; padding:2px 6px; border-radius:4px; background:var(--bg-input); color:var(--accent-primary); font-family:var(--font-mono);">
                  ${e}
                </span>
              `).join('')}
            </div>

            <!-- Parameters preview -->
            <details style="font-size:0.78rem; margin-bottom:0.75rem;">
              <summary style="cursor:pointer; color:var(--accent-primary); font-weight:500;">View Active Parameters</summary>
              <pre style="margin-top:0.5rem; padding:0.5rem; background:var(--bg-card); border-radius:6px; font-family:var(--font-mono); font-size:0.72rem; overflow-x:auto;">${JSON.stringify(c.params, null, 2)}</pre>
            </details>
          </div>

          <!-- Pending Maker-Checker Banner if applicable -->
          <div>
            ${hasPending ? `
              <div style="background:rgba(234,179,8,0.1); border:1px solid rgba(234,179,8,0.3); border-radius:6px; padding:0.6rem; margin-bottom:0.75rem; font-size:0.8rem;">
                <div style="font-weight:600; color:#ca8a04; margin-bottom:0.25rem;">
                  v${c.pending_version.version} Pending Checker Review
                </div>
                <div style="color:var(--text-muted); font-size:0.75rem; margin-bottom:0.4rem;">
                  Proposed by: ${c.pending_version.created_by}
                </div>
                <div style="display:flex; gap:0.5rem;">
                  <button class="btn btn-sm btn-success btn-approve-version" data-key="${c.key}" data-vid="${c.pending_version.id}" style="font-size:0.75rem; padding:3px 8px;">
                    Approve (Checker)
                  </button>
                  <button class="btn btn-sm btn-danger btn-reject-version" data-key="${c.key}" data-vid="${c.pending_version.id}" style="font-size:0.75rem; padding:3px 8px;">
                    Reject
                  </button>
                </div>
              </div>
            ` : ''}

            <div style="display:flex; justify-content:flex-end;">
              <button class="btn btn-sm btn-secondary btn-edit-control" data-key="${c.key}" data-name="${c.name}" data-params='${JSON.stringify(c.params)}' style="font-size:0.8rem;">
                Propose Edit (Maker)
              </button>
            </div>
          </div>
        </div>
      `;
    }).join('');

    attachCardListeners();
  }

  function attachCardListeners() {
    // Propose Edit Modal
    container.querySelectorAll('.btn-edit-control').forEach(btn => {
      btn.addEventListener('click', () => {
        const key = btn.dataset.key;
        const name = btn.dataset.name;
        const params = JSON.parse(btn.dataset.params || '{}');

        container.querySelector('#edit-control-key').value = key;
        container.querySelector('#edit-modal-title').textContent = `Propose Edit: ${name}`;
        container.querySelector('#edit-params-json').value = JSON.stringify(params, null, 2);
        container.querySelector('#edit-rationale').value = '';
        container.querySelector('#edit-control-modal').style.display = 'flex';
      });
    });

    // Checker Approve
    container.querySelectorAll('.btn-approve-version').forEach(btn => {
      btn.addEventListener('click', async () => {
        const key = btn.dataset.key;
        const vid = btn.dataset.vid;
        const comment = prompt('Checker review comment (optional):', 'Approved');
        if (comment === null) return;

        try {
          await api.post(`/controls/${key}/versions/${vid}/decide`, { action: 'approve', comment });
          alert(`Version approved! Control '${key}' updated.`);
          await loadControls();
        } catch (err) {
          alert(`Approval failed: ${err.message}`);
        }
      });
    });

    // Checker Reject
    container.querySelectorAll('.btn-reject-version').forEach(btn => {
      btn.addEventListener('click', async () => {
        const key = btn.dataset.key;
        const vid = btn.dataset.vid;
        const comment = prompt('Reason for rejection:');
        if (!comment) return;

        try {
          await api.post(`/controls/${key}/versions/${vid}/decide`, { action: 'reject', comment });
          alert(`Version rejected.`);
          await loadControls();
        } catch (err) {
          alert(`Rejection failed: ${err.message}`);
        }
      });
    });
  }

  // Filter chips
  container.querySelectorAll('#control-category-filters .filter-chip').forEach(btn => {
    btn.addEventListener('click', () => {
      container.querySelectorAll('#control-category-filters .filter-chip').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      currentCategory = btn.dataset.cat;
      renderGrid();
    });
  });

  // Close modals
  container.querySelector('#btn-close-edit-modal').addEventListener('click', () => {
    container.querySelector('#edit-control-modal').style.display = 'none';
  });
  container.querySelector('#btn-cancel-edit').addEventListener('click', () => {
    container.querySelector('#edit-control-modal').style.display = 'none';
  });
  container.querySelector('#btn-cancel-run').addEventListener('click', () => {
    container.querySelector('#run-controls-modal').style.display = 'none';
  });
  container.querySelector('#btn-close-findings').addEventListener('click', () => {
    container.querySelector('#findings-modal').style.display = 'none';
  });

  // Submit Propose Edit
  container.querySelector('#form-propose-edit').addEventListener('submit', async (e) => {
    e.preventDefault();
    const key = container.querySelector('#edit-control-key').value;
    const jsonStr = container.querySelector('#edit-params-json').value;
    const rationale = container.querySelector('#edit-rationale').value;

    let parsedParams;
    try {
      parsedParams = JSON.parse(jsonStr);
    } catch {
      alert('Invalid JSON parameters format');
      return;
    }

    try {
      await api.post(`/controls/${key}/edit`, { params: parsedParams, rationale });
      container.querySelector('#edit-control-modal').style.display = 'none';
      alert('Draft version submitted! Requires checker approval to take effect.');
      await loadControls();
    } catch (err) {
      alert(`Submission failed: ${err.message}`);
    }
  });

  // Run Suite Button
  container.querySelector('#btn-run-suite').addEventListener('click', async () => {
    try {
      const res = await api.get('/datasets');
      const datasets = res.datasets || [];
      const select = container.querySelector('#run-dataset-select');

      if (datasets.length === 0) {
        select.innerHTML = `<option value="">No datasets found. Generate one first!</option>`;
      } else {
        select.innerHTML = datasets.map(d => `<option value="${d.id}">${d.name} (${d.period_start} to ${d.period_end})</option>`).join('');
      }

      container.querySelector('#run-controls-modal').style.display = 'flex';
    } catch (err) {
      alert(`Failed to load datasets: ${err.message}`);
    }
  });

  // Confirm Run Suite
  container.querySelector('#btn-confirm-run').addEventListener('click', async () => {
    const datasetId = container.querySelector('#run-dataset-select').value;
    if (!datasetId) {
      alert('Please select a dataset');
      return;
    }

    container.querySelector('#run-controls-modal').style.display = 'none';
    const runBtn = container.querySelector('#btn-run-suite');
    runBtn.disabled = true;
    runBtn.textContent = 'Running 15 controls...';

    try {
      const runResult = await api.post('/controls/run', { dataset_id: datasetId });
      showFindingsModal(runResult);
    } catch (err) {
      alert(`Execution failed: ${err.message}`);
    } finally {
      runBtn.disabled = false;
      runBtn.innerHTML = `
        <svg width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><polygon points="5 3 19 12 5 21 5 3"/></svg>
        Run Suite
      `;
    }
  });

  function showFindingsModal(run) {
    const modal = container.querySelector('#findings-modal');
    container.querySelector('#findings-title').textContent = `Execution Complete (${run.duration_ms || 0} ms)`;
    
    container.querySelector('#findings-summary').innerHTML = `
      <div class="badge badge-info">Total Findings: ${run.total_findings}</div>
      <div class="badge badge-danger">Critical: ${run.findings_by_severity?.critical || 0}</div>
      <div class="badge badge-warning">High: ${run.findings_by_severity?.high || 0}</div>
      <div class="badge badge-secondary">Medium: ${run.findings_by_severity?.medium || 0}</div>
    `;

    const findings = run.findings || [];
    if (findings.length === 0) {
      container.querySelector('#findings-table-container').innerHTML = `
        <div style="padding:2rem; text-align:center; color:var(--success-color);">
          Zero findings generated! All 15 financial controls passed cleanly against the dataset.
        </div>
      `;
    } else {
      container.querySelector('#findings-table-container').innerHTML = `
        <table class="table" style="font-size:0.85rem; width:100%;">
          <thead>
            <tr>
              <th>Severity</th>
              <th>Control</th>
              <th>Description</th>
              <th>Amount</th>
              <th>Row Refs</th>
            </tr>
          </thead>
          <tbody>
            ${findings.map(f => `
              <tr>
                <td>
                  <span class="badge ${f.severity === 'critical' ? 'badge-danger' : f.severity === 'high' ? 'badge-warning' : 'badge-info'}" style="font-size:0.75rem;">
                    ${f.severity}
                  </span>
                </td>
                <td style="font-family:var(--font-mono); font-size:0.8rem;">${f.control_id}</td>
                <td>${f.description}</td>
                <td style="font-family:var(--font-mono);">${f.amount != null ? f.amount.toLocaleString(undefined, {minimumFractionDigits: 2}) : '—'}</td>
                <td style="font-family:var(--font-mono); font-size:0.75rem;">${(f.affected_row_refs || []).slice(0, 3).join(', ')}</td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      `;
    }

    modal.style.display = 'flex';
  }

  await loadControls();
}
