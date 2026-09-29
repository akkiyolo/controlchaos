/**
 * Treasury & Liquidity Workbench Page: LCR, Cash Positions, Maturity Ladder
 */

import { api } from "../api.js";

export const TreasuryPage = {
  datasets: [],
  selectedDatasetId: null,

  async render() {
    return `
      <div class="page-container" style="max-width: 1400px; margin: 0 auto; padding: 24px;">
        <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 24px;">
          <div>
            <h1 style="font-size: 24px; font-weight: 700; margin: 0 0 6px 0;">Treasury & Liquidity Workbench</h1>
            <p style="color: var(--text-muted); margin: 0; font-size: 14px;">
              Basel III Liquidity Coverage Ratio (LCR), maturity ladder cash curves, and multi-currency exposure.
            </p>
          </div>
          <div style="display: flex; gap: 12px; align-items: center;">
            <select id="treasury-dataset-select" class="form-control" style="min-width: 240px;"></select>
            <button id="refresh-treasury-btn" class="btn btn-primary">Refresh</button>
          </div>
        </div>

        <!-- Top Regulatory KPIs -->
        <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 24px;">
          <div class="card" style="padding: 16px; background: var(--bg-surface); border: 1px solid var(--border-subtle); border-radius: 8px;">
            <div style="font-size: 11px; text-transform: uppercase; color: var(--text-muted); font-weight: 600;">Total Cash & Equivalents</div>
            <div id="kpi-total-cash" style="font-size: 22px; font-weight: 700; margin-top: 6px;">$0.00</div>
          </div>
          <div class="card" style="padding: 16px; background: var(--bg-surface); border: 1px solid var(--border-subtle); border-radius: 8px;">
            <div style="font-size: 11px; text-transform: uppercase; color: var(--text-muted); font-weight: 600;">Total HQLA (Level 1 & 2)</div>
            <div id="kpi-total-hqla" style="font-size: 22px; font-weight: 700; margin-top: 6px;">$0.00</div>
          </div>
          <div class="card" style="padding: 16px; background: var(--bg-surface); border: 1px solid var(--border-subtle); border-radius: 8px;">
            <div style="font-size: 11px; text-transform: uppercase; color: var(--text-muted); font-weight: 600;">Net 30-Day Outflow</div>
            <div id="kpi-net-outflow" style="font-size: 22px; font-weight: 700; margin-top: 6px;">$0.00</div>
          </div>
          <div class="card" style="padding: 16px; background: var(--bg-surface); border: 1px solid var(--border-subtle); border-radius: 8px;">
            <div style="font-size: 11px; text-transform: uppercase; color: var(--text-muted); font-weight: 600;">Basel III LCR Ratio</div>
            <div style="display: flex; align-items: baseline; gap: 8px; margin-top: 6px;">
              <span id="kpi-lcr-val" style="font-size: 22px; font-weight: 700;">0.00</span>
              <span id="kpi-lcr-badge" class="badge badge-success">COMPLIANT</span>
            </div>
          </div>
        </div>

        <div style="display: grid; grid-template-columns: 2fr 1fr; gap: 20px; margin-bottom: 24px;">
          <!-- Maturity Ladder Table -->
          <div class="card" style="padding: 20px; background: var(--bg-surface); border: 1px solid var(--border-subtle); border-radius: 8px;">
            <h3 style="margin: 0 0 16px 0; font-size: 16px;">Maturity Ladder Liquidity Curve</h3>
            <div id="ladder-container">
              <div style="text-align: center; padding: 30px; color: var(--text-muted);">Loading maturity ladder...</div>
            </div>
          </div>

          <!-- Currency Concentration -->
          <div class="card" style="padding: 20px; background: var(--bg-surface); border: 1px solid var(--border-subtle); border-radius: 8px;">
            <h3 style="margin: 0 0 16px 0; font-size: 16px;">Multi-Currency Breakdown</h3>
            <div id="currency-container">
              <div style="text-align: center; padding: 30px; color: var(--text-muted);">Loading currency distribution...</div>
            </div>
          </div>
        </div>

        <!-- Funding Sources -->
        <div class="card" style="padding: 20px; background: var(--bg-surface); border: 1px solid var(--border-subtle); border-radius: 8px;">
          <h3 style="margin: 0 0 16px 0; font-size: 16px;">Institutional Funding Distribution</h3>
          <div id="funding-container">
            <div style="text-align: center; padding: 30px; color: var(--text-muted);">Loading funding sources...</div>
          </div>
        </div>
      </div>
    `;
  },

  async mount() {
    await this.loadDatasets();
    this.bindEvents();
    if (this.selectedDatasetId) {
      await this.loadTreasuryData();
    }
  },

  async loadDatasets() {
    try {
      this.datasets = await api.get("/datasets");
      const sel = document.getElementById("treasury-dataset-select");
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
    const sel = document.getElementById("treasury-dataset-select");
    if (sel) {
      sel.onchange = () => {
        this.selectedDatasetId = sel.value;
        this.loadTreasuryData();
      };
    }
    const refBtn = document.getElementById("refresh-treasury-btn");
    if (refBtn) {
      refBtn.onclick = () => this.loadTreasuryData();
    }
  },

  async loadTreasuryData() {
    if (!this.selectedDatasetId) return;

    try {
      const data = await api.get(`/finance/treasury?dataset_id=${this.selectedDatasetId}`);

      // Top KPIs
      document.getElementById("kpi-total-cash").innerText = `$${(data.total_cash_usd || 0).toLocaleString(undefined, {minimumFractionDigits: 2})}`;
      document.getElementById("kpi-total-hqla").innerText = `$${(data.total_hqla_usd || 0).toLocaleString(undefined, {minimumFractionDigits: 2})}`;
      document.getElementById("kpi-net-outflow").innerText = `$${(data.net_30d_outflow_usd || 0).toLocaleString(undefined, {minimumFractionDigits: 2})}`;

      const lcr = data.lcr_ratio || 0;
      document.getElementById("kpi-lcr-val").innerText = `${(lcr * 100).toFixed(1)}%`;
      const lcrBadge = document.getElementById("kpi-lcr-badge");
      lcrBadge.innerText = data.lcr_status || (lcr >= 1.0 ? "COMPLIANT" : "DEFICIT");
      lcrBadge.className = `badge ${lcr >= 1.0 ? 'badge-success' : 'badge-danger'}`;

      // Maturity ladder table
      const ladder = data.maturity_ladder || [];
      const ladderEl = document.getElementById("ladder-container");
      ladderEl.innerHTML = `
        <table class="table" style="width: 100%; border-collapse: collapse; font-size: 13px;">
          <thead>
            <tr style="border-bottom: 2px solid var(--border-subtle); text-align: left;">
              <th style="padding: 10px;">Bucket</th>
              <th style="padding: 10px; text-align: right;">Inflows</th>
              <th style="padding: 10px; text-align: right;">Outflows</th>
              <th style="padding: 10px; text-align: right;">Net Position</th>
              <th style="padding: 10px; text-align: center;">Status</th>
            </tr>
          </thead>
          <tbody>
            ${ladder.map(b => `
              <tr style="border-bottom: 1px solid var(--border-subtle);">
                <td style="padding: 10px; font-weight: 600; text-transform: uppercase;">${b.bucket}</td>
                <td style="padding: 10px; text-align: right;">$${b.inflows.toLocaleString(undefined, {minimumFractionDigits: 2})}</td>
                <td style="padding: 10px; text-align: right;">$${b.outflows.toLocaleString(undefined, {minimumFractionDigits: 2})}</td>
                <td style="padding: 10px; text-align: right; font-weight: 600; color: ${b.net >= 0 ? 'var(--color-success)' : 'var(--color-danger)'};">
                  ${b.net >= 0 ? '+' : ''}$${b.net.toLocaleString(undefined, {minimumFractionDigits: 2})}
                </td>
                <td style="padding: 10px; text-align: center;">
                  <span class="badge ${b.net >= 0 ? 'badge-success' : 'badge-danger'}">${b.net >= 0 ? 'SURPLUS' : 'DEFICIT'}</span>
                </td>
              </tr>
            `).join("")}
          </tbody>
        </table>
      `;

      // Currency distribution
      const ccy = data.by_currency || [];
      const ccyEl = document.getElementById("currency-container");
      ccyEl.innerHTML = `
        <div style="display: flex; flex-direction: column; gap: 16px;">
          ${ccy.map(c => `
            <div>
              <div style="display: flex; justify-content: space-between; font-size: 13px; margin-bottom: 6px;">
                <strong>${c.currency}</strong>
                <span>$${c.balance.toLocaleString(undefined, {minimumFractionDigits: 2})} (${c.pct}%)</span>
              </div>
              <div style="height: 8px; background: var(--bg-elevated); border-radius: 4px; overflow: hidden;">
                <div style="height: 100%; width: ${c.pct}%; background: var(--color-primary); border-radius: 4px;"></div>
              </div>
            </div>
          `).join("")}
        </div>
      `;

      // Funding sources
      const sources = data.funding_sources || [];
      const fundEl = document.getElementById("funding-container");
      fundEl.innerHTML = `
        <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px;">
          ${sources.map(s => `
            <div style="background: var(--bg-elevated); padding: 16px; border-radius: 6px; border: 1px solid var(--border-subtle);">
              <div style="font-size: 13px; font-weight: 600; margin-bottom: 6px;">${s.source}</div>
              <div style="font-size: 20px; font-weight: 700; color: var(--color-primary);">$${s.amount.toLocaleString(undefined, {minimumFractionDigits: 2})}</div>
              <div style="font-size: 12px; color: var(--text-muted); margin-top: 4px;">${s.pct}% of total facility</div>
            </div>
          `).join("")}
        </div>
      `;

    } catch (e) {
      console.error("Failed to load treasury metrics:", e);
    }
  },
};
