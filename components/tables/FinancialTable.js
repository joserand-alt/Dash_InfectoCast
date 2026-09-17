/**
 * InfectoCast Component Library - FinancialTable (Dark Command-Center)
 * Especialização de DataTable para faturas, parcelas e controle de inadimplência (Asaas / Vindi).
 */

import { DataTable } from './DataTable.js';

export class FinancialTable extends DataTable {
  /**
   * @param {Object} options
   * @param {Array<Object>} options.invoices - Lista de faturas/cobranças
   * @param {Function} [options.onViewInvoice] - Callback ao clicar em 'Ver Fatura'
   */
  constructor(options = {}) {
    const columns = [
      {
        key: 'sacado',
        label: 'Aluno / Pagador',
        width: '240px',
        render: (val, row) => {
          const initials = (val || 'A').split(' ').map(n => n[0]).slice(0, 2).join('').toUpperCase();
          return `
            <div class="student-cell">
              <div class="student-avatar" style="background: linear-gradient(135deg, #0284c7, #06b6d4); box-shadow: 0 0 10px rgba(6, 182, 212, 0.4);">${initials}</div>
              <div class="student-info">
                <span class="student-name">${val || 'Sacado Desconhecido'}</span>
                <span class="student-email">${row.email || row.cpf || '—'}</span>
              </div>
            </div>
          `;
        }
      },
      {
        key: 'descricao',
        label: 'Descrição da Parcela / Produto',
        render: (val) => `<span style="color: #e2e8f0; font-size: 0.85rem; font-weight: 500;">${val || 'Mensalidade Pós-Graduação'}</span>`
      },
      {
        key: 'vencimento',
        label: 'Vencimento',
        render: (val, row) => {
          const isOverdue = row.status === 'VENCIDO' || row.status === 'INADIMPLENTE';
          const color = isOverdue ? '#ef4444' : '#94a3b8';
          return `<span style="color: ${color}; font-size: 0.85rem; font-weight: 600;">${val || '—'}</span>`;
        }
      },
      {
        key: 'valor',
        label: 'Valor',
        align: 'right',
        render: (val) => {
          const num = Number(val) || 0;
          return `<span style="color: #38bdf8; font-family: 'JetBrains Mono', monospace; font-size: 0.95rem; font-weight: 700; text-shadow: 0 0 8px rgba(56, 189, 248, 0.4);">R$ ${num.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>`;
        }
      },
      {
        key: 'status',
        label: 'Status da Fatura',
        render: (val) => {
          const s = (val || '').toUpperCase();
          let cls = 'status-ativo';
          let label = 'Paga / Liquidada';

          if (s.includes('PAGO') || s.includes('RECEIVED') || s.includes('CONFIRMED')) {
            cls = 'status-ativo';
            label = 'Liquidada';
          } else if (s.includes('VENCID') || s.includes('OVERDUE') || s.includes('INADIMP')) {
            cls = 'status-abandono';
            label = 'Inadimplente';
          } else if (s.includes('PEND') || s.includes('AGUARD') || s.includes('FUTUR')) {
            cls = 'status-risco';
            label = 'A Receber';
          }

          return `<span class="status-badge ${cls}"><span class="status-dot"></span> ${label}</span>`;
        }
      },
      {
        key: 'gateway',
        label: 'Gateway',
        render: (val) => {
          const isAsaas = (val || '').toLowerCase().includes('asaas');
          const bg = isAsaas ? 'rgba(56, 189, 248, 0.15)' : 'rgba(168, 85, 247, 0.15)';
          const border = isAsaas ? 'rgba(56, 189, 248, 0.4)' : 'rgba(168, 85, 247, 0.4)';
          const text = isAsaas ? '#38bdf8' : '#c084fc';
          return `<span style="padding: 3px 8px; border-radius: 6px; font-size: 0.75rem; font-weight: 700; background: ${bg}; border: 1px solid ${border}; color: ${text}; text-transform: uppercase;">${val || 'Asaas'}</span>`;
        }
      },
      {
        key: 'actions',
        label: 'Ações',
        sortable: false,
        align: 'center',
        render: (_, row) => {
          const btn = document.createElement('button');
          btn.className = 'action-btn';
          btn.textContent = 'Ver Fatura';
          btn.addEventListener('click', (e) => {
            e.stopPropagation();
            if (typeof options.onViewInvoice === 'function') {
              options.onViewInvoice(row);
            } else if (row.url_fatura) {
              window.open(row.url_fatura, '_blank');
            } else {
              alert(`Fatura #${row.id || '001'} no valor de R$ ${Number(row.valor || 0).toFixed(2)}.`);
            }
          });
          return btn;
        }
      }
    ];

    super({
      ...options,
      columns,
      data: options.invoices || [],
      searchPlaceholder: 'Buscar faturas por aluno, descrição ou gateway...',
      searchKeys: ['sacado', 'descricao', 'email', 'cpf', 'gateway', 'status']
    });

    this.onViewInvoice = options.onViewInvoice || null;
    this.currentFilter = 'all';
  }

  /** Renderiza com Chips Rápidos de Status */
  render(containerId) {
    super.render(containerId);
    if (!this.element) return;

    // Injeta barra de Chips acima da tabela
    const controls = this.element.querySelector('.datatable-controls');
    if (controls) {
      const chipsContainer = document.createElement('div');
      chipsContainer.className = 'financial-chips-filter';
      chipsContainer.style.cssText = 'display: flex; gap: 8px; align-items: center; margin-top: 8px; flex-wrap: wrap;';
      
      const filters = [
        { key: 'all', label: 'Todas as Faturas' },
        { key: 'paid', label: '✅ Pagas / Liquidadas' },
        { key: 'pending', label: '⏳ A Receber' },
        { key: 'overdue', label: '⚠️ Inadimplentes' }
      ];

      filters.forEach(f => {
        const chip = document.createElement('button');
        chip.className = `financial-chip ${this.currentFilter === f.key ? 'active' : ''}`;
        chip.textContent = f.label;
        chip.style.cssText = `
          padding: 5px 12px;
          border-radius: 20px;
          font-size: 0.78rem;
          font-weight: 600;
          cursor: pointer;
          transition: all 0.2s ease;
          background: ${this.currentFilter === f.key ? 'rgba(6, 182, 212, 0.25)' : 'rgba(15, 23, 42, 0.6)'};
          border: 1px solid ${this.currentFilter === f.key ? '#06b6d4' : 'rgba(255, 255, 255, 0.1)'};
          color: ${this.currentFilter === f.key ? '#38bdf8' : '#94a3b8'};
          box-shadow: ${this.currentFilter === f.key ? '0 0 10px rgba(6, 182, 212, 0.4)' : 'none'};
        `;

        chip.addEventListener('click', () => {
          this.currentFilter = f.key;
          chipsContainer.querySelectorAll('.financial-chip').forEach(c => {
            c.style.background = 'rgba(15, 23, 42, 0.6)';
            c.style.borderColor = 'rgba(255, 255, 255, 0.1)';
            c.style.color = '#94a3b8';
            c.style.boxShadow = 'none';
          });
          chip.style.background = 'rgba(6, 182, 212, 0.25)';
          chip.style.borderColor = '#06b6d4';
          chip.style.color = '#38bdf8';
          chip.style.boxShadow = '0 0 10px rgba(6, 182, 212, 0.4)';

          this.applyFilterAndSort();
        });

        chipsContainer.appendChild(chip);
      });

      controls.appendChild(chipsContainer);
    }
  }

  applyFilterAndSort() {
    let result = [...this.rawData];

    // Filtro por Chip
    if (this.currentFilter === 'paid') {
      result = result.filter(r => {
        const s = (r.status || '').toUpperCase();
        return s.includes('PAGO') || s.includes('RECEIVED') || s.includes('CONFIRMED');
      });
    } else if (this.currentFilter === 'pending') {
      result = result.filter(r => {
        const s = (r.status || '').toUpperCase();
        return s.includes('PEND') || s.includes('AGUARD') || s.includes('FUTUR');
      });
    } else if (this.currentFilter === 'overdue') {
      result = result.filter(r => {
        const s = (r.status || '').toUpperCase();
        return s.includes('VENCID') || s.includes('OVERDUE') || s.includes('INADIMP');
      });
    }

    // Busca textual
    if (this.searchTerm.trim()) {
      const term = this.searchTerm.toLowerCase().trim();
      result = result.filter(row => {
        const keys = this.searchKeys || Object.keys(row);
        return keys.some(k => String(row[k] || '').toLowerCase().includes(term));
      });
    }

    // Ordenação
    if (this.sortColumn) {
      result.sort((a, b) => {
        let va = a[this.sortColumn] ?? '';
        let vb = b[this.sortColumn] ?? '';
        if (!isNaN(Number(va)) && !isNaN(Number(vb)) && va !== '' && vb !== '') {
          va = Number(va);
          vb = Number(vb);
        } else {
          va = String(va).toLowerCase();
          vb = String(vb).toLowerCase();
        }
        if (va < vb) return this.sortDirection === 'asc' ? -1 : 1;
        if (va > vb) return this.sortDirection === 'asc' ? 1 : -1;
        return 0;
      });
    }

    this.filteredData = result;
    this.currentPage = 1;
    this.renderBody();
    this.renderPagination();
  }
}
