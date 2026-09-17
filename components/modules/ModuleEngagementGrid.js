/**
 * InfectoCast Component Library - ModuleEngagementGrid (Dark Command-Center)
 * Componente visual para análise de engajamento por módulo e detecção de gargalos/atrito.
 */

export class ModuleEngagementGrid {
  /**
   * @param {Object} options
   * @param {string} [options.id] - ID do container
   * @param {Array<Object>} options.modules - Dados dos módulos
   * @param {Function} [options.onLessonSelect] - Callback ao selecionar uma aula
   */
  constructor(options = {}) {
    this.id = options.id || `module-grid-${Math.random().toString(36).substr(2, 9)}`;
    this.modules = options.modules || [];
    this.onLessonSelect = options.onLessonSelect || null;
    this.element = null;
    this.expandedModules = new Set();
  }

  setModules(modules) {
    this.modules = modules || [];
    this.render();
  }

  render(containerId) {
    let container = null;
    if (containerId) {
      container = typeof containerId === 'string' ? document.getElementById(containerId) : containerId;
    } else if (this.element && this.element.parentElement) {
      container = this.element.parentElement;
    }

    if (!container) return;

    if (!this.element) {
      this.element = document.createElement('div');
      this.element.id = this.id;
      this.element.className = 'modules-grid';
      container.appendChild(this.element);
    }

    this.element.innerHTML = '';

    if (this.modules.length === 0) {
      this.element.innerHTML = `
        <div style="grid-column: 1/-1; text-align: center; padding: 40px; color: #64748b;">
          Nenhum módulo disponível para exibição.
        </div>
      `;
      return;
    }

    this.modules.forEach((mod, idx) => {
      const card = this._createModuleCard(mod, idx);
      this.element.appendChild(card);
    });
  }

  _createModuleCard(mod, idx) {
    const card = document.createElement('div');
    const isFriction = Boolean(mod.is_friction || mod.queda_taxa > 25);
    card.className = `module-hud-card ${isFriction ? 'is-friction' : ''}`;

    const completionRate = Math.min(100, Math.max(0, Math.round(Number(mod.taxa_conclusao || mod.progresso_medio || 0))));
    let color = '#38bdf8';
    let shadow = 'rgba(56, 189, 248, 0.4)';
    if (isFriction) {
      color = '#ef4444';
      shadow = 'rgba(239, 68, 68, 0.4)';
    } else if (completionRate >= 70) {
      color = '#10b981';
      shadow = 'rgba(16, 185, 129, 0.4)';
    } else if (completionRate >= 40) {
      color = '#f59e0b';
      shadow = 'rgba(245, 158, 11, 0.4)';
    }

    const isExpanded = this.expandedModules.has(idx);

    card.innerHTML = `
      <div class="module-card-header">
        <span class="module-badge-id ${isFriction ? 'friction' : ''}">${mod.codigo || `MÓDULO ${idx + 1}`}</span>
        <span class="status-badge ${isFriction ? 'status-abandono' : completionRate >= 70 ? 'status-ativo' : 'status-risco'}">
          <span class="status-dot"></span> ${isFriction ? '⚠️ Gargalo' : completionRate >= 70 ? '⚡ Alto Engajamento' : 'Estável'}
        </span>
      </div>

      <h4 class="module-card-title">${mod.nome || `Módulo ${idx + 1}`}</h4>

      <div class="module-card-meta">
        <div class="module-meta-item">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
          ${mod.duracao_total || '1h 30m'}
        </div>
        <div class="module-meta-item">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/></svg>
          ${(mod.aulas || []).length || mod.total_aulas || 0} aulas
        </div>
      </div>

      <div class="module-progress-section">
        <div class="module-progress-header">
          <span class="module-progress-label">Taxa Média de Conclusão</span>
          <span class="module-progress-value" style="color: ${color}; text-shadow: 0 0 8px ${shadow};">${completionRate}%</span>
        </div>
        <div class="module-progress-track">
          <div class="module-progress-bar" style="width: ${completionRate}%; background: ${color}; box-shadow: 0 0 10px ${shadow};"></div>
        </div>
      </div>

      ${isFriction ? `
        <div class="module-friction-alert">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
          <span>Queda de retenção de ${mod.queda_taxa || 32}% dos alunos neste ponto.</span>
        </div>
      ` : ''}

      <button class="module-expand-btn" data-idx="${idx}">
        <span>${isExpanded ? 'Ocultar Aulas' : 'Visualizar Aulas do Módulo'}</span>
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="transform: ${isExpanded ? 'rotate(180deg)' : 'rotate(0deg)'}; transition: transform 0.2s;"><polyline points="6 9 12 15 18 9"/></svg>
      </button>

      <div class="module-lessons-list" style="display: ${isExpanded ? 'flex' : 'none'};">
        ${(mod.aulas || []).map((aula, aIdx) => `
          <div class="module-lesson-row" style="cursor: pointer;" data-lesson-idx="${aIdx}">
            <span class="module-lesson-title" title="${aula.titulo || ''}">${aIdx + 1}. ${aula.titulo || `Aula ${aIdx + 1}`}</span>
            <span class="module-lesson-views">${aula.views || 0} views</span>
          </div>
        `).join('')}
      </div>
    `;

    // Event listener para expansão
    const expandBtn = card.querySelector('.module-expand-btn');
    expandBtn.addEventListener('click', () => {
      if (this.expandedModules.has(idx)) {
        this.expandedModules.delete(idx);
      } else {
        this.expandedModules.add(idx);
      }
      this.render();
    });

    // Event listener para seleção de aula
    const lessonRows = card.querySelectorAll('.module-lesson-row');
    lessonRows.forEach(row => {
      row.addEventListener('click', () => {
        const aIdx = parseInt(row.getAttribute('data-lesson-idx'), 10);
        const selectedAula = (mod.aulas || [])[aIdx];
        if (typeof this.onLessonSelect === 'function' && selectedAula) {
          this.onLessonSelect(selectedAula, mod);
        }
      });
    });

    return card;
  }
}
