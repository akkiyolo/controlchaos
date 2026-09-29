/**
 * Variance Studio Page: Actual vs Budget comparisons and AI Verified Commentary
 */

import { api } from "../api.js";

export const VariancePage = {
  datasets: [],
  selectedDatasetId: null,
  selectedPeriod: "2025-01",
  selectedEntity: "",

  async render() {
    return `
      <div class="page-container" style="max-width: 1400px; margin: 0 auto; padding: 24px;">
        <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 24px;">
          <div>
            <h1 style="font-size: 24px; font-weight: 700; margin: 0 0 6px 0;">Variance Studio & AI Commentary</h1>
            <p style="color: var(--text-muted); margin: 0; font-size: 14px;">
              Multi-dimensional ledger variance analysis with verified AI management explanations grounded in GL lines.
            </p>
          </div>
          <div style="display: flex; gap: 12px; align-items: center;">
            <div>
              <label style="font-size: 11px; text-transform: uppercase; color: var(--text-muted); font-weight: 600; display: block; margin-bottom: 4px;">Dataset</label>
              <select id="variance-dataset-select" class="form-control" style="min-width: 220px;"></select>
            </div>
            <div>
              <label style="font-size: 11px; text-transform: uppercase; color: var(--text-muted); font-weight: 600; display: block; margin-bottom: 4px;">Period</label>
              <select id="variance-period-select" class="form-control" style="width: 120px;">
                <option value="2025-01">2025-01</option>
                <option value="2024-12">2024-12</option>
              </select>
            </div>
            <button id="refresh-variance-btn" class="btn btn-primary" style="margin-top: 18px;">Refresh</button>
          </div>
        </div>

        <!-- KPI Cards -->
        <div id="variance-kpis" style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 24px;">
          <div class="card" style="padding: 16px; background: var(--bg-surface); border: 1px solid var(--border-subtle); border-radius: 8px;">
            <div style="font-size: 11px; text-transform: uppercase; color: var(--text-muted); font-weight: 600;">Actual Revenue</div>
            <div id="kpi-act-rev" style="font-size: 22px; font-weight: 700; margin-top: 6px;">$0.00</div>
          </div>
          <div class="card" style="padding: 16px; background: var(--bg-surface); border: 1px solid var(--border-subtle); border-radius: 8px;">
            <div style="font-size: 11px; text-transform: uppercase; color: var(--text-muted); font-weight: 600;">Budget Revenue</div>
            <div id="kpi-bud-rev" style="font-size: 22px; font-weight: 700; margin-top: 6px;">$0.00</div>
          </div>
          <div class="card" style="padding: 16px; background: var(--bg-surface); border: 1px solid var(--border-subtle); border-radius: 8px;">
            <div style="font-size: 11px; text-transform: uppercase; color: var(--text-muted); font-weight: 600;">Actual Expenses</div>
            <div id="kpi-act-exp" style="font-size: 22px; font-weight: 700; margin-top: 6px;">$0.00</div>
          </div>
          <div class="card" style="padding: 16px; background: var(--bg-surface); border: 1px solid var(--border-subtle); border-radius: 8px;">
            <div style="font-size: 11px; text-transform: uppercase; color: var(--text-muted); font-weight: 600;">Net Income Variance</div>
            <div id="kpi-net-var" style="font-size: 22px; font-weight: 700; margin-top: 6px;">$0.00</div>
          </div>
        </div>

        <!-- Table View -->
        <div class="card" style="padding: 20px; background: var(--bg-surface); border: 1px solid var(--border-subtle); border-radius: 8px;">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
            <h3 style="margin: 0; font-size: 16px;">General Ledger Accounts Breakdown</h3>
            <span style="font-size: 12px; color: var(--text-muted);">Thresholds: Watch > 10% | Breach > 20%</span>
          </div>
          <div id="variance-table-container">
            <div style="text-align: center; padding: 40px; color: var(--text-muted);">Loading variance data...</div>
          </div>
        </div>
      </div>

      <!-- AI Commentary Modal -->
      <div id="commentary-modal" class="modal-overlay" style="display: none; position: fixed; inset: 0; background: rgba(0,0,0,0.7); z-index: 999; align-items: center; justify-content: center;">
        <div class="card" style="width: 680px; max-width: 90vw; background: var(--bg-surface); padding: 24px; border-radius: 8px; border: 1px solid var(--border-subtle);">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
            <div style="display: flex; align-items: center; gap: 8px;">
              <span style="color: var(--color-primary); font-size: 20px;">✨</span>
              <h3 style="margin: 0; font-size: 18px;">Variance Analyst Commentary</h3>
            </div>
            <button id="close-commentary-modal" class="btn btn-ghost btn-sm">&times;</button>
          </div>
          <div id="commentary-modal-content">
            <div style="text-align: center; padding: 30px; color: var(--text-muted);">Generating grounded commentary...</div>
          </div>
        </div>
      </div>
    `;
  },

  async mount() {
    await this.loadDatasets();
    this.bindEvents();
    if (this.selectedDatasetId) {
      await this.loadVarianceData();
    }
  },

  async loadDatasets() {
    try {
      this.datasets = await api.get("/datasets");
      const sel = document.getElementById("variance-dataset-select");
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
    const sel = document.getElementById("variance-dataset-select");
    if (sel) {
      sel.onchange = () => {
        this.selectedDatasetId = sel.value;
        this.loadVarianceData();
      };
    }

    const perSel = document.getElementById("variance-period-select");
    if (perSel) {
      perSel.onchange = () => {
        this.selectedPeriod = perSel.value;
        this.loadVarianceData();
      };
    }

    const refBtn = document.getElementById("refresh-variance-btn");
    if (refBtn) {
      refBtn.onclick = () => this.loadVarianceData();
    }

    const closeBtn = document.getElementById("close-commentary-modal");
    if (closeBtn) {
      closeBtn.onclick = () => {
        document.getElementById("commentary-modal").style.display = "none";
      };
    }
  },

  async loadVarianceData() {
    if (!this.selectedDatasetId) return;
    const container = document.getElementById("variance-table-container");
    if (!container) return;
    container.innerHTML = `<div style="text-align: center; padding: 40px; color: var(--text-muted);">Loading variance data...</div>`;

    try {
      const data = await api.get(`/finance/variance-studio?dataset_id=${this.selectedDatasetId}&period=${this.selectedPeriod}`);

      // Update KPI cards
      document.getElementById("kpi-act-rev").innerText = `$${(data.total_actual_revenue || 0).toLocaleString(undefined, {minimumFractionDigits: 2})}`;
      document.getElementById("kpi-bud-rev").innerText = `$${(data.total_budget_revenue || 0).toLocaleString(undefined, {minimumFractionDigits: 2})}`;
      document.getElementById("kpi-act-exp").innerText = `$${(data.total_actual_expense || 0).toLocaleString(undefined, {minimumFractionDigits: 2})}`;
      const netVar = data.net_income_variance || 0;
      const netEl = document.getElementById("kpi-net-var");
      netEl.innerText = `${netVar >= 0 ? '+' : ''}$${netVar.toLocaleString(undefined, {minimumFractionDigits: 2})}`;
      netEl.style.color = netVar >= 0 ? "var(--color-success)" : "var(--color-danger)";

      const rows = data.rows || [];
      if (rows.length === 0) {
        container.innerHTML = `<div style="text-align: center; padding: 40px; color: var(--text-muted);">No GL activity found for this period.</div>`;
        return;
      }

      container.innerHTML = `
        <table class="table" style="width: 100%; border-collapse: collapse; font-size: 13px;">
          <thead>
            <tr style="border-bottom: 2px solid var(--border-subtle); text-align: left;">
              <th style="padding: 10px;">Account</th>
              <th style="padding: 10px;">Name</th>
              <th style="padding: 10px;">Type</th>
              <th style="padding: 10px; text-align: right;">Actual</th>
              <th style="padding: 10px; text-align: right;">Budget</th>
              <th style="padding: 10px; text-align: right;">Variance ($)</th>
              <th style="padding: 10px; text-align: right;">Variance (%)</th>
              <th style="padding: 10px; text-align: center;">Status</th>
              <th style="padding: 10px; text-align: right;">Action</th>
            </tr>
          </thead>
          <tbody>
            ${rows.map(r => {
              const statusClass = r.status === 'breach' ? 'badge-danger' : (r.status === 'watch' ? 'badge-warning' : 'badge-success');
              const varColor = r.is_adverse ? 'var(--color-danger)' : 'var(--text-main)';
              return `
                <tr style="border-bottom: 1px solid var(--border-subtle);">
                  <td style="padding: 10px; font-family: monospace; font-weight: 600;">${r.account_code}</td>
                  <td style="padding: 10px;">${r.account_name}</td>
                  <td style="padding: 10px;"><span style="text-transform: capitalize; font-size: 11px; opacity: 0.8;">${r.account_type}</span></td>
                  <td style="padding: 10px; text-align: right;">$${r.actual.toLocaleString(undefined, {minimumFractionDigits: 2})}</td>
                  <td style="padding: 10px; text-align: right;">$${r.budget.toLocaleString(undefined, {minimumFractionDigits: 2})}</td>
                  <td style="padding: 10px; text-align: right; color: ${varColor}; font-weight: 600;">
                    ${r.variance_amount >= 0 ? '+' : ''}$${r.variance_amount.toLocaleString(undefined, {minimumFractionDigits: 2})}
                  </td>
                  <td style="padding: 10px; text-align: right; color: ${varColor};">
                    ${(r.variance_pct * 100).toFixed(1)}%
                  </td>
                  <td style="padding: 10px; text-align: center;">
                    <span class="badge ${statusClass}">${r.status.toUpperCase()}</span>
                  </td>
                  <td style="padding: 10px; text-align: right;">
                    <button class="btn btn-sm btn-secondary explain-ai-btn" data-code="${r.account_code}" data-actual="${r.actual}" data-budget="${r.budget}" style="display: inline-flex; align-items: center; gap: 4px;">
                      <span>Explain</span>
                      <span style="color: var(--color-primary);">✨</span>
                    </button>
                  </td>
                </tr>
              `;
            }).join("")}
          </tbody>
        </table>
      `;

      // Bind explain with AI buttons
      container.querySelectorAll(".explain-ai-btn").forEach(btn => {
        btn.onclick = async () => {
          const code = btn.dataset.code;
          const act = parseFloat(btn.dataset.actual);
          const bud = parseFloat(btn.dataset.budget);
          const modal = document.getElementById("commentary-modal");
          const content = document.getElementById("commentary-modal-content");
          modal.style.display = "flex";
          content.innerHTML = `<div style="text-align: center; padding: 40px; color: var(--text-muted);">Consulting Variance Analyst Agent...</div>`;

          try {
            const aiRes = await api.post("/finance/variance-studio/ai-commentary", {
              dataset_id: this.selectedDatasetId,
              account_code: code,
              period: this.selectedPeriod,
              actual: act,
              budget: bud,
            });

            content.innerHTML = `
              <div style="background: var(--bg-elevated); padding: 16px; border-radius: 6px; margin-bottom: 16px; border-left: 4px solid var(--color-primary);">
                <div style="font-size: 11px; text-transform: uppercase; font-weight: 700; color: var(--color-primary); margin-bottom: 6px;">Executive Management Commentary</div>
                <div style="font-size: 14px; line-height: 1.6;">${aiRes.management_commentary}</div>
              </div>

              <div style="margin-bottom: 16px;">
                <h4 style="margin: 0 0 8px 0; font-size: 13px; text-transform: uppercase; color: var(--text-muted);">Grounded Factual Drivers</h4>
                <ul style="margin: 0; padding-left: 20px; font-size: 13px; line-height: 1.6;">
                  ${aiRes.factual_drivers.map(d => `<li>${d}</li>`).join("")}
                </ul>
              </div>

              <div style="display: flex; justify-content: space-between; align-items: center; border-top: 1px solid var(--border-subtle); padding-top: 12px;">
                <span style="font-size: 12px; color: var(--text-muted);">Analyst Classification:</span>
                <span class="badge ${aiRes.is_legitimate_or_anomalous.includes('anomalous') ? 'badge-danger' : 'badge-success'}">
                  ${aiRes.is_legitimate_or_anomalous.replace(/_/g, ' ').toUpperCase()}
                </span>
              </div>
            `;
          } catch (err) {
            content.innerHTML = `<div style="color: var(--color-danger); padding: 20px;">Failed to generate AI commentary: ${err.message}</div>`;
          }
        };
      });

    } catch (e) {
      container.innerHTML = `<div style="color: var(--color-danger); padding: 20px;">Error loading variance data: ${e.message}</div>`;
    }
  },
};
