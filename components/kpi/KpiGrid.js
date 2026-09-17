/**
 * InfectoCast Component Library - KpiGrid
 * Container flexível e responsivo para organização de cards de KPI.
 */

import { KpiCard } from './KpiCard.js';

export class KpiGrid {
  /**
   * @param {Object} options
   * @param {string} [options.id] - ID do container
   * @param {number|string} [options.columns='auto'] - 1 | 2 | 3 | 4 | 5 | 6 | 'auto'
   * @param {string} [options.gap='16px'] - Espaçamento entre os cards
   * @param {Array<KpiCard|Object>} [options.cards=[]] - Lista de instâncias ou configurações de KpiCard
   * @param {string} [options.className=''] - Classes CSS adicionais
   */
  constructor(options = {}) {
    this.id = options.id || `kpi-grid-${Math.random().toString(36).substr(2, 9)}`;
    this.columns = options.columns || 'auto';
    this.gap = options.gap || '16px';
    this.className = options.className || '';
    this.cards = (options.cards || []).map(c => c instanceof KpiCard ? c : new KpiCard(c));
    this.element = null;
  }

  /** Adiciona um novo card à grade */
  addCard(card) {
    const kpiCard = card instanceof KpiCard ? card : new KpiCard(card);
    this.cards.push(kpiCard);
    if (this.element) {
      this.element.appendChild(kpiCard.render());
    }
    return kpiCard;
  }

  /** Retorna um card pelo ID */
  getCard(id) {
    return this.cards.find(c => c.id === id);
  }

  /** Renderiza a grade e seus cards */
  render() {
    const grid = document.createElement('div');
    grid.id = this.id;
    const colClass = this.columns === 'auto' ? 'kpi-grid-auto' : `kpi-grid-cols-${this.columns}`;
    grid.className = `kpi-grid ${colClass} ${this.className}`.trim();
    if (this.gap) grid.style.gap = this.gap;

    this.cards.forEach(card => {
      grid.appendChild(card.render());
    });

    this.element = grid;
    return grid;
  }

  /** Monta a grade no elemento de destino */
  mount(target) {
    const container = typeof target === 'string' ? document.querySelector(target) : target;
    if (container) {
      container.appendChild(this.render());
    }
    return this;
  }

  /** Desmonta e limpa a grade */
  destroy() {
    if (this.element && this.element.parentNode) {
      this.element.parentNode.removeChild(this.element);
    }
    this.element = null;
  }
}
