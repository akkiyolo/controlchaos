/**
 * ControlChaos Main Application Controller
 */

import { ApiClient } from './api.js';
import { Router } from './router.js';
import { renderDashboardPage } from './pages/dashboard.js';
import { renderAuditPage } from './pages/audit.js';
import { renderLoginPage } from './pages/login.js';

class App {
  constructor() {
    this.theme = localStorage.getItem('cc_theme') || 'dark';
    this.initTheme();
    this.initRouter();
  }

  initTheme() {
    document.documentElement.setAttribute('data-theme', this.theme);
  }

  toggleTheme() {
    this.theme = this.theme === 'dark' ? 'light' : 'dark';
    localStorage.setItem('cc_theme', this.theme);
    this.initTheme();
  }

  initRouter() {
    const mainContent = document.getElementById('main-content');
    const pageTitle = document.getElementById('current-page-title');
    const user = ApiClient.getCurrentUser();

    this.updateUserBadge(user);

    const routes = {
      '#login': async () => {
        document.getElementById('sidebar').style.display = 'none';
        document.getElementById('topbar').style.display = 'none';
        renderLoginPage(mainContent, () => {
          this.updateUserBadge(ApiClient.getCurrentUser());
          window.location.hash = '#dashboard';
        });
      },
      '#dashboard': async () => {
        this.ensureShellVisible();
        pageTitle.textContent = 'Executive Overview';
        await renderDashboardPage(mainContent);
      },
      '#audit': async () => {
        this.ensureShellVisible();
        pageTitle.textContent = 'Cryptographic Audit Log';
        await renderAuditPage(mainContent);
      },
      // Placeholders for future phases
      '#datasets': async () => {
        this.ensureShellVisible();
        pageTitle.textContent = 'Synthetic Ledgers & Datasets';
        mainContent.innerHTML = `<div class="card"><div class="card-header"><div class="card-title">Dataset Generator</div><span class="badge badge-info">Phase 2</span></div><p style="color:var(--text-secondary);">Balanced double-entry generator, sub-ledgers, budget, treasury, and decoy anomalies will activate in Phase 2.</p></div>`;
      },
      '#mutations': async () => {
        this.ensureShellVisible();
        pageTitle.textContent = 'Mutation Lab & Campaigns';
        mainContent.innerHTML = `<div class="card"><div class="card-header"><div class="card-title">Mutation Catalog</div><span class="badge badge-info">Phase 4</span></div><p style="color:var(--text-secondary);">20 financial error injection mutators with magnitude and stealth tuning will activate in Phase 4.</p></div>`;
      },
      '#controls': async () => {
        this.ensureShellVisible();
        pageTitle.textContent = 'Financial Controls Suite';
        mainContent.innerHTML = `<div class="card"><div class="card-header"><div class="card-title">Control Suite & Versioning</div><span class="badge badge-info">Phase 3</span></div><p style="color:var(--text-secondary);">Reconciliations, Benford analysis, threshold splitting, and segregation of duties controls activate in Phase 3.</p></div>`;
      },
      '#runs': async () => {
        this.ensureShellVisible();
        pageTitle.textContent = 'Runs & Scorecard';
        mainContent.innerHTML = `<div class="card"><div class="card-header"><div class="card-title">Execution Engine & Detection Scoring</div><span class="badge badge-info">Phase 5</span></div><p style="color:var(--text-secondary);">Orchestrated control runs with detection matching, false positive benchmarks, and blind spot heatmaps activate in Phase 5.</p></div>`;
      },
      '#agents': async () => {
        this.ensureShellVisible();
        pageTitle.textContent = 'Governed Multi-Agent Console';
        mainContent.innerHTML = `<div class="card"><div class="card-header"><div class="card-title">LangGraph Multi-Agent System</div><span class="badge badge-info">Phase 6</span></div><p style="color:var(--text-secondary);">Adversary, Investigator, Control Architect, Skeptic, and Variance Analyst agents activate in Phase 6.</p></div>`;
      },
    };

    this.router = new Router(routes, '#dashboard');
    this.router.init();

    // Attach theme toggle
    document.getElementById('theme-toggle-btn')?.addEventListener('click', () => {
      this.toggleTheme();
    });

    // Attach logout
    document.getElementById('logout-btn')?.addEventListener('click', (e) => {
      e.preventDefault();
      ApiClient.logout();
    });
  }

  ensureShellVisible() {
    document.getElementById('sidebar').style.display = 'flex';
    document.getElementById('topbar').style.display = 'flex';
  }

  updateUserBadge(user) {
    const userRoleEl = document.getElementById('user-role-badge');
    const userNameEl = document.getElementById('user-name-display');

    if (user && userRoleEl && userNameEl) {
      userRoleEl.textContent = user.role.toUpperCase();
      userRoleEl.className = 'badge badge-info';
      userNameEl.textContent = user.name;
    }
  }
}

// Global Toast utility
export function showToast(message, type = 'info') {
  const container = document.getElementById('toast-container');
  if (!container) return;

  const toast = document.createElement('div');
  toast.className = 'toast';
  toast.textContent = message;
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = '0';
    setTimeout(() => toast.remove(), 200);
  }, 4000);
}

document.addEventListener('DOMContentLoaded', () => {
  window.app = new App();
});
