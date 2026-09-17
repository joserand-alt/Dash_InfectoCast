/**
 * InfectoCast Component Library - KpiCard
 * Componente modular para renderização de cards de métricas reativos e interativos.
 */

export class KpiCard {
  /**
   * @param {Object} options
   * @param {string} [options.id] - Identificador único do card
   * @param {string} options.title - Título/rótulo da métrica
   * @param {number|string} options.value - Valor da métrica
   * @param {string} [options.format='number'] - 'number' | 'currency' | 'percent' | 'days' | 'raw'
   * @param {string} [options.subtitle] - Descrição secundária ou complemento
   * @param {Object} [options.trend] - { value: '+12%', direction: 'up'|'down'|'neutral', label: 'vs mês anterior' }
   * @param {string} [options.color='blue'] - 'blue' | 'emerald' | 'amber' | 'rose' | 'purple' | 'cyan'
   * @param {string} [options.icon] - Nome do ícone SVG ('users', 'dollar', 'chart', 'clock', 'check', 'alert', 'star', 'tag')
   * @param {string} [options.tooltip] - Texto explicativo do cálculo
   * @param {number} [options.progress] - Porcentagem de preenchimento da barra (0 a 100)
   * @param {Function} [options.onClick] - Callback executado ao clicar no card: (kpiCard) => void
   * @param {boolean} [options.interactive=false] - Se o card possui efeito hover/click
   */
  constructor(options = {}) {
    this.id = options.id || `kpi-${Math.random().toString(36).substr(2, 9)}`;
    this.title = options.title || 'Métrica';
    this.value = options.value !== undefined ? options.value : 0;
    this.format = options.format || 'number';
    this.subtitle = options.subtitle || '';
    this.trend = options.trend || null;
    this.color = options.color || 'blue';
    this.icon = options.icon || 'chart';
    this.tooltip = options.tooltip || '';
    this.progress = typeof options.progress === 'number' ? Math.min(100, Math.max(0, options.progress)) : null;
    this.onClick = options.onClick || null;
    this.interactive = Boolean(options.onClick || options.interactive);
    this.isSelected = false;
    this.isLoading = false;
    
    this.element = null;
  }

  /** Formata o valor de acordo com o tipo */
  formatValue(val) {
    if (val === null || val === undefined || isNaN(val)) return '—';
    if (this.format === 'currency') {
      return Number(val).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
    }
    if (this.format === 'percent') {
      return `${Number(val).toLocaleString('pt-BR', { minimumFractionDigits: 1, maximumFractionDigits: 1 })}%`;
    }
    if (this.format === 'days') {
      const num = Math.round(Number(val));
      return `${num} ${num === 1 ? 'dia' : 'dias'}`;
    }
    if (this.format === 'number') {
      return Number(val).toLocaleString('pt-BR');
    }
    return String(val);
  }

  /** Retorna o SVG correspondente ao ícone configurado */
  getIconSvg(iconName) {
    const icons = {
      users: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path><circle cx="9" cy="7" r="4"></circle><path d="M23 21v-2a4 4 0 0 0-3-3.87"></path><path d="M16 3.13a4 4 0 0 1 0 7.75"></path></svg>',
      dollar: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="1" x2="12" y2="23"></line><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"></path></svg>',
      chart: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="20" x2="18" y2="10"></line><line x1="12" y1="20" x2="12" y2="4"></line><line x1="6" y1="20" x2="6" y2="14"></line></svg>',
      clock: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><polyline points="12 6 12 12 16 14"></polyline></svg>',
      check: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline></svg>',
      alert: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line></svg>',
      star: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"></polygon></svg>',
      tag: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20.59 13.41l-7.17 7.17a2 2 0 0 1-2.83 0L2 12V2h10l8.59 8.59a2 2 0 0 1 0 2.82z"></path><line x1="7" y1="7" x2="7.01" y2="7"></line></svg>',
      trendUp: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="23 6 13.5 15.5 8.5 10.5 1 18"></polyline><polyline points="17 6 23 6 23 12"></polyline></svg>',
      trendDown: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="23 18 13.5 8.5 8.5 13.5 1 6"></polyline><polyline points="17 18 23 18 23 12"></polyline></svg>',
      info: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="16" x2="12" y2="12"></line><line x1="12" y1="8" x2="12.01" y2="8"></line></svg>'
    };
    return icons[iconName] || icons.chart;
  }

  /** Renderiza o HTML do componente */
  render() {
    const card = document.createElement('div');
    card.id = this.id;
    card.className = `kpi-card kpi-card-${this.color} ${this.interactive ? 'interactive' : ''} ${this.isSelected ? 'selected' : ''} ${this.isLoading ? 'loading' : ''}`;
    
    // Cabeçalho
    let headerHtml = `
      <div class="kpi-card-header">
        <div class="kpi-card-title-wrap">
          <span class="kpi-card-title">${this.title}</span>
          ${this.tooltip ? `<span class="kpi-info-icon" title="${this.tooltip}">${this.getIconSvg('info')}</span>` : ''}
        </div>
        <div class="kpi-card-icon">
          ${this.getIconSvg(this.icon)}
        </div>
      </div>
    `;

    // Trend badge
    let trendHtml = '';
    if (this.trend) {
      const dir = this.trend.direction || 'neutral';
      const trendIcon = dir === 'up' ? this.getIconSvg('trendUp') : (dir === 'down' ? this.getIconSvg('trendDown') : '');
      trendHtml = `
        <span class="kpi-trend kpi-trend-${dir}" title="${this.trend.label || ''}">
          ${trendIcon} ${this.trend.value}
        </span>
      `;
    }

    // Corpo
    let bodyHtml = `
      <div class="kpi-card-body">
        <div class="kpi-card-value">${this.formatValue(this.value)}</div>
        ${trendHtml}
      </div>
    `;

    // Rodapé & Progresso
    let footerHtml = '';
    if (this.subtitle || this.progress !== null) {
      footerHtml = `
        <div class="kpi-card-footer">
          ${this.subtitle ? `<div class="kpi-card-subtitle">${this.subtitle}</div>` : ''}
          ${this.progress !== null ? `
            <div class="kpi-progress-bar">
              <div class="kpi-progress-fill" style="width: ${this.progress}%"></div>
            </div>
          ` : ''}
        </div>
      `;
    }

    card.innerHTML = `${headerHtml}${bodyHtml}${footerHtml}`;

    if (this.interactive && this.onClick) {
      card.addEventListener('click', () => {
        this.onClick(this);
      });
    }

    this.element = card;
    return card;
  }

  /** Atualiza o valor dinamicamente */
  setValue(newValue, newSubtitle, newProgress) {
    this.value = newValue;
    if (newSubtitle !== undefined) this.subtitle = newSubtitle;
    if (newProgress !== undefined) this.progress = newProgress;
    
    if (this.element) {
      const valEl = this.element.querySelector('.kpi-card-value');
      if (valEl) valEl.textContent = this.formatValue(this.value);
      
      const subEl = this.element.querySelector('.kpi-card-subtitle');
      if (subEl && this.subtitle) subEl.textContent = this.subtitle;
      
      const progEl = this.element.querySelector('.kpi-progress-fill');
      if (progEl && this.progress !== null) progEl.style.width = `${this.progress}%`;
    }
  }

  /** Define o estado de selecionado */
  setSelected(selected) {
    this.isSelected = Boolean(selected);
    if (this.element) {
      this.element.classList.toggle('selected', this.isSelected);
    }
  }

  /** Define o estado de loading */
  setLoading(loading) {
    this.isLoading = Boolean(loading);
    if (this.element) {
      this.element.classList.toggle('loading', this.isLoading);
    }
  }

  /** Monta o card dentro de um elemento alvo */
  mount(target) {
    const container = typeof target === 'string' ? document.querySelector(target) : target;
    if (container) {
      container.appendChild(this.render());
    }
    return this;
  }
}
