/**
 * InfectoCast Component Library - BaseChart
 * Classe base para renderização de gráficos Canvas de alta performance com Retina support e tooltips.
 */

export class BaseChart {
  /**
   * @param {Object} options
   * @param {string} [options.id] - ID do container
   * @param {string} options.title - Título do gráfico
   * @param {string} [options.subtitle] - Subtítulo
   * @param {number} [options.height=280] - Altura em pixels
   */
  constructor(options = {}) {
    this.id = options.id || `chart-${Math.random().toString(36).substr(2, 9)}`;
    this.title = options.title || 'Gráfico';
    this.subtitle = options.subtitle || '';
    this.height = options.height || 280;
    this.element = null;
    this.canvas = null;
    this.ctx = null;
    this.tooltipEl = null;
    this.resizeObserver = null;
  }

  /** Cria a casca HTML do componente */
  createCardWrapper(contentHtml = '') {
    const card = document.createElement('div');
    card.id = this.id;
    card.className = 'chart-card';

    card.innerHTML = `
      <div class="chart-header">
        <div class="chart-title-wrap">
          <h3 class="chart-title">${this.title}</h3>
          ${this.subtitle ? `<span class="chart-subtitle">${this.subtitle}</span>` : ''}
        </div>
        <div class="chart-controls"></div>
      </div>
      <div class="chart-canvas-container" style="height: ${this.height}px;">
        <canvas class="chart-canvas"></canvas>
        <div class="chart-tooltip"></div>
      </div>
      ${contentHtml}
    `;

    this.element = card;
    this.canvas = card.querySelector('.chart-canvas');
    this.ctx = this.canvas.getContext('2d');
    this.tooltipEl = card.querySelector('.chart-tooltip');

    this.setupResizeObserver();
    return card;
  }

  /** Ajusta resolução do Canvas para telas HiDPI / Retina */
  setupCanvasDimensions() {
    if (!this.canvas) return { width: 0, height: 0 };
    const rect = this.canvas.getBoundingClientRect();
    const dpr = window.devicePixelRatio || 1;
    
    this.canvas.width = rect.width * dpr;
    this.canvas.height = rect.height * dpr;
    this.ctx.resetTransform ? this.ctx.resetTransform() : this.ctx.setTransform(1, 0, 0, 1, 0, 0);
    this.ctx.scale(dpr, dpr);

    return { width: rect.width, height: rect.height };
  }

  /** Monitora alterações de tamanho da tela */
  setupResizeObserver() {
    if (!window.ResizeObserver) return;
    this.resizeObserver = new ResizeObserver(() => {
      if (this.element && this.draw) {
        requestAnimationFrame(() => this.draw());
      }
    });
    this.resizeObserver.observe(this.element);
  }

  /** Exibe tooltip formatado */
  showTooltip(x, y, title, rows = []) {
    if (!this.tooltipEl) return;
    let rowsHtml = rows.map(r => `
      <div class="chart-tooltip-row">
        <span>${r.label}:</span>
        <strong class="chart-tooltip-val" style="color: ${r.color || '#38bdf8'}">${r.value}</strong>
      </div>
    `).join('');

    this.tooltipEl.innerHTML = `
      <div class="chart-tooltip-title">${title}</div>
      ${rowsHtml}
    `;
    this.tooltipEl.style.left = `${x}px`;
    this.tooltipEl.style.top = `${y}px`;
    this.tooltipEl.style.opacity = '1';
  }

  /** Oculta tooltip */
  hideTooltip() {
    if (this.tooltipEl) this.tooltipEl.style.opacity = '0';
  }

  /** Monta no DOM */
  mount(target) {
    const container = typeof target === 'string' ? document.querySelector(target) : target;
    if (container) {
      container.appendChild(this.render());
      setTimeout(() => this.draw && this.draw(), 50);
    }
    return this;
  }

  destroy() {
    if (this.resizeObserver) this.resizeObserver.disconnect();
    if (this.element && this.element.parentNode) {
      this.element.parentNode.removeChild(this.element);
    }
  }
}
