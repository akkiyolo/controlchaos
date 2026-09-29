/**
 * Lightweight Client-Side Hash Router
 */

import { ApiClient } from './api.js';

export class Router {
  constructor(routes, defaultRoute = '#dashboard') {
    this.routes = routes;
    this.defaultRoute = defaultRoute;
    this.currentRoute = null;

    window.addEventListener('hashchange', () => this.handleRoute());
  }

  init() {
    this.handleRoute();
  }

  navigate(path) {
    window.location.hash = path;
  }

  async handleRoute() {
    let hash = window.location.hash || this.defaultRoute;
    const cleanHash = hash.split('?')[0];

    const token = ApiClient.getToken();
    if (!token && cleanHash !== '#login') {
      window.location.hash = '#login';
      return;
    }

    if (token && cleanHash === '#login') {
      window.location.hash = '#dashboard';
      return;
    }

    const routeHandler = this.routes[cleanHash] || this.routes[this.defaultRoute];
    if (routeHandler) {
      this.currentRoute = cleanHash;
      await routeHandler();
      this.updateActiveNav(cleanHash);
    }
  }

  updateActiveNav(hash) {
    document.querySelectorAll('.nav-link').forEach((link) => {
      if (link.getAttribute('href') === hash) {
        link.classList.add('active');
      } else {
        link.classList.remove('active');
      }
    });
  }
}
