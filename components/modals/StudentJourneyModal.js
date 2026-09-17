/**
 * InfectoCast Component Library - StudentJourneyModal
 * Modal da jornada 360° do aluno: perfil, métricas e linha do tempo de eventos.
 */

import { BaseModal } from './BaseModal.js';

export class StudentJourneyModal extends BaseModal {
  constructor(options = {}) {
    super({
      title: options.title || 'Jornada 360° do Aluno',
      size: 'large',
      ...options
    });
  }

  /** Exibe os dados do aluno e monta a linha do tempo */
  showStudent(student) {
    if (!student) return;

    this.setTitle(`Jornada 360° · ${student.nome || 'Aluno'}`);

    const initials = (student.nome || 'A').split(' ').map(n => n[0]).slice(0, 2).join('').toUpperCase();
    const events = student.eventos || [];

    const content = document.createElement('div');
    content.innerHTML = `
      <!-- Cabeçalho do Perfil -->
      <div class="student-profile-header">
        <div class="student-profile-avatar">${initials}</div>
        <div class="student-profile-details">
          <div class="student-profile-name">${student.nome || 'Sem Nome'}</div>
          <div class="student-profile-meta">
            <span>✉️ ${student.email || '—'}</span>
            ${student.telefone ? `<span>📱 ${student.telefone}</span>` : ''}
            <span>🎓 <strong>${student.curso || 'Pós-Graduação'}</strong></span>
          </div>
        </div>
      </div>

      <!-- Mini Cards de Estatísticas -->
      <div class="modal-stat-grid">
        <div class="modal-stat-card">
          <span class="modal-stat-label">Progresso</span>
          <span class="modal-stat-val" style="color: #0284c7;">${student.progresso || 0}%</span>
        </div>
        <div class="modal-stat-card">
          <span class="modal-stat-label">Aulas Concluídas</span>
          <span class="modal-stat-val">${student.aulas_assistidas || 0} <small style="font-size: 0.8rem; color: #64748b;">/ ${student.total_aulas || 40}</small></span>
        </div>
        <div class="modal-stat-card">
          <span class="modal-stat-label">Status Acesso</span>
          <span class="modal-stat-val" style="font-size: 1rem; color: #10b981;">${student.status || 'Ativo'}</span>
        </div>
        <div class="modal-stat-card">
          <span class="modal-stat-label">Gateway / Origem</span>
          <span class="modal-stat-val" style="font-size: 1rem;">${student.gateway || 'Asaas'}</span>
        </div>
      </div>

      <!-- Linha do Tempo da Jornada -->
      <div class="timeline-section-title">
        <span>⏱️ Linha do Tempo Cronológica</span>
      </div>

      <div class="journey-timeline">
        ${this.renderTimelineItems(events, student)}
      </div>
    `;

    this.open(content);
  }

  renderTimelineItems(events, student) {
    if (!events || events.length === 0) {
      return `
        <div class="timeline-item">
          <div class="timeline-node timeline-node-payment"></div>
          <div class="timeline-content">
            <div class="timeline-content-header">
              <span>Matrícula Confirmada</span>
              <span>${student.dt_matricula || 'Recente'}</span>
            </div>
            <div class="timeline-content-title">Entrada na Plataforma de Ensino</div>
            <div class="timeline-content-desc">Aluno matriculado no curso ${student.curso || 'InfectoCast'}</div>
          </div>
        </div>
      `;
    }

    return events.map((ev, idx) => {
      let nodeClass = 'timeline-node-lead';
      let tag = 'Interação Marketing';
      const evLow = String(ev.nome || ev).toLowerCase();

      if (evLow.includes('pago') || evLow.includes('matrícula') || evLow.includes('compra')) {
        nodeClass = 'timeline-node-payment';
        tag = 'Transação / Matrícula';
      } else if (evLow.includes('aula') || evLow.includes('módulo') || evLow.includes('assistiu')) {
        nodeClass = 'timeline-node-lesson';
        tag = 'Progresso Acadêmico';
      }

      return `
        <div class="timeline-item">
          <div class="timeline-node ${nodeClass}"></div>
          <div class="timeline-content">
            <div class="timeline-content-header">
              <span>${tag}</span>
              <span>${ev.data || 'Etapa ' + (idx + 1)}</span>
            </div>
            <div class="timeline-content-title">${ev.nome || ev}</div>
            ${ev.desc ? `<div class="timeline-content-desc">${ev.desc}</div>` : ''}
          </div>
        </div>
      `;
    }).join('');
  }
}
