/**
 * InfectoCast Component Library - LeadsTable (Dark Command-Center)
 * Especialização de DataTable para análise de Leads, ICP Scoring e Conversão via WhatsApp.
 */

import { DataTable } from './DataTable.js';

export class LeadsTable extends DataTable {
  /**
   * @param {Object} options
   * @param {Array<Object>} options.leads - Lista de leads
   * @param {Function} [options.onWhatsApp] - Callback ao clicar no botão de WhatsApp
   */
  constructor(options = {}) {
    const columns = [
      {
        key: 'nome',
        label: 'Lead / Contato',
        width: '240px',
        render: (val, row) => {
          const initials = (val || 'L').split(' ').map(n => n[0]).slice(0, 2).join('').toUpperCase();
          return `
            <div class="student-cell">
              <div class="student-avatar" style="background: linear-gradient(135deg, #a855f7, #6366f1); box-shadow: 0 0 10px rgba(168, 85, 247, 0.4); border-color: rgba(168, 85, 247, 0.6);">${initials}</div>
              <div class="student-info">
                <span class="student-name">${val || 'Lead Sem Nome'}</span>
                <span class="student-email">${row.email || '—'}</span>
              </div>
            </div>
          `;
        }
      },
      {
        key: 'score',
        label: 'Score (ICP)',
        width: '160px',
        render: (val) => {
          const score = Math.min(100, Math.max(0, Math.round(Number(val) || 0)));
          let color = '#ef4444'; // Laser Crimson
          let shadow = 'rgba(239, 68, 68, 0.4)';
          if (score >= 75) {
            color = '#10b981'; // Matrix Emerald
            shadow = 'rgba(16, 185, 129, 0.5)';
          } else if (score >= 50) {
            color = '#f59e0b'; // Hologram Amber
            shadow = 'rgba(245, 158, 11, 0.5)';
          } else if (score >= 25) {
            color = '#06b6d4'; // Electric Cyan
            shadow = 'rgba(6, 182, 212, 0.5)';
          }

          return `
            <div class="table-progress-wrap">
              <div class="table-progress-bar" style="height: 8px; background: rgba(15, 23, 42, 0.8); border: 1px solid rgba(255,255,255,0.06);">
                <div class="table-progress-fill" style="width: ${score}%; background: ${color}; box-shadow: 0 0 10px ${shadow};"></div>
              </div>
              <span class="table-progress-text" style="color: ${color}; font-weight: 700;">${score}</span>
            </div>
          `;
        }
      },
      {
        key: 'maturidade',
        label: 'Maturidade',
        render: (val, row) => {
          const score = Math.round(Number(row.score) || 0);
          let mat = val || (score >= 75 ? 'Pronto' : score >= 50 ? 'Quente' : score >= 25 ? 'Morno' : 'Frio');
          let cls = 'status-nunca';
          if (mat.includes('Pronto') || mat.includes('Quente')) cls = 'status-ativo';
          else if (mat.includes('Morno')) cls = 'status-risco';
          else cls = 'status-abandono';

          return `<span class="status-badge ${cls}"><span class="status-dot"></span> ${mat}</span>`;
        }
      },
      {
        key: 'profissao',
        label: 'Perfil / Especialidade',
        render: (val) => `<span style="color: #94a3b8; font-size: 0.825rem; font-weight: 500;">${val || 'Médico Geral'}</span>`
      },
      {
        key: 'interesse',
        label: 'Interesse Principal',
        render: (val) => `<span class="course-tag" style="background: rgba(168, 85, 247, 0.12); border-color: rgba(168, 85, 247, 0.35); color: #c084fc;">${val || 'Pós-Graduação'}</span>`
      },
      {
        key: 'origem',
        label: 'Origem',
        render: (val) => `<span style="color: #64748b; font-size: 0.8rem;">${val || 'RD Station'}</span>`
      },
      {
        key: 'actions',
        label: 'Ações de Contato',
        sortable: false,
        align: 'center',
        render: (_, row) => {
          const btn = document.createElement('button');
          btn.className = 'action-btn';
          btn.style.cssText = 'background: rgba(16, 185, 129, 0.15); border-color: rgba(16, 185, 129, 0.4); color: #34d399; display: inline-flex; align-items: center; gap: 6px;';
          btn.innerHTML = `
            <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><path d="M.057 24l1.687-6.163c-1.041-1.804-1.588-3.849-1.587-5.946.003-6.556 5.338-11.891 11.893-11.891 3.181.001 6.167 1.24 8.413 3.488 2.245 2.248 3.481 5.236 3.48 8.414-.003 6.557-5.338 11.892-11.893 11.892-1.99-.001-3.951-.5-5.688-1.448l-6.305 1.654zm6.597-3.807c1.676.995 3.276 1.591 5.392 1.592 5.448 0 9.886-4.434 9.889-9.885.002-5.462-4.415-9.89-9.881-9.892-5.452 0-9.887 4.434-9.889 9.884-.001 2.225.651 3.891 1.746 5.634l-.999 3.648 3.742-.981z"/></svg>
            WhatsApp
          `;
          btn.addEventListener('click', (e) => {
            e.stopPropagation();
            if (typeof options.onWhatsApp === 'function') {
              options.onWhatsApp(row);
            } else {
              const tel = (row.telefone || '').replace(/\D/g, '');
              const msg = encodeURIComponent(`Olá ${row.nome || ''}! Vimos seu interesse nos cursos da InfectoCast. Como podemos te ajudar?`);
              if (tel) {
                window.open(`https://wa.me/55${tel}?text=${msg}`, '_blank');
              } else {
                alert(`Lead ${row.nome || ''} não possui telefone cadastrado.`);
              }
            }
          });
          return btn;
        }
      }
    ];

    super({
      ...options,
      columns,
      data: options.leads || [],
      searchPlaceholder: 'Buscar leads por nome, e-mail, perfil ou interesse...',
      searchKeys: ['nome', 'email', 'profissao', 'interesse', 'origem']
    });

    this.onWhatsApp = options.onWhatsApp || null;
  }
}
