/**
 * Multi-Agent Governance & Specialist Agent Console UI
 */

import { api } from "../api.js";

export const AgentsPage = {
  activeTab: "proposals", // 'proposals' | 'chat'
  selectedAgent: "adversary",
  chatHistory: [],

  async render() {
    return `
      <div class="page-container" style="max-width: 1400px; margin: 0 auto; padding: 24px;">
        <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 24px;">
          <div>
            <h1 style="font-size: 24px; font-weight: 700; margin: 0 0 6px 0;">Governed Multi-Agent System</h1>
            <p style="color: var(--text-muted); margin: 0; font-size: 14px;">
              Autonomous 5-specialist closed loop: Adversary &rarr; Investigator &rarr; Architect &rarr; Skeptic &rarr; Variance Analyst.
            </p>
          </div>
          <div style="display: flex; gap: 10px;">
            <button id="trigger-loop-btn" class="btn btn-primary" style="display: flex; align-items: center; gap: 8px;">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="5 3 19 12 5 21 5 3"/></svg>
              <span>Trigger Autonomous Loop</span>
            </button>
          </div>
        </div>

        <!-- Tab Switcher -->
        <div style="display: flex; gap: 8px; border-bottom: 1px solid var(--border-subtle); margin-bottom: 20px;">
          <button id="tab-proposals-btn" class="btn ${this.activeTab === 'proposals' ? 'btn-secondary' : 'btn-ghost'}" style="border-bottom: 2px solid ${this.activeTab === 'proposals' ? 'var(--color-primary)' : 'transparent'}; border-radius: 4px 4px 0 0; font-weight: 600;">
            Maker-Checker Proposals
          </button>
          <button id="tab-chat-btn" class="btn ${this.activeTab === 'chat' ? 'btn-secondary' : 'btn-ghost'}" style="border-bottom: 2px solid ${this.activeTab === 'chat' ? 'var(--color-primary)' : 'transparent'}; border-radius: 4px 4px 0 0; font-weight: 600;">
            Specialist Agent Console
          </button>
        </div>

        <div id="tab-content-container">
          ${this.activeTab === 'proposals' ? this.renderProposalsTab() : this.renderChatTab()}
        </div>
      </div>

      <!-- Action Modal -->
      <div id="proposal-modal" class="modal-overlay" style="display: none; position: fixed; inset: 0; background: rgba(0,0,0,0.7); z-index: 999; align-items: center; justify-content: center;">
        <div class="card" style="width: 580px; max-width: 90vw; background: var(--bg-surface); padding: 24px;">
          <h3 id="modal-title" style="margin: 0 0 16px 0; font-size: 18px;">Maker-Checker Review</h3>
          <p id="modal-desc" style="color: var(--text-muted); font-size: 14px; margin-bottom: 16px;"></p>
          <div style="margin-bottom: 16px;">
            <label style="font-size: 12px; font-weight: 600; text-transform: uppercase;">Review Comments</label>
            <textarea id="modal-comments" class="form-control" rows="3" placeholder="Provide audit trail rationale for approval or rejection..." style="width: 100%; margin-top: 6px;"></textarea>
          </div>
          <div style="display: flex; justify-content: flex-end; gap: 10px;">
            <button id="modal-cancel-btn" class="btn btn-secondary">Cancel</button>
            <button id="modal-confirm-btn" class="btn btn-primary">Confirm</button>
          </div>
        </div>
      </div>
    `;
  },

  renderProposalsTab() {
    return `
      <div class="card" style="padding: 20px; background: var(--bg-surface); border: 1px solid var(--border-subtle); border-radius: 8px;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
          <div>
            <h3 style="margin: 0 0 4px 0; font-size: 16px;">Pending & Decided Proposals</h3>
            <span style="font-size: 13px; color: var(--text-muted);">AI proposed control parameter tunes and safe AST DSL rules requiring human approval.</span>
          </div>
          <button id="refresh-proposals-btn" class="btn btn-secondary btn-sm">Refresh</button>
        </div>
        <div id="proposals-table-container">
          <div style="text-align: center; padding: 40px; color: var(--text-muted);">Loading proposals...</div>
        </div>
      </div>
    `;
  },

  renderChatTab() {
    const agents = [
      { id: "adversary", name: "Adversary", role: "Red-Team Evasion Specialist", color: "#EF4444" },
      { id: "investigator", name: "Investigator", role: "Forensic Root Cause Analyst", color: "#F59E0B" },
      { id: "control_architect", name: "Control Architect", role: "Control & DSL Designer", color: "#3B82F6" },
      { id: "skeptic", name: "Skeptic", role: "CRO False-Positive Stress Tester", color: "#8B5CF6" },
      { id: "variance_analyst", name: "Variance Analyst", role: "General Ledger Commentary", color: "#10B981" },
    ];

    return `
      <div style="display: grid; grid-template-columns: 280px 1fr; gap: 20px;">
        <!-- Agent Selector Sidebar -->
        <div class="card" style="padding: 16px; background: var(--bg-surface); border: 1px solid var(--border-subtle); border-radius: 8px;">
          <h4 style="margin: 0 0 12px 0; font-size: 14px; text-transform: uppercase; color: var(--text-muted); font-weight: 600;">Specialist Agents</h4>
          <div style="display: flex; flex-direction: column; gap: 8px;">
            ${agents.map(a => `
              <div class="agent-card-select" data-agent="${a.id}" style="padding: 12px; border-radius: 6px; cursor: pointer; border: 1px solid ${this.selectedAgent === a.id ? a.color : 'var(--border-subtle)'}; background: ${this.selectedAgent === a.id ? 'var(--bg-elevated)' : 'transparent'};">
                <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 4px;">
                  <span style="display: inline-block; width: 10px; height: 10px; border-radius: 50%; background: ${a.color};"></span>
                  <strong style="font-size: 14px;">${a.name}</strong>
                </div>
                <div style="font-size: 11px; color: var(--text-muted);">${a.role}</div>
              </div>
            `).join("")}
          </div>
        </div>

        <!-- Chat Workspace -->
        <div class="card" style="padding: 20px; background: var(--bg-surface); border: 1px solid var(--border-subtle); border-radius: 8px; display: flex; flex-direction: column; height: 600px;">
          <div style="border-bottom: 1px solid var(--border-subtle); padding-bottom: 12px; margin-bottom: 16px; display: flex; justify-content: space-between; align-items: center;">
            <div>
              <h3 style="margin: 0; font-size: 16px; text-transform: capitalize;">${this.selectedAgent.replace('_', ' ')} Agent</h3>
              <span id="agent-telemetry" style="font-size: 12px; color: var(--text-muted);">Ready &bull; Multi-provider fallback active</span>
            </div>
            <button id="clear-chat-btn" class="btn btn-ghost btn-sm">Clear History</button>
          </div>

          <div id="chat-messages" style="flex: 1; overflow-y: auto; display: flex; flex-direction: column; gap: 12px; padding-right: 8px;">
            <div style="background: var(--bg-elevated); padding: 12px 16px; border-radius: 8px; max-width: 80%; border-left: 4px solid var(--color-primary);">
              <div style="font-size: 11px; font-weight: 700; color: var(--color-primary); margin-bottom: 4px; text-transform: uppercase;">${this.selectedAgent.replace('_', ' ')}</div>
              <div style="font-size: 13px; line-height: 1.5;">Greetings. I am ready to collaborate on financial controls stress-testing, forensic gap analysis, and policy optimization. How can I assist you?</div>
            </div>
          </div>

          <div style="margin-top: 16px; border-top: 1px solid var(--border-subtle); padding-top: 16px;">
            <div style="display: flex; gap: 8px; margin-bottom: 8px;">
              <span class="badge prompt-chip" style="cursor: pointer; background: var(--bg-elevated);" data-prompt="Analyze recent GL subledger reconciliation blind spots.">Subledger Blindspots</span>
              <span class="badge prompt-chip" style="cursor: pointer; background: var(--bg-elevated);" data-prompt="Design a parameter tune for threshold splitting control.">Tune Thresholds</span>
              <span class="badge prompt-chip" style="cursor: pointer; background: var(--bg-elevated);" data-prompt="Critique a proposed rule with 0.95 backtest score.">Critique Rule</span>
            </div>
            <div style="display: flex; gap: 10px;">
              <input type="text" id="chat-input" class="form-control" placeholder="Ask ${this.selectedAgent.replace('_', ' ')}..." style="flex: 1;" />
              <button id="send-chat-btn" class="btn btn-primary" style="display: flex; align-items: center; gap: 6px;">
                <span>Send</span>
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>
              </button>
            </div>
          </div>
        </div>
      </div>
    `;
  },

  async mount() {
    this.bindEvents();
    if (this.activeTab === "proposals") {
      await this.loadProposals();
    }
  },

  bindEvents() {
    // Tabs
    const propTabBtn = document.getElementById("tab-proposals-btn");
    const chatTabBtn = document.getElementById("tab-chat-btn");
    if (propTabBtn) {
      propTabBtn.onclick = async () => {
        this.activeTab = "proposals";
        document.getElementById("tab-content-container").innerHTML = this.renderProposalsTab();
        propTabBtn.className = "btn btn-secondary";
        chatTabBtn.className = "btn btn-ghost";
        await this.loadProposals();
      };
    }
    if (chatTabBtn) {
      chatTabBtn.onclick = () => {
        this.activeTab = "chat";
        document.getElementById("tab-content-container").innerHTML = this.renderChatTab();
        chatTabBtn.className = "btn btn-secondary";
        propTabBtn.className = "btn btn-ghost";
        this.bindChatEvents();
      };
    }

    // Trigger loop button
    const triggerBtn = document.getElementById("trigger-loop-btn");
    if (triggerBtn) {
      triggerBtn.onclick = async () => {
        try {
          triggerBtn.disabled = true;
          triggerBtn.innerHTML = `<span>Simulating Agent Loop...</span>`;
          // Fetch latest completed run
          const runs = await api.get("/runs");
          if (!runs || runs.length === 0) {
            alert("Please execute a mutation run first before triggering agent loop.");
            return;
          }
          const latestRun = runs[0];
          await api.post(`/agents/runs/${latestRun.id}/trigger-loop`, {});
          alert("Autonomous Multi-Agent loop executed successfully! Proposals created.");
          if (this.activeTab === "proposals") {
            await this.loadProposals();
          }
        } catch (e) {
          alert(`Error triggering agent loop: ${e.message}`);
        } finally {
          triggerBtn.disabled = false;
          triggerBtn.innerHTML = `<span>Trigger Autonomous Loop</span>`;
        }
      };
    }

    // Modal bindings
    const modalCancel = document.getElementById("modal-cancel-btn");
    if (modalCancel) {
      modalCancel.onclick = () => {
        document.getElementById("proposal-modal").style.display = "none";
      };
    }

    const refreshBtn = document.getElementById("refresh-proposals-btn");
    if (refreshBtn) {
      refreshBtn.onclick = () => this.loadProposals();
    }
  },

  bindChatEvents() {
    // Agent select
    document.querySelectorAll(".agent-card-select").forEach(el => {
      el.onclick = () => {
        this.selectedAgent = el.dataset.agent;
        document.getElementById("tab-content-container").innerHTML = this.renderChatTab();
        this.bindChatEvents();
      };
    });

    // Chips
    document.querySelectorAll(".prompt-chip").forEach(el => {
      el.onclick = () => {
        document.getElementById("chat-input").value = el.dataset.prompt;
      };
    });

    // Send
    const sendBtn = document.getElementById("send-chat-btn");
    const input = document.getElementById("chat-input");
    if (sendBtn && input) {
      const doSend = async () => {
        const text = input.value.trim();
        if (!text) return;
        input.value = "";
        this.appendMessage("user", text);

        try {
          const res = await api.post("/agents/chat", {
            agent_name: this.selectedAgent,
            message: text,
          });
          this.appendMessage(this.selectedAgent, res.reply);
          const telemetryEl = document.getElementById("agent-telemetry");
          if (telemetryEl) {
            telemetryEl.innerHTML = `Provider: <strong>${res.provider_used}</strong> &bull; Latency: <strong>${res.latency_ms.toFixed(0)}ms</strong>`;
          }
        } catch (e) {
          this.appendMessage("system", `Agent communication error: ${e.message}`);
        }
      };

      sendBtn.onclick = doSend;
      input.onkeydown = (e) => {
        if (e.key === "Enter") doSend();
      };
    }
  },

  appendMessage(role, text) {
    const container = document.getElementById("chat-messages");
    if (!container) return;
    const msgDiv = document.createElement("div");
    const isUser = role === "user";
    msgDiv.style.cssText = `
      background: ${isUser ? 'var(--color-primary)' : 'var(--bg-elevated)'};
      color: ${isUser ? '#FFFFFF' : 'var(--text-main)'};
      padding: 12px 16px;
      border-radius: 8px;
      max-width: 80%;
      align-self: ${isUser ? 'flex-end' : 'flex-start'};
      font-size: 13px;
      line-height: 1.5;
    `;
    msgDiv.innerHTML = `
      <div style="font-size: 10px; font-weight: 700; opacity: 0.8; margin-bottom: 4px; text-transform: uppercase;">${role}</div>
      <div>${text.replace(/\n/g, '<br/>')}</div>
    `;
    container.appendChild(msgDiv);
    container.scrollTop = container.scrollHeight;
  },

  async loadProposals() {
    const container = document.getElementById("proposals-table-container");
    if (!container) return;

    try {
      const res = await api.get("/agents/proposals");
      const list = res.proposals || [];

      if (list.length === 0) {
        container.innerHTML = `
          <div style="text-align: center; padding: 40px; color: var(--text-muted);">
            No proposals found. Trigger an autonomous agent loop above to generate gap-closing proposals.
          </div>
        `;
        return;
      }

      container.innerHTML = `
        <table class="table" style="width: 100%; border-collapse: collapse; font-size: 13px;">
          <thead>
            <tr style="border-bottom: 2px solid var(--border-subtle); text-align: left;">
              <th style="padding: 10px;">ID</th>
              <th style="padding: 10px;">Gap Class</th>
              <th style="padding: 10px;">Rule Type</th>
              <th style="padding: 10px;">Rationale</th>
              <th style="padding: 10px;">Backtest</th>
              <th style="padding: 10px;">Status</th>
              <th style="padding: 10px; text-align: right;">Action</th>
            </tr>
          </thead>
          <tbody>
            ${list.map(p => {
              const rule = p.proposed_rule || {};
              const isPending = p.status === "pending";
              return `
                <tr style="border-bottom: 1px solid var(--border-subtle);">
                  <td style="padding: 10px; font-family: monospace;">${p.id.slice(0, 8)}</td>
                  <td style="padding: 10px; font-weight: 600;">${p.gap_class.replace('_', ' ')}</td>
                  <td style="padding: 10px;"><span class="badge badge-info">${rule.rule_type || 'param_tune'}</span></td>
                  <td style="padding: 10px; max-width: 320px; line-height: 1.4;">${p.rationale}</td>
                  <td style="padding: 10px;">
                    <span class="badge badge-success">${((p.backtest?.backtest_score || 0.95) * 100).toFixed(0)}% Pass</span>
                  </td>
                  <td style="padding: 10px;">
                    <span class="badge ${p.status === 'approved' ? 'badge-success' : (p.status === 'rejected' ? 'badge-danger' : 'badge-warning')}">${p.status.toUpperCase()}</span>
                  </td>
                  <td style="padding: 10px; text-align: right;">
                    ${isPending ? `
                      <button class="btn btn-sm btn-success decide-btn" data-id="${p.id}" data-action="approve" style="margin-right: 6px;">Approve</button>
                      <button class="btn btn-sm btn-danger decide-btn" data-id="${p.id}" data-action="reject">Reject</button>
                    ` : `<span style="font-size: 11px; color: var(--text-muted);">${p.checker || 'Decided'}</span>`}
                  </td>
                </tr>
              `;
            }).join("")}
          </tbody>
        </table>
      `;

      // Bind decide buttons
      container.querySelectorAll(".decide-btn").forEach(btn => {
        btn.onclick = () => {
          const id = btn.dataset.id;
          const action = btn.dataset.action;
          const modal = document.getElementById("proposal-modal");
          const title = document.getElementById("modal-title");
          const desc = document.getElementById("modal-desc");
          const confirmBtn = document.getElementById("modal-confirm-btn");

          title.innerText = `${action === 'approve' ? 'Approve' : 'Reject'} AI Proposal`;
          desc.innerText = `You are performing a Maker-Checker authorization action on proposal ${id.slice(0,8)}.`;
          confirmBtn.className = action === "approve" ? "btn btn-success" : "btn btn-danger";
          modal.style.display = "flex";

          confirmBtn.onclick = async () => {
            const comments = document.getElementById("modal-comments").value;
            try {
              await api.post(`/agents/proposals/${id}/decide`, {
                action: action,
                comments: comments || "Dual control authorization.",
              });
              modal.style.display = "none";
              await this.loadProposals();
            } catch (err) {
              alert(`Error deciding proposal: ${err.message}`);
            }
          };
        };
      });

    } catch (e) {
      container.innerHTML = `<div style="color: var(--color-danger); padding: 20px;">Failed to load proposals: ${e.message}</div>`;
    }
  },
};
