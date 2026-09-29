/**
 * Audit Log & Cryptographic Verification Page Component
 */

import { ApiClient } from '../api.js';

export async function renderAuditPage(container) {
  container.innerHTML = `
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
      <div>
        <h2 style="font-size: 18px; font-weight: 600; color: var(--text-primary);">Tamper-Evident Audit Log</h2>
        <p style="font-size: 12px; color: var(--text-muted);">Append-only SHA-256 cryptographic hash chain verifying governance and traceability.</p>
      </div>
      <div style="display: flex; gap: 12px; align-items: center;">
        <span id="audit-chain-badge" class="badge badge-info">Unverified</span>
        <button id="verify-chain-btn" class="btn btn-primary btn-sm">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
          Verify Chain Cryptography
        </button>
      </div>
    </div>

    <div class="card">
      <div class="table-responsive">
        <table class="table">
          <thead>
            <tr>
              <th style="width: 60px;">ID</th>
              <th style="width: 160px;">Timestamp (UTC)</th>
              <th style="width: 140px;">Actor</th>
              <th style="width: 160px;">Action</th>
              <th style="width: 140px;">Entity</th>
              <th>SHA-256 Hash</th>
              <th style="width: 80px;">Details</th>
            </tr>
          </thead>
          <tbody id="audit-table-body">
            <tr>
              <td colspan="7" style="text-align: center; color: var(--text-muted); padding: 30px;">Loading audit ledger...</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Modal for payload viewing -->
    <div id="payload-modal" style="display:none; position:fixed; top:0; left:0; width:100%; height:100%; background:rgba(0,0,0,0.7); z-index:9999; align-items:center; justify-content:center;">
      <div class="card" style="width:500px; max-width:90%; max-height:80vh; overflow-y:auto;">
        <div class="card-header">
          <div class="card-title">Audit Record Payload</div>
          <button id="close-modal-btn" class="btn btn-secondary btn-sm">Close</button>
        </div>
        <pre id="modal-json" style="background:var(--bg-primary); padding:12px; border-radius:var(--radius-sm); font-size:12px; font-family:var(--font-mono); overflow-x:auto;"></pre>
      </div>
    </div>
  `;

  const tbody = document.getElementById('audit-table-body');
  const verifyBtn = document.getElementById('verify-chain-btn');
  const chainBadge = document.getElementById('audit-chain-badge');
  const modal = document.getElementById('payload-modal');
  const modalJson = document.getElementById('modal-json');
  const closeModalBtn = document.getElementById('close-modal-btn');

  closeModalBtn.addEventListener('click', () => { modal.style.display = 'none'; });

  async function loadAuditLogs() {
    try {
      const data = await ApiClient.listAuditLogs(1, 50);
      if (!data.entries || data.entries.length === 0) {
        tbody.innerHTML = `<tr><td colspan="7" style="text-align:center; color:var(--text-muted); padding:30px;">No audit entries recorded yet.</td></tr>`;
        return;
      }

      tbody.innerHTML = data.entries.map((entry) => `
        <tr>
          <td class="num">${entry.id}</td>
          <td class="num" style="font-size:12px;">${entry.ts.replace('T', ' ').slice(0, 19)}</td>
          <td><span class="badge badge-info" style="text-transform:none;">${entry.actor}</span></td>
          <td><strong>${entry.action}</strong></td>
          <td>${entry.entity_type} <span style="color:var(--text-muted); font-size:11px;">#${entry.entity_id}</span></td>
          <td style="font-family:var(--font-mono); font-size:11px; color:var(--text-muted);" title="Prev: ${entry.prev_hash}">
            ${entry.hash.slice(0, 16)}...${entry.hash.slice(-8)}
          </td>
          <td>
            <button class="btn btn-secondary btn-sm view-payload-btn" data-payload='${JSON.stringify(entry.payload)}'>View</button>
          </td>
        </tr>
      `).join('');

      container.querySelectorAll('.view-payload-btn').forEach((btn) => {
        btn.addEventListener('click', () => {
          modalJson.textContent = JSON.stringify(JSON.parse(btn.dataset.payload), null, 2);
          modal.style.display = 'flex';
        });
      });

    } catch (err) {
      tbody.innerHTML = `<tr><td colspan="7" style="color:var(--status-danger-text); padding:20px; text-align:center;">Failed to load audit logs: ${err.message}</td></tr>`;
    }
  }

  async function verifyChain() {
    verifyBtn.disabled = true;
    chainBadge.textContent = 'Verifying SHA-256 Chain...';
    chainBadge.className = 'badge badge-warning';

    try {
      const result = await ApiClient.verifyAuditChain();
      if (result.is_intact) {
        chainBadge.className = 'badge badge-success';
        chainBadge.innerHTML = `<span class="badge-dot"></span> Chain Intact (${result.total_entries_verified} Blocks)`;
      } else {
        chainBadge.className = 'badge badge-danger';
        chainBadge.innerHTML = `<span class="badge-dot"></span> Tampered at Block #${result.broken_link?.entry_id}`;
      }
    } catch (err) {
      chainBadge.className = 'badge badge-danger';
      chainBadge.textContent = 'Verification Error';
    } finally {
      verifyBtn.disabled = false;
    }
  }

  verifyBtn.addEventListener('click', verifyChain);

  // Initial load
  await loadAuditLogs();
  await verifyChain();
}
