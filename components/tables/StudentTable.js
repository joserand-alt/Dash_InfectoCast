/**
 * InfectoCast Component Library - StudentTable
 * Especialização de DataTable para exibição de alunos, progresso e matrículas.
 */

import { DataTable } from './DataTable.js';

export class StudentTable extends DataTable {
  /**
   * @param {Object} options
   * @param {Array<Object>} options.students - Lista de alunos
   * @param {Function} [options.onVerJornada] - Callback ao clicar em 'Ver Jornada'
   */
  constructor(options = {}) {
    const columns = [
      {
        key: 'nome',
        label: 'Aluno',
        width: '280px',
        render: (val, row) => {
          const initials = (val || 'A').split(' ').map(n => n[0]).slice(0, 2).join('').toUpperCase();
          return `
            <div class="student-cell">
              <div class="student-avatar">${initials}</div>
              <div class="student-info">
                <span class="student-name">${val || 'Sem Nome'}</span>
                <span class="student-email">${row.email || '—'}</span>
              </div>
            </div>
          `;
        }
      },
      {
        key: 'curso',
        label: 'Curso / Pós',
        render: (val) => `<span class="course-tag" title="${val || ''}">${val || 'Geral'}</span>`
      },
      {
        key: 'status',
        label: 'Status de Acesso',
        render: (val) => {
          const s = (val || 'nunca').toLowerCase();
          let cls = 'status-nunca';
          let label = 'Nunca Acessou';
          if (s.includes('ativo')) { cls = 'status-ativo'; label = 'Ativo'; }
          else if (s.includes('risco')) { cls = 'status-risco'; label = 'Em Risco'; }
          else if (s.includes('abandono')) { cls = 'status-abandono'; label = 'Abandono'; }
          
          return `<span class="status-badge ${cls}"><span class="status-dot"></span> ${label}</span>`;
        }
      },
      {
        key: 'progresso',
        label: 'Progresso',
        width: '180px',
        render: (val, row) => {
          const pct = Math.min(100, Math.max(0, Math.round(Number(val) || 0)));
          const assistidas = row.aulas_assistidas || 0;
          const total = row.total_aulas || 0;
          return `
            <div class="table-progress-wrap">
              <div class="table-progress-bar">
                <div class="table-progress-fill" style="width: ${pct}%"></div>
              </div>
              <span class="table-progress-text">${pct}%</span>
            </div>
          `;
        }
      },
      {
        key: 'ultimo_acesso',
        label: 'Último Acesso',
        render: (val) => `<span style="color: #64748b; font-size: 0.825rem;">${val || '—'}</span>`
      },
      {
        key: 'actions',
        label: 'Ações',
        sortable: false,
        align: 'center',
        render: (_, row) => {
          const btn = document.createElement('button');
          btn.className = 'action-btn';
          btn.textContent = 'Ver Jornada';
          btn.addEventListener('click', (e) => {
            e.stopPropagation();
            if (typeof options.onVerJornada === 'function') {
              options.onVerJornada(row);
            }
          });
          return btn;
        }
      }
    ];

    super({
      ...options,
      columns,
      data: options.students || [],
      searchPlaceholder: 'Buscar por aluno, email ou curso...',
      searchKeys: ['nome', 'email', 'curso', 'telefone']
    });

    this.onVerJornada = options.onVerJornada || null;
  }
}
