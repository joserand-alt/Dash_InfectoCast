/**
 * InfectoCast Component Library - SyncStatusModal
 * Modal para exibição do status e execução de sincronização online com APIs.
 */

import { BaseModal } from './BaseModal.js';

export class SyncStatusModal extends BaseModal {
  constructor(options = {}) {
    super({
      title: options.title || 'Sincronização de Dados Online',
      size: 'default',
      ...options
    });
  }

  showSyncStatus(statusData = {}) {
    const content = document.createElement('div');
    content.innerHTML = `
      <div style="text-align: center; padding: 10px 0 20px 0;">
        <div style="width: 50px; height: 50px; border-radius: 50%; background: #ecfdf5; color: #10b981; display: inline-flex; align-items: center; justify-content: center; font-size: 1.5rem; margin-bottom: 12px;">
          ☁️
        </div>
        <h4 style="font-size: 1.1rem; font-weight: 700; color: #0f172a; margin-bottom: 4px;">Atualização 100% em Nuvem Ativa</h4>
        <p style="font-size: 0.85rem; color: #64748b;">Os dados são sincronizados automaticamente a cada hora via GitHub Actions.</p>
      </div>

      <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 10px; padding: 16px; margin-bottom: 16px;">
        <div style="display: flex; justify-content: space-between; font-size: 0.85rem; padding: 6px 0; border-bottom: 1px solid #f1f5f9;">
          <span style="color: #64748b;">InfectoCast Academy API:</span>
          <strong style="color: #10b981;">● Online (7.489 logs)</strong>
        </div>
        <div style="display: flex; justify-content: space-between; font-size: 0.85rem; padding: 6px 0; border-bottom: 1px solid #f1f5f9;">
          <span style="color: #64748b;">Cativa Digital API:</span>
          <strong style="color: #10b981;">● Online (12.839 logs)</strong>
        </div>
        <div style="display: flex; justify-content: space-between; font-size: 0.85rem; padding: 6px 0; border-bottom: 1px solid #f1f5f9;">
          <span style="color: #64748b;">Asaas & Vindi Financeiro:</span>
          <strong style="color: #10b981;">● Online (807 alunos)</strong>
        </div>
        <div style="display: flex; justify-content: space-between; font-size: 0.85rem; padding: 6px 0;">
          <span style="color: #64748b;">RD Station Marketing:</span>
          <strong style="color: #10b981;">● Online (26.566 leads)</strong>
        </div>
      </div>

      <div style="text-align: center;">
        <a href="https://github.com/joserand-alt/Dash_InfectoCast/actions" target="_blank" class="action-btn" style="padding: 10px 20px; font-size: 0.85rem; text-decoration: none; display: inline-block;">
          🚀 Disparar Sincronização Imediata no GitHub
        </a>
      </div>
    `;

    this.open(content);
  }
}
