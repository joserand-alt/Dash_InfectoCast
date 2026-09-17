/**
 * InfectoCast Component Library - FunnelPyramidChart
 * Visualização do funil de conversão de leads até a matrícula.
 */

export class FunnelPyramidChart {
  /**
   * @param {Object} options
   * @param {string} [options.id]
   * @param {string} options.title
   * @param {Array<Object>} options.stages - [{ name: 'Leads Totais', count: 26566, color: '#3b82f6' }, ...]
   */
  constructor(options = {}) {
    this.id = options.id || `funnel-${Math.random().toString(36).substr(2, 9)}`;
    this.title = options.title || '🚀 Funil de Conversão de Leads & Matrículas';
    this.subtitle = options.subtitle || 'Eficiência das etapas de captação até a compra da pós-graduação';
    this.stages = options.stages || [];
    this.element = null;
  }

  setData(stages) {
    this.stages = stages || [];
    if (this.element) {
      const parent = this.element.parentNode;
      if (parent) {
        const newEl = this.render();
        parent.replaceChild(newEl, this.element);
      }
    }
  }

  render() {
    const card = document.createElement('div');
    card.id = this.id;
    card.className = 'chart-card';

    const maxCount = Math.max(1, ...(this.stages.map(s => s.count || 0)));

    let stagesHtml = this.stages.map((stage, idx) => {
      const pctOfMax = ((stage.count / maxCount) * 100).toFixed(1);
      const prevCount = idx > 0 ? this.stages[idx - 1].count : null;
      const convRate = prevCount ? ((stage.count / prevCount) * 100).toFixed(1) + '% de conv.' : '100% base';

      return `
        <div class="funnel-stage">
          <div class="funnel-stage-header">
            <span>${stage.name}</span>
            <span><strong>${stage.count.toLocaleString('pt-BR')}</strong> <small style="color: #64748b; font-weight: normal;">(${convRate})</small></span>
          </div>
          <div class="funnel-stage-bar-wrap">
            <div class="funnel-stage-bar-fill" style="width: ${Math.max(4, pctOfMax)}%; background: ${stage.color || '#0284c7'};"></div>
            <span class="funnel-stage-bar-label">${pctOfMax}%</span>
          </div>
        </div>
      `;
    }).join('');

    card.innerHTML = `
      <div class="chart-header">
        <div class="chart-title-wrap">
          <h3 class="chart-title">${this.title}</h3>
          <span class="chart-subtitle">${this.subtitle}</span>
        </div>
      </div>
      <div class="funnel-container">
        ${stagesHtml}
      </div>
    `;

    this.element = card;
    return card;
  }

  mount(target) {
    const container = typeof target === 'string' ? document.querySelector(target) : target;
    if (container) {
      container.appendChild(this.render());
    }
    return this;
  }
}
