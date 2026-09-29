/**
 * Mutation Lab & Campaign Builder Component for ControlChaos
 * Displays the 20 financial error mutators, allows configuring campaigns,
 * and viewing ground truth mutation ledgers.
 */

import { api } from '../services/api.js';

export function renderMutationsPage(container) {
  container.innerHTML = `
    <div class="page-header" style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:1.5rem;">
      <div>
        <h1 style="font-size:1.75rem; font-weight:700; color:var(--text-main); margin-bottom:0.25rem;">Mutation Lab & Catalog</h1>
        <p style="color:var(--text-muted); font-size:0.9rem;">
          20 institutional accounting error injection mutators with magnitude, stealth, and location tuning.
        </p>
      </div>
      <div style="display:flex; gap:0.75rem;">
        <button id="btn-open-campaign-modal" class="btn btn-primary" style="display:flex; align-items:center; gap:0.5rem;">
          <svg width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M12 5v14M5 12h14"/></svg>
          Build Mutation Campaign
        </button>
      </div>
    </div>

    <!-- Active Mutated Datasets Quick Select -->
    <div class="card" style="padding:1rem 1.25rem; margin-bottom:1.5rem; background:var(--bg-surface); border:1px solid var(--border-color); border-radius:10px; display:flex; align-items:center; justify-content:space-between;">
      <div style="display:flex; align-items:center; gap:1rem;">
        <span style="font-size:0.85rem; font-weight:600; color:var(--text-muted);">Inspect Ground Truth Ledger:</span>
        <select id="select-mutated-dataset" style="padding:0.4rem 0.75rem; border-radius:6px; border:1px solid var(--border-color); background:var(--bg-input); color:var(--text-main); font-size:0.85rem;">
          <option value="">Select a mutated dataset...</option>
        </select>
      </div>
      <button id="btn-view-ledger" class="btn btn-sm btn-secondary" disabled>View Injected Errors</button>
    </div>

    <!-- Mutators Grid (20 items) -->
    <div id="mutators-grid" style="display:grid; grid-template-columns:repeat(auto-fill, minmax(320px, 1fr)); gap:1.25rem;">
      <div style="color:var(--text-muted); padding:2rem; text-align:center; grid-column:1/-1;">Loading mutator catalog...</div>
    </div>

    <!-- Build Campaign Modal -->
    <div id="campaign-modal" class="modal" style="display:none; position:fixed; inset:0; background:rgba(0,0,0,0.6); z-index:1000; align-items:center; justify-content:center;">
      <div class="card" style="width:100%; max-width:650px; max-height:90vh; overflow-y:auto; padding:1.75rem; background:var(--bg-surface); border:1px solid var(--border-color); border-radius:12px;">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:1rem;">
          <h3 style="font-size:1.25rem; font-weight:600;">Build Mutation Campaign</h3>
          <button id="btn-close-campaign-modal" style="background:none; border:none; color:var(--text-muted); cursor:pointer; font-size:1.25rem;">&times;</button>
        </div>
        
        <form id="form-create-campaign">
          <div class="form-group" style="margin-bottom:1rem;">
            <label style="display:block; font-size:0.85rem; font-weight:600; margin-bottom:0.25rem;">Parent Baseline Dataset</label>
            <select id="campaign-parent-dataset" required style="width:100%; padding:0.6rem; border:1px solid var(--border-color); border-radius:6px; background:var(--bg-input); color:var(--text-main);">
              <option value="">Loading baseline datasets...</option>
            </select>
          </div>

          <div class="form-group" style="margin-bottom:1rem;">
            <label style="display:block; font-size:0.85rem; font-weight:600; margin-bottom:0.25rem;">Campaign Name</label>
            <input type="text" id="campaign-name" required value="Adversarial Stress Test Q1" style="width:100%; padding:0.6rem; border:1px solid var(--border-color); border-radius:6px; background:var(--bg-input); color:var(--text-main);" />
          </div>

          <div style="display:grid; grid-template-columns:1fr 1fr; gap:1rem; margin-bottom:1rem;">
            <div class="form-group">
              <label style="display:block; font-size:0.85rem; font-weight:600; margin-bottom:0.25rem;">Default Magnitude</label>
              <select id="campaign-magnitude" style="width:100%; padding:0.6rem; border:1px solid var(--border-color); border-radius:6px; background:var(--bg-input); color:var(--text-main);">
                <option value="small">Small (Sub-material)</option>
                <option value="medium" selected>Medium (Standard)</option>
                <option value="large">Large (Material)</option>
              </select>
            </div>
            <div class="form-group">
              <label style="display:block; font-size:0.85rem; font-weight:600; margin-bottom:0.25rem;">Default Stealth</label>
              <select id="campaign-stealth" style="width:100%; padding:0.6rem; border:1px solid var(--border-color); border-radius:6px; background:var(--bg-input); color:var(--text-main);">
                <option value="obvious">Obvious (Clerical mistake)</option>
                <option value="subtle" selected>Subtle (Plausible noise)</option>
                <option value="adversarial">Adversarial (Deliberately masked)</option>
              </select>
            </div>
          </div>

          <div class="form-group" style="margin-bottom:1.25rem;">
            <label style="display:block; font-size:0.85rem; font-weight:600; margin-bottom:0.5rem;">Select Mutators to Inject</label>
            <div id="campaign-mutator-checkboxes" style="max-height:200px; overflow-y:auto; border:1px solid var(--border-color); border-radius:6px; padding:0.75rem; background:var(--bg-card); display:grid; grid-template-columns:1fr 1fr; gap:0.5rem;">
              <!-- Populated dynamically -->
            </div>
          </div>

          <div style="display:flex; justify-content:flex-end; gap:0.75rem;">
            <button type="button" id="btn-cancel-campaign" class="btn btn-secondary">Cancel</button>
            <button type="submit" id="btn-submit-campaign" class="btn btn-primary">Clone & Inject Mutants</button>
          </div>
        </form>
      </div>
    </div>

    <!-- Ground Truth Ledger Modal -->
    <div id="ledger-modal" class="modal" style="display:none; position:fixed; inset:0; background:rgba(0,0,0,0.6); z-index:1000; align-items:center; justify-content:center;">
      <div class="card" style="width:100%; max-width:850px; max-height:85vh; display:flex; flex-direction:column; padding:1.75rem; background:var(--bg-surface); border:1px solid var(--border-color); border-radius:12px;">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:1rem;">
          <h3 id="ledger-modal-title" style="font-size:1.25rem; font-weight:600;">Ground Truth Injected Mutations</h3>
          <button id="btn-close-ledger-modal" style="background:none; border:none; color:var(--text-muted); cursor:pointer; font-size:1.25rem;">&times;</button>
        </div>
        <div id="ledger-table-container" style="flex:1; overflow-y:auto;"></div>
      </div>
    </div>
  `;

  initMutationsView(container);
}

async function initMutationsView(container) {
  let catalog = [];

  async function loadCatalog() {
    try {
      const res = await api.get('/mutations/catalog');
      catalog = res.mutators || [];
      renderGrid();
      populateCheckboxes();
    } catch (err) {
      container.querySelector('#mutators-grid').innerHTML = `
        <div class="alert alert-danger" style="grid-column:1/-1;">Failed to load catalog: ${err.message}</div>
      `;
    }
  }

  async function loadDatasets() {
    try {
      const res = await api.get('/datasets');
      const all = res.datasets || [];
      const parentSelect = container.querySelector('#campaign-parent-dataset');
      const mutatedSelect = container.querySelector('#select-mutated-dataset');

      const baselines = all.filter(d => d.is_baseline);
      const mutated = all.filter(d => !d.is_baseline);

      parentSelect.innerHTML = baselines.length
        ? baselines.map(d => `<option value="${d.id}">${d.name} (${d.period_start} to ${d.period_end})</option>`).join('')
        : `<option value="">No baseline datasets found. Generate one first!</option>`;

      mutatedSelect.innerHTML = mutated.length
        ? `<option value="">Select a mutated dataset...</option>` + mutated.map(d => `<option value="${d.id}">${d.name}</option>`).join('')
        : `<option value="">No mutated datasets yet</option>`;
    } catch (err) {
      console.error('Failed to load datasets:', err);
    }
  }

  function renderGrid() {
    const grid = container.querySelector('#mutators-grid');
    grid.innerHTML = catalog.map(m => `
      <div class="card" style="padding:1.25rem; border:1px solid var(--border-color); border-radius:10px; background:var(--bg-surface); display:flex; flex-direction:column; justify-content:space-between;">
        <div>
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.5rem;">
            <span style="font-family:var(--font-mono); font-size:0.75rem; color:var(--accent-primary); background:var(--bg-card); padding:2px 6px; border-radius:4px;">
              ${m.key}
            </span>
            <span class="badge ${m.default_severity === 'critical' ? 'badge-danger' : 'badge-warning'}" style="font-size:0.75rem;">
              ${m.default_severity}
            </span>
          </div>
          <h3 style="font-size:1.05rem; font-weight:600; margin-bottom:0.4rem; color:var(--text-main);">${m.name}</h3>
          <p style="font-size:0.82rem; color:var(--text-muted); line-height:1.4;">
            ${m.description}
          </p>
        </div>
      </div>
    `).join('');
  }

  function populateCheckboxes() {
    const containerEl = container.querySelector('#campaign-mutator-checkboxes');
    containerEl.innerHTML = catalog.map((m, idx) => `
      <label style="display:flex; align-items:center; gap:0.5rem; font-size:0.8rem; cursor:pointer;">
        <input type="checkbox" name="mutator_choice" value="${m.key}" ${idx < 6 ? 'checked' : ''} />
        <span>${m.name}</span>
      </label>
    `).join('');
  }

  // Modal open/close
  container.querySelector('#btn-open-campaign-modal').addEventListener('click', () => {
    container.querySelector('#campaign-modal').style.display = 'flex';
  });
  container.querySelector('#btn-close-campaign-modal').addEventListener('click', () => {
    container.querySelector('#campaign-modal').style.display = 'none';
  });
  container.querySelector('#btn-cancel-campaign').addEventListener('click', () => {
    container.querySelector('#campaign-modal').style.display = 'none';
  });
  container.querySelector('#btn-close-ledger-modal').addEventListener('click', () => {
    container.querySelector('#ledger-modal').style.display = 'none';
  });

  // Dataset dropdown change
  const mutatedSelect = container.querySelector('#select-mutated-dataset');
  const viewLedgerBtn = container.querySelector('#btn-view-ledger');
  mutatedSelect.addEventListener('change', () => {
    viewLedgerBtn.disabled = !mutatedSelect.value;
  });

  // View Ledger button
  viewLedgerBtn.addEventListener('click', async () => {
    const datasetId = mutatedSelect.value;
    if (!datasetId) return;

    try {
      const res = await api.get(`/mutations/datasets/${datasetId}/ledger`);
      const list = res.mutations || [];
      const table = container.querySelector('#ledger-table-container');

      if (list.length === 0) {
        table.innerHTML = `<div style="padding:2rem; text-align:center; color:var(--text-muted);">No mutations recorded in this dataset.</div>`;
      } else {
        table.innerHTML = `
          <table class="table" style="font-size:0.82rem; width:100%;">
            <thead>
              <tr>
                <th>Class</th>
                <th>Expected Impact</th>
                <th>Affected Rows</th>
                <th>Stealth & Magnitude</th>
              </tr>
            </thead>
            <tbody>
              ${list.map(m => `
                <tr>
                  <td>
                    <div style="font-weight:600; color:var(--text-main);">${m.class_name}</div>
                    <div style="font-size:0.75rem; color:var(--text-muted);">${m.params?.description || ''}</div>
                  </td>
                  <td style="font-family:var(--font-mono); font-weight:600; color:var(--danger-color);">
                    $${m.expected_impact_amount.toLocaleString(undefined, {minimumFractionDigits: 2})}
                  </td>
                  <td style="font-family:var(--font-mono); font-size:0.75rem;">
                    ${(m.affected_row_refs || []).slice(0, 3).join(', ')}
                  </td>
                  <td>
                    <span class="badge badge-info" style="font-size:0.7rem;">${m.params?.stealth || 'subtle'}</span>
                    <span class="badge badge-secondary" style="font-size:0.7rem;">${m.params?.magnitude || 'medium'}</span>
                  </td>
                </tr>
              `).join('')}
            </tbody>
          </table>
        `;
      }

      container.querySelector('#ledger-modal').style.display = 'flex';
    } catch (err) {
      alert(`Failed to load ledger: ${err.message}`);
    }
  });

  // Submit campaign
  container.querySelector('#form-create-campaign').addEventListener('submit', async (e) => {
    e.preventDefault();
    const parentId = container.querySelector('#campaign-parent-dataset').value;
    const name = container.querySelector('#campaign-name').value;
    const mag = container.querySelector('#campaign-magnitude').value;
    const stealth = container.querySelector('#campaign-stealth').value;

    const checkedBoxes = Array.from(container.querySelectorAll('input[name="mutator_choice"]:checked'));
    if (checkedBoxes.length === 0) {
      alert('Please select at least one mutator to inject.');
      return;
    }

    const mutations = checkedBoxes.map(cb => ({
      class_name: cb.value,
      count: 1,
      magnitude: mag,
      stealth: stealth,
    }));

    const submitBtn = container.querySelector('#btn-submit-campaign');
    submitBtn.disabled = true;
    submitBtn.textContent = 'Cloning & Injecting...';

    try {
      const res = await api.post('/mutations/campaign', {
        parent_dataset_id: parentId,
        campaign_name: name,
        mutations: mutations,
        seed: Math.floor(Math.random() * 100000),
      });

      container.querySelector('#campaign-modal').style.display = 'none';
      alert(`Campaign complete! Injected ${res.mutations_injected} accounting errors. Expected impact: $${res.total_expected_impact.toLocaleString()}`);
      await loadDatasets();
    } catch (err) {
      alert(`Campaign failed: ${err.message}`);
    } finally {
      submitBtn.disabled = false;
      submitBtn.textContent = 'Clone & Inject Mutants';
    }
  });

  await loadCatalog();
  await loadDatasets();
}
