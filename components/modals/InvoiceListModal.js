/**
 * InfectoCast Component Library - InvoiceListModal
 * Modal para exibição detalhada de faturas, cobranças e parcelas financeiras.
 */

import { BaseModal } from './BaseModal.js';

export class InvoiceListModal extends BaseModal {
  constructor(options = {}) {
    super({
      title: options.title || 'Faturas & Cobranças',
      size: 'large',
      ...options
    });
  }

  /** Exibe a lista de faturas */
  showInvoices(invoices, titleSuffix = '') {
    if (!invoices) return;

    this.setTitle(`Faturas & Parcelas ${titleSuffix}`);

    const content = document.createElement('div');

    const totalValor = invoices.reduce((acc, f) => acc + (f.valor || 0), 0);
    const pagasCount = invoices.filter(f => (f.status || '').toLowerCase().includes('pago')).length;

    content.innerHTML = `
      <div class="modal-stat-grid" style="grid-template-columns: repeat(3, 1fr);">
        <div class="modal-stat-card">
          <span class="modal-stat-label">Total de Faturas</span>
          <span class="modal-stat-val">${invoices.length}</span>
        </div>
        <div class="modal-stat-card">
          <span class="modal-stat-label">Valor Consolidado</span>
          <span class="modal-stat-val" style="color: #10b981;">${totalValor.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })}</span>
        </div>
        <div class="modal-stat-card">
          <span class="modal-stat-label">Liquidadas</span>
          <span class="modal-stat-val">${pagasCount} <small style="font-size: 0.8rem; color: #64748b;">/ ${invoices.length}</small></span>
        </div>
      </div>

      <div style="overflow-x: auto; max-height: 380px; border: 1px solid #e2e8f0; border-radius: 8px;">
        <table class="modal-table">
          <thead>
            <tr>
              <th>Aluno / Cliente</th>
              <th>Plano / Descrição</th>
              <th>Vencimento</th>
              <th>Valor</th>
              <th>Status</th>
              <th>Ação</th>
            </tr>
          </thead>
          <tbody>
            ${invoices.map(f => {
              const statusCls = (f.status || '').toLowerCase().includes('pago') ? 'status-ativo' : 'status-risco';
              return `
                <tr>
                  <td><strong>${f.aluno || '—'}</strong><br><small style="color: #64748b;">${f.email || ''}</small></td>
                  <td>${f.plano || f.description || 'Assinatura'}</td>
                  <td>${f.vencimento || '—'}</td>
                  <td><strong>${(f.valor || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })}</strong></td>
                  <td><span class="status-badge ${statusCls}">${f.status_label || f.status || 'Pendente'}</span></td>
                  <td>
                    ${f.url ? `<a href="${f.url}" target="_blank" class="action-btn" style="text-decoration: none;">Ver Fatura</a>` : '—'}
                  </td>
                </tr>
              `;
            }).join('')}
          </tbody>
        </table>
      </div>
    `;

    this.open(content);
  }
}
