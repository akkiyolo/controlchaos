/**
 * ControlChaos Main Application Controller
 */

import { ApiClient } from './api.js';
import { Router } from './router.js';
import { renderDashboardPage } from './pages/dashboard.js';
import { renderDatasetsPage } from './pages/datasets.js';
import { renderControls } from './pages/controls.js';
import { renderMutationsPage } from './pages/mutations.js';
import { renderRunsPage } from './pages/runs.js';
import { AgentsPage } from './pages/agents.js';
import { VariancePage } from './pages/variance.js';
import { TreasuryPage } from './pages/treasury.js';
import { ReconPage } from './pages/recon.js';
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
      '#datasets': async () => {
        this.ensureShellVisible();
        pageTitle.textContent = 'Synthetic Ledgers & Datasets';
        await renderDatasetsPage(mainContent);
      },
      '#mutations': async () => {
        this.ensureShellVisible();
        pageTitle.textContent = 'Mutation Lab & Campaigns';
        await renderMutationsPage(mainContent);
      },
      '#controls': async () => {
        this.ensureShellVisible();
        pageTitle.textContent = 'Financial Controls Suite';
        await renderControls(mainContent);
      },
      '#runs': async () => {
        this.ensureShellVisible();
        pageTitle.textContent = 'Runs & Scorecards';
        await renderRunsPage(mainContent);
      },
      '#variance': async () => {
        this.ensureShellVisible();
        pageTitle.textContent = 'Variance Studio & AI Commentary';
        mainContent.innerHTML = await VariancePage.render();
        await VariancePage.mount();
      },
      '#treasury': async () => {
        this.ensureShellVisible();
        pageTitle.textContent = 'Treasury & Liquidity Workbench';
        mainContent.innerHTML = await TreasuryPage.render();
        await TreasuryPage.mount();
      },
      '#recon': async () => {
        this.ensureShellVisible();
        pageTitle.textContent = 'Reconciliation Workbench';
        mainContent.innerHTML = await ReconPage.render();
        await ReconPage.mount();
      },
      '#agents': async () => {
        this.ensureShellVisible();
        pageTitle.textContent = 'Governed Multi-Agent Workbench';
        mainContent.innerHTML = await AgentsPage.render();
        await AgentsPage.mount();
      },
      '#audit': async () => {
        this.ensureShellVisible();
        pageTitle.textContent = 'Cryptographic Audit Log';
        await renderAuditPage(mainContent);
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
