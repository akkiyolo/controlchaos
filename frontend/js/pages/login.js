/**
 * Login Page Component
 */

import { ApiClient } from '../api.js';

export function renderLoginPage(container, onLoginSuccess) {
  container.innerHTML = `
    <div style="display:flex; align-items:center; justify-content:center; min-height:85vh; padding: 20px;">
      <div class="card" style="width: 100%; max-width: 440px; border-color: var(--border-strong);">
        <div style="text-align: center; margin-bottom: 24px;">
          <div class="brand-icon" style="width: 44px; height: 44px; font-size: 22px; margin: 0 auto 12px; border-radius: var(--radius-md);">CC</div>
          <h2 style="font-size: 20px; font-weight: 700; color: var(--text-primary); letter-spacing: -0.02em;">ControlChaos</h2>
          <p style="font-size: 13px; color: var(--text-muted); margin-top: 4px;">Mutation Testing for Financial Controls</p>
        </div>

        <form id="login-form">
          <div class="form-group">
            <label class="form-label" for="login-email">Email Address</label>
            <input type="email" id="login-email" class="form-control" required placeholder="admin@controlchaos.local" value="admin@controlchaos.local" />
          </div>

          <div class="form-group">
            <label class="form-label" for="login-password">Password</label>
            <input type="password" id="login-password" class="form-control" required placeholder="••••••••••••" value="ControlChaosAdmin2026!" />
          </div>

          <div id="login-error" style="display:none; color: var(--status-danger-text); font-size: 12px; margin-bottom: 12px; padding: 8px; background: var(--status-danger-bg); border-radius: var(--radius-sm);"></div>

          <button type="submit" class="btn btn-primary" style="width: 100%; padding: 10px; font-size: 14px; font-weight: 600;">
            Sign In to Terminal
          </button>
        </form>

        <div style="margin-top: 24px; padding-top: 16px; border-top: 1px solid var(--border-subtle);">
          <div style="font-size: 11px; font-weight: 600; text-transform: uppercase; color: var(--text-muted); margin-bottom: 10px; text-align: center;">
            Quick Role Switcher (Demo Mode)
          </div>
          <div style="display: flex; flex-wrap: wrap; gap: 6px;">
            <button class="btn btn-secondary btn-sm role-btn" data-email="admin@controlchaos.local" data-pass="ControlChaosAdmin2026!">Admin</button>
            <button class="btn btn-secondary btn-sm role-btn" data-email="owner@controlchaos.local" data-pass="ControlOwner2026!">Control Owner</button>
            <button class="btn btn-secondary btn-sm role-btn" data-email="reviewer@controlchaos.local" data-pass="Reviewer2026!">Reviewer (Checker)</button>
            <button class="btn btn-secondary btn-sm role-btn" data-email="analyst@controlchaos.local" data-pass="Analyst2026!">Analyst</button>
            <button class="btn btn-secondary btn-sm role-btn" data-email="auditor@controlchaos.local" data-pass="Auditor2026!">Auditor</button>
          </div>
        </div>
      </div>
    </div>
  `;

  // Attach quick-fill role buttons
  container.querySelectorAll('.role-btn').forEach((btn) => {
    btn.addEventListener('click', (e) => {
      e.preventDefault();
      document.getElementById('login-email').value = btn.dataset.email;
      document.getElementById('login-password').value = btn.dataset.pass;
    });
  });

  // Attach form submit
  const form = document.getElementById('login-form');
  const errBox = document.getElementById('login-error');

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    errBox.style.display = 'none';

    const email = document.getElementById('login-email').value.trim();
    const password = document.getElementById('login-password').value;

    try {
      await ApiClient.login(email, password);
      if (onLoginSuccess) onLoginSuccess();
    } catch (err) {
      errBox.textContent = err.message || 'Login failed';
      errBox.style.display = 'block';
    }
  });
}
