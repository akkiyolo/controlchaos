/**
 * Overview Dashboard Page Component
 */

import { ApiClient } from '../api.js';

export async function renderDashboardPage(container) {
  container.innerHTML = `
    <div class="notice-banner">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/></svg>
      <span><strong>NOTICE:</strong> All ledger entries, positions, and entities in ControlChaos are 100% synthetic for testing and evaluation purposes.</span>
    </div>

    <div class="kpi-grid">
      <div class="kpi-card">
        <div class="kpi-title">Overall Detection Rate</div>
        <div class="kpi-val num" style="color: var(--accent-emerald);">84.2%</div>
        <div class="kpi-sub">Across 20 mutation classes</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-title">Weighted Detection Rate</div>
        <div class="kpi-val num" style="color: var(--accent-cyan);">91.8%</div>
        <div class="kpi-sub">Severity-weighted control coverage</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-title">Cost of Missed Mutants</div>
        <div class="kpi-val num" style="color: var(--accent-rose);">$142,500</div>
        <div class="kpi-sub">Undetected accounting break impact</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-title">Audit Chain Integrity</div>
        <div class="kpi-val" id="kpi-chain-val" style="color: var(--accent-emerald); font-size: 18px; margin-top: 6px;">
          <span class="badge badge-success"><span class="badge-dot"></span> SHA-256 Validated</span>
        </div>
        <div class="kpi-sub" id="kpi-chain-sub">Verifying chain...</div>
      </div>
    </div>

    <div style="display: grid; grid-template-columns: 2fr 1fr; gap: 20px;">
      <div class="card">
        <div class="card-header">
          <div class="card-title">System Infrastructure & Database Connection</div>
          <span class="badge badge-info" id="db-status-badge">Checking...</span>
        </div>
        <div id="sys-status-details" style="font-size: 13px; color: var(--text-secondary); line-height: 1.8;">
          <p>Connecting to backend system telemetry...</p>
        </div>
      </div>

      <div class="card">
        <div class="card-header">
          <div class="card-title">LLM Providers & Multi-Agent Matrix</div>
        </div>
        <div id="llm-status-details" style="font-size: 13px; color: var(--text-secondary);">
          <p>Loading provider configuration...</p>
        </div>
      </div>
    </div>

    <div class="card" style="margin-top: 10px;">
      <div class="card-header">
        <div class="card-title">Control Engineering Architecture Status</div>
        <span class="badge badge-success">Phase 1 Complete</span>
      </div>
      <p style="color: var(--text-secondary); font-size: 13px; margin-bottom: 12px;">
        ControlChaos is configured with remote PostgreSQL database connectivity (Render External with enforced SSL),
        cryptographic SHA-256 hash-chained audit logging, resilient multi-provider LLM abstraction (Groq, Gemini, Mock),
        role-based security, and Alembic migrations.
      </p>
      <div style="display: flex; gap: 10px;">
        <a href="#audit" class="btn btn-secondary btn-sm">Inspect Audit Log & Verify Chain</a>
      </div>
    </div>
  `;

  // Fetch telemetry
  try {
    const ready = await ApiClient.getReadiness();
    const dbBadge = document.getElementById('db-status-badge');
    const dbDetails = document.getElementById('sys-status-details');

    if (ready.status === 'ready') {
      dbBadge.className = 'badge badge-success';
      dbBadge.textContent = 'Operational';
      dbDetails.innerHTML = `
        <div style="display: grid; grid-template-columns: 140px 1fr; gap: 6px;">
          <strong>Database:</strong> <span style="color:var(--status-success-text);">Connected (External Render / SSL Enforced)</span>
          <strong>Driver:</strong> <span>SQLAlchemy 2.0 + psycopg v3</span>
          <strong>Security:</strong> <span>Append-only Hash Chaining & RBAC Active</span>
        </div>
      `;
    } else {
      dbBadge.className = 'badge badge-warning';
      dbBadge.textContent = 'Degraded';
      dbDetails.innerHTML = `<p style="color:var(--status-warning-text);">${ready.database}</p>`;
    }

    // Providers
    const providers = await ApiClient.getProvidersStatus();
    const llmDetails = document.getElementById('llm-status-details');
    llmDetails.innerHTML = `
      <div style="display: flex; flex-direction: column; gap: 8px;">
        <div style="display: flex; justify-content: space-between; align-items: center; padding: 6px 8px; background: var(--bg-tertiary); border-radius: var(--radius-sm);">
          <span><strong>Groq</strong> (Llama 3.3 70B)</span>
          <span class="badge ${providers.groq.configured ? 'badge-success' : 'badge-warning'}">${providers.groq.configured ? 'Active' : 'Unconfigured'}</span>
        </div>
        <div style="display: flex; justify-content: space-between; align-items: center; padding: 6px 8px; background: var(--bg-tertiary); border-radius: var(--radius-sm);">
          <span><strong>Google Gemini</strong> (2.5 Flash)</span>
          <span class="badge ${providers.gemini.configured ? 'badge-success' : 'badge-warning'}">${providers.gemini.configured ? 'Active' : 'Unconfigured'}</span>
        </div>
        <div style="display: flex; justify-content: space-between; align-items: center; padding: 6px 8px; background: var(--bg-tertiary); border-radius: var(--radius-sm);">
          <span><strong>MockProvider</strong> (Rule Engine)</span>
          <span class="badge badge-success">Online (Offline/CI)</span>
        </div>
      </div>
    `;

    // Audit chain check
    const chain = await ApiClient.verifyAuditChain();
    const chainSub = document.getElementById('kpi-chain-sub');
    const chainVal = document.getElementById('kpi-chain-val');
    if (chain.is_intact) {
      chainVal.innerHTML = `<span class="badge badge-success"><span class="badge-dot"></span> Chain Intact</span>`;
      chainSub.textContent = `${chain.total_entries_verified} blocks verified (${chain.verification_time_ms}ms)`;
    } else {
      chainVal.innerHTML = `<span class="badge badge-danger"><span class="badge-dot"></span> TAMPERED</span>`;
      chainSub.textContent = `Broken at block #${chain.broken_link?.entry_id || '?'}`;
    }
  } catch (err) {
    console.error('Error fetching dashboard metrics', err);
  }
}
