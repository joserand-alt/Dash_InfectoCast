/**
 * InfectoCast Component Library - RecentSyncModal (Dark Command-Center)
 * Modal de Telemetria de Matrículas e Sincronizações RD Station das últimas 24h.
 */

import { BaseModal } from './BaseModal.js';

export class RecentSyncModal extends BaseModal {
  constructor(options = {}) {
    super({
      ...options,
      title: 'TELEMETRIA // MATRÍCULAS SINCRONIZADAS (ÚLTIMAS 24H)',
      size: 'large'
    });
    this.students = [];
  }

  /**
   * Abre o modal com os dados de sincronização
   * @param {Object} data
   * @param {Array<Object>} data.students - Lista de alunos sincronizados nas últimas 24h
   * @param {string} [data.lastSync] - Horário do último disparo
   * @param {number} [data.successRate] - Taxa de sucesso (ex: 100)
   */
  open(data = {}) {
    this.students = data.students || [];
    const lastSync = data.lastSync || 'Há 3 minutos';
    const total = this.students.length;
    const successRate = data.successRate || 100;

    if (!this.bodyEl) return;

    this.bodyEl.innerHTML = `
      <!-- Telemetry Highlights Bar -->
      <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 14px; margin-bottom: 20px;">
        <div style="background: rgba(15, 23, 42, 0.7); border: 1px solid rgba(6, 182, 212, 0.3); border-radius: 10px; padding: 14px; display: flex; align-items: center; gap: 12px; box-shadow: 0 0 15px rgba(6, 182, 212, 0.1);">
          <div style="width: 38px; height: 38px; border-radius: 8px; background: rgba(6, 182, 212, 0.15); border: 1px solid rgba(6, 182, 212, 0.4); display: flex; align-items: center; justify-content: center; color: #38bdf8;">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>
          </div>
          <div>
            <div style="font-size: 0.75rem; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.05em;">Matrículas 24h</div>
            <div style="font-size: 1.35rem; font-weight: 800; color: #38bdf8; font-family: 'JetBrains Mono', monospace; text-shadow: 0 0 10px rgba(56, 189, 248, 0.5);">${total} Alunos</div>
          </div>
        </div>

        <div style="background: rgba(15, 23, 42, 0.7); border: 1px solid rgba(16, 185, 129, 0.3); border-radius: 10px; padding: 14px; display: flex; align-items: center; gap: 12px; box-shadow: 0 0 15px rgba(16, 185, 129, 0.1);">
          <div style="width: 38px; height: 38px; border-radius: 8px; background: rgba(16, 185, 129, 0.15); border: 1px solid rgba(16, 185, 129, 0.4); display: flex; align-items: center; justify-content: center; color: #34d399;">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
          </div>
          <div>
            <div style="font-size: 0.75rem; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.05em;">Status API RD</div>
            <div style="font-size: 1.35rem; font-weight: 800; color: #34d399; font-family: 'JetBrains Mono', monospace;">${successRate}% OK</div>
          </div>
        </div>

        <div style="background: rgba(15, 23, 42, 0.7); border: 1px solid rgba(168, 85, 247, 0.3); border-radius: 10px; padding: 14px; display: flex; align-items: center; gap: 12px; box-shadow: 0 0 15px rgba(168, 85, 247, 0.1);">
          <div style="width: 38px; height: 38px; border-radius: 8px; background: rgba(168, 85, 247, 0.15); border: 1px solid rgba(168, 85, 247, 0.4); display: flex; align-items: center; justify-content: center; color: #c084fc;">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
          </div>
          <div>
            <div style="font-size: 0.75rem; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.05em;">Último Disparo</div>
            <div style="font-size: 1.1rem; font-weight: 700; color: #e2e8f0; font-family: 'JetBrains Mono', monospace;">${lastSync}</div>
          </div>
        </div>
      </div>

      <!-- Quick Search in Modal -->
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; gap: 12px; flex-wrap: wrap;">
        <span style="font-size: 0.85rem; color: #94a3b8; font-weight: 600;">LISTA DE MATRÍCULAS PROCESSADAS & TAGUEADAS:</span>
        <input type="text" id="sync-modal-search" placeholder="Filtrar por aluno, e-mail ou curso..." style="
          background: rgba(15, 23, 42, 0.8);
          border: 1px solid rgba(255, 255, 255, 0.12);
          border-radius: 8px;
          padding: 7px 14px;
          font-size: 0.825rem;
          color: #f1f5f9;
          width: 260px;
          outline: none;
        " />
      </div>

      <!-- Students Table -->
      <div style="max-height: 380px; overflow-y: auto; border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 8px; background: rgba(11, 15, 25, 0.8);">
        <table class="datatable" style="width: 100%; border-collapse: collapse;">
          <thead>
            <tr>
              <th style="padding: 10px 14px; font-size: 0.75rem; text-align: left; color: #94a3b8; border-bottom: 1px solid rgba(255, 255, 255, 0.08);">ALUNO / CONTATO</th>
              <th style="padding: 10px 14px; font-size: 0.75rem; text-align: left; color: #94a3b8; border-bottom: 1px solid rgba(255, 255, 255, 0.08);">CURSO MATRICULADO</th>
              <th style="padding: 10px 14px; font-size: 0.75rem; text-align: left; color: #94a3b8; border-bottom: 1px solid rgba(255, 255, 255, 0.08);">HORÁRIO</th>
              <th style="padding: 10px 14px; font-size: 0.75rem; text-align: left; color: #94a3b8; border-bottom: 1px solid rgba(255, 255, 255, 0.08);">TAGS APLICADAS NO RD</th>
              <th style="padding: 10px 14px; font-size: 0.75rem; text-align: center; color: #94a3b8; border-bottom: 1px solid rgba(255, 255, 255, 0.08);">STATUS RD</th>
            </tr>
          </thead>
          <tbody id="sync-modal-tbody">
            ${this._renderRows(this.students)}
          </tbody>
        </table>
      </div>
    `;

    // Filtro de busca dentro do modal
    const searchInput = this.bodyEl.querySelector('#sync-modal-search');
    if (searchInput) {
      searchInput.addEventListener('input', (e) => {
        const term = e.target.value.toLowerCase().trim();
        const filtered = this.students.filter(s => 
          (s.nome || '').toLowerCase().includes(term) ||
          (s.email || '').toLowerCase().includes(term) ||
          (s.curso || '').toLowerCase().includes(term)
        );
        const tbody = this.bodyEl.querySelector('#sync-modal-tbody');
        if (tbody) tbody.innerHTML = this._renderRows(filtered);
      });
    }

    super.open();
  }

  _renderRows(studentsList) {
    if (!studentsList || studentsList.length === 0) {
      return `<tr><td colspan="5" style="text-align: center; padding: 24px; color: #64748b;">Nenhuma sincronização recente encontrada.</td></tr>`;
    }

    return studentsList.map(s => {
      const initials = (s.nome || 'A').split(' ').map(n => n[0]).slice(0, 2).join('').toUpperCase();
      const tags = s.tags || ['aluno-ativo', 'academy-pago'];
      
      return `
        <tr style="border-bottom: 1px solid rgba(255, 255, 255, 0.04);">
          <td style="padding: 10px 14px;">
            <div class="student-cell">
              <div class="student-avatar" style="background: linear-gradient(135deg, #06b6d4, #3b82f6); box-shadow: 0 0 8px rgba(6, 182, 212, 0.4);">${initials}</div>
              <div class="student-info">
                <span class="student-name">${s.nome || 'Sem Nome'}</span>
                <span class="student-email">${s.email || '—'}</span>
              </div>
            </div>
          </td>
          <td style="padding: 10px 14px;">
            <span class="course-tag">${s.curso || 'Pós-Graduação'}</span>
          </td>
          <td style="padding: 10px 14px; color: #94a3b8; font-size: 0.8rem; font-family: 'JetBrains Mono', monospace;">
            ${s.horario || 'Hoje às 10:15'}
          </td>
          <td style="padding: 10px 14px;">
            <div style="display: flex; gap: 4px; flex-wrap: wrap;">
              ${tags.map(t => `<span style="padding: 2px 6px; border-radius: 4px; font-size: 0.72rem; font-family: 'JetBrains Mono', monospace; background: rgba(16, 185, 129, 0.12); border: 1px solid rgba(16, 185, 129, 0.3); color: #34d399;">#${t}</span>`).join('')}
            </div>
          </td>
          <td style="padding: 10px 14px; text-align: center;">
            <span class="status-badge status-ativo">
              <span class="status-dot"></span> Sincronizado
            </span>
          </td>
        </tr>
      `;
    }).join('');
  }
}
