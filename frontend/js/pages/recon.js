/**
 * Reconciliation Workbench Page: Subledger Recon Breaks & Resolution
 */

import { api } from "../api.js";

export const ReconPage = {
  datasets: [],
  selectedDatasetId: null,

  async render() {
    return `
      <div class="page-container" style="max-width: 1400px; margin: 0 auto; padding: 24px;">
        <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 24px;">
          <div>
            <h1 style="font-size: 24px; font-weight: 700; margin: 0 0 6px 0;">Reconciliation Workbench</h1>
            <p style="color: var(--text-muted); margin: 0; font-size: 14px;">
              Sub-ledger to General Ledger reconciliation breaks, aging telemetry, and audit-trailed resolution workflows.
            </p>
          </div>
          <div style="display: flex; gap: 12px; align-items: center;">
            <select id="recon-dataset-select" class="form-control" style="min-width: 240px;"></select>
            <button id="refresh-recon-btn" class="btn btn-primary">Refresh</button>
          </div>
        </div>

        <!-- Subledgers Overview Cards -->
        <h3 style="margin: 0 0 12px 0; font-size: 15px; text-transform: uppercase; color: var(--text-muted); font-weight: 600;">Control Accounts Status</h3>
        <div id="recon-subledgers-container" style="display: grid; grid-template-columns: repeat(5, 1fr); gap: 14px; margin-bottom: 24px;">
          <div style="text-align: center; padding: 20px; color: var(--text-muted); grid-column: 1 / -1;">Loading subledgers...</div>
        </div>

        <!-- Aging Breakdown Cards -->
        <h3 style="margin: 0 0 12px 0; font-size: 15px; text-transform: uppercase; color: var(--text-muted); font-weight: 600;">Break Aging Distribution</h3>
        <div id="recon-aging-container" style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; margin-bottom: 24px;">
          <div class="card" style="padding: 14px; background: var(--bg-surface); border: 1px solid var(--border-subtle); border-radius: 6px;">
            <div style="font-size: 11px; text-transform: uppercase; color: var(--text-muted); font-weight: 600;">&lt; 15 Days</div>
            <div id="aging-lt15" style="font-size: 20px; font-weight: 700; margin-top: 4px;">0</div>
          </div>
          <div class="card" style="padding: 14px; background: var(--bg-surface); border: 1px solid var(--border-subtle); border-radius: 6px;">
            <div style="font-size: 11px; text-transform: uppercase; color: var(--text-muted); font-weight: 600;">15 &ndash; 30 Days</div>
            <div id="aging-1530" style="font-size: 20px; font-weight: 700; margin-top: 4px;">0</div>
          </div>
          <div class="card" style="padding: 14px; background: var(--bg-surface); border: 1px solid var(--border-subtle); border-radius: 6px;">
            <div style="font-size: 11px; text-transform: uppercase; color: var(--text-muted); font-weight: 600;">30 &ndash; 60 Days</div>
            <div id="aging-3060" style="font-size: 20px; font-weight: 700; margin-top: 4px;">0</div>
          </div>
          <div class="card" style="padding: 14px; background: var(--bg-surface); border: 1px solid var(--border-subtle); border-radius: 6px;">
            <div style="font-size: 11px; text-transform: uppercase; color: var(--text-muted); font-weight: 600;">&gt; 60 Days (Critical)</div>
            <div id="aging-gt60" style="font-size: 20px; font-weight: 700; margin-top: 4px; color: var(--color-danger);">0</div>
          </div>
        </div>

        <!-- Detailed Breaks Table -->
        <div class="card" style="padding: 20px; background: var(--bg-surface); border: 1px solid var(--border-subtle); border-radius: 8px;">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
            <div>
              <h3 style="margin: 0 0 4px 0; font-size: 16px;">Reconciliation Breaks & Exceptions</h3>
              <span style="font-size: 13px; color: var(--text-muted);">Unmatched subledger items and clerical variance exceptions requiring resolution.</span>
            </div>
          </div>
          <div id="breaks-table-container">
            <div style="text-align: center; padding: 40px; color: var(--text-muted);">Loading reconciliation breaks...</div>
          </div>
        </div>
      </div>

      <!-- Resolve Modal -->
      <div id="resolve-modal" class="modal-overlay" style="display: none; position: fixed; inset: 0; background: rgba(0,0,0,0.7); z-index: 999; align-items: center; justify-content: center;">
        <div class="card" style="width: 560px; max-width: 90vw; background: var(--bg-surface); padding: 24px; border-radius: 8px;">
          <h3 id="resolve-modal-title" style="margin: 0 0 16px 0; font-size: 18px;">Resolve Reconciliation Break</h3>
          <div style="margin-bottom: 16px;">
            <label style="font-size: 12px; font-weight: 600; text-transform: uppercase;">Resolution Action</label>
            <select id="resolve-action-select" class="form-control" style="width: 100%; margin-top: 6px;">
              <option value="resolve">Post Adjusting Journal & Resolve</option>
              <option value="investigate">Flag for Forensic Investigation</option>
              <option value="write_off">Write-Off Immaterial Variance</option>
            </select>
          </div>
          <div style="margin-bottom: 16px;">
            <label style="font-size: 12px; font-weight: 600; text-transform: uppercase;">Auditor Rationale & Notes</label>
            <textarea id="resolve-notes" class="form-control" rows="3" placeholder="Explain the root cause and adjustment documentation..." style="width: 100%; margin-top: 6px;"></textarea>
          </div>
          <div style="display: flex; justify-content: flex-end; gap: 10px;">
            <button id="resolve-cancel-btn" class="btn btn-secondary">Cancel</button>
            <button id="resolve-confirm-btn" class="btn btn-primary">Submit Resolution</button>
          </div>
        </div>
      </div>
    `;
  },

  async mount() {
    await this.loadDatasets();
    this.bindEvents();
    if (this.selectedDatasetId) {
      await this.loadReconData();
    }
  },

  async loadDatasets() {
    try {
      this.datasets = await api.get("/datasets");
      const sel = document.getElementById("recon-dataset-select");
      if (!sel) return;
      sel.innerHTML = this.datasets.map(d => `
        <option value="${d.id}" ${d.is_baseline ? 'selected' : ''}>${d.name} (${d.period_start})</option>
      `).join("");
      if (this.datasets.length > 0) {
        this.selectedDatasetId = sel.value;
      }
    } catch (e) {
      console.error("Failed to load datasets:", e);
    }
  },

  bindEvents() {
    const sel = document.getElementById("recon-dataset-select");
    if (sel) {
      sel.onchange = () => {
        this.selectedDatasetId = sel.value;
        this.loadReconData();
      };
    }
    const refBtn = document.getElementById("refresh-recon-btn");
    if (refBtn) {
      refBtn.onclick = () => this.loadReconData();
    }

    const cancelBtn = document.getElementById("resolve-cancel-btn");
    if (cancelBtn) {
      cancelBtn.onclick = () => {
        document.getElementById("resolve-modal").style.display = "none";
      };
    }
  },

  async loadReconData() {
    if (!this.selectedDatasetId) return;

    try {
      const data = await api.get(`/finance/reconciliation?dataset_id=${this.selectedDatasetId}`);

      // Subledgers overview cards
      const subContainer = document.getElementById("recon-subledgers-container");
      subContainer.innerHTML = (data.subledgers || []).map(s => {
        const isBalanced = s.break_count === 0 && Math.abs(s.variance) < 1.0;
        return `
          <div class="card" style="padding: 14px; background: var(--bg-surface); border: 1px solid ${isBalanced ? 'var(--border-subtle)' : 'var(--color-danger)'}; border-radius: 6px;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
              <strong style="font-size: 13px;">${s.subledger_type}</strong>
              <span class="badge ${isBalanced ? 'badge-success' : 'badge-danger'}" style="font-size: 10px;">${isBalanced ? 'BALANCED' : `${s.break_count} BREAKS`}</span>
            </div>
            <div style="font-size: 11px; color: var(--text-muted);">GL: $${s.gl_balance.toLocaleString(undefined, {minimumFractionDigits: 2})}</div>
            <div style="font-size: 11px; color: var(--text-muted);">Sub: $${s.subledger_balance.toLocaleString(undefined, {minimumFractionDigits: 2})}</div>
            <div style="font-size: 12px; font-weight: 700; margin-top: 6px; color: ${isBalanced ? 'var(--color-success)' : 'var(--color-danger)'};">
              Var: ${s.variance >= 0 ? '+' : ''}$${s.variance.toLocaleString(undefined, {minimumFractionDigits: 2})}
            </div>
          </div>
        `;
      }).join("");

      // Aging counts
      const aging = data.aging_breakdown || {};
      document.getElementById("aging-lt15").innerText = aging["<15d"] || 0;
      document.getElementById("aging-1530").innerText = aging["15-30d"] || 0;
      document.getElementById("aging-3060").innerText = aging["30-60d"] || 0;
      document.getElementById("aging-gt60").innerText = aging[">60d"] || 0;

      // Breaks table
      const breaks = data.breaks || [];
      const tableContainer = document.getElementById("breaks-table-container");
      if (breaks.length === 0) {
        tableContainer.innerHTML = `
          <div style="text-align: center; padding: 40px; color: var(--color-success); font-weight: 600;">
            ✓ All sub-ledgers fully reconciled with General Ledger. Zero breaks detected.
          </div>
        `;
        return;
      }

      tableContainer.innerHTML = `
        <table class="table" style="width: 100%; border-collapse: collapse; font-size: 13px;">
          <thead>
            <tr style="border-bottom: 2px solid var(--border-subtle); text-align: left;">
              <th style="padding: 10px;">Break ID</th>
              <th style="padding: 10px;">Subledger</th>
              <th style="padding: 10px;">Ref ID</th>
              <th style="padding: 10px;">Counterparty</th>
              <th style="padding: 10px; text-align: right;">Amount</th>
              <th style="padding: 10px;">Aging</th>
              <th style="padding: 10px;">Status</th>
              <th style="padding: 10px; text-align: right;">Action</th>
            </tr>
          </thead>
          <tbody>
            ${breaks.map(b => `
              <tr style="border-bottom: 1px solid var(--border-subtle);">
                <td style="padding: 10px; font-family: monospace; font-weight: 600;">${b.break_id}</td>
                <td style="padding: 10px;"><span class="badge badge-info">${b.subledger_type}</span></td>
                <td style="padding: 10px; font-family: monospace;">${b.ref_id}</td>
                <td style="padding: 10px;">${b.counterparty}</td>
                <td style="padding: 10px; text-align: right; font-weight: 600; color: var(--color-danger);">$${b.subledger_amount.toLocaleString(undefined, {minimumFractionDigits: 2})}</td>
                <td style="padding: 10px;">
                  <span class="badge ${b.aging_days > 45 ? 'badge-danger' : (b.aging_days > 20 ? 'badge-warning' : 'badge-success')}">
                    ${b.aging_days}d (${b.aging_bucket})
                  </span>
                </td>
                <td style="padding: 10px;">
                  <span class="badge ${b.status === 'open' ? 'badge-warning' : 'badge-success'}">${b.status.toUpperCase()}</span>
                </td>
                <td style="padding: 10px; text-align: right;">
                  <button class="btn btn-sm btn-secondary resolve-break-btn" data-id="${b.break_id}">Resolve</button>
                </td>
              </tr>
            `).join("")}
          </tbody>
        </table>
      `;

      // Bind resolve break buttons
      tableContainer.querySelectorAll(".resolve-break-btn").forEach(btn => {
        btn.onclick = () => {
          const breakId = btn.dataset.id;
          const modal = document.getElementById("resolve-modal");
          const title = document.getElementById("resolve-modal-title");
          const confirmBtn = document.getElementById("resolve-confirm-btn");
          title.innerText = `Resolve Reconciliation Break ${breakId}`;
          modal.style.display = "flex";

          confirmBtn.onclick = async () => {
            const action = document.getElementById("resolve-action-select").value;
            const notes = document.getElementById("resolve-notes").value;
            try {
              await api.post("/finance/reconciliation/resolve-break", {
                break_id: breakId,
                action: action,
                resolution_notes: notes || "Auditor validated adjustment.",
              });
              modal.style.display = "none";
              alert(`Break ${breakId} successfully updated with action: ${action}`);
              await this.loadReconData();
            } catch (err) {
              alert(`Error: ${err.message}`);
            }
          };
        };
      });

    } catch (e) {
      console.error("Failed to load reconciliation data:", e);
    }
  },
};
