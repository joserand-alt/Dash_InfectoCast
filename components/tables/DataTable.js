/**
 * InfectoCast Component Library - DataTable
 * Componente base universal para tabelas dinâmicas com busca, ordenação, paginação e sticky headers.
 */

export class DataTable {
  /**
   * @param {Object} options
   * @param {string} [options.id] - ID do container
   * @param {Array<Object>} options.columns - Definição das colunas [{ key, label, sortable, render, width, align }]
   * @param {Array<Object>} options.data - Lista de objetos de dados
   * @param {number} [options.pageSize=15] - Quantidade de itens por página
   * @param {boolean} [options.searchable=true] - Se exibe barra de pesquisa
   * @param {string} [options.searchPlaceholder='Buscar...'] - Placeholder da busca
   * @param {Array<string>} [options.searchKeys] - Campos do objeto a pesquisar (default: todas as chaves)
   * @param {Function} [options.onRowClick] - Callback ao clicar na linha
   */
  constructor(options = {}) {
    this.id = options.id || `datatable-${Math.random().toString(36).substr(2, 9)}`;
    this.columns = options.columns || [];
    this.rawData = options.data || [];
    this.filteredData = [...this.rawData];
    this.pageSize = options.pageSize || 15;
    this.currentPage = 1;
    this.searchable = options.searchable !== false;
    this.searchPlaceholder = options.searchPlaceholder || 'Buscar na tabela...';
    this.searchKeys = options.searchKeys || null;
    this.sortColumn = null;
    this.sortDirection = 'asc'; // 'asc' | 'desc'
    this.searchTerm = '';
    this.onRowClick = options.onRowClick || null;

    this.element = null;
    this._searchDebounceTimer = null;
  }

  /** Atualiza os dados da tabela */
  setData(newData) {
    this.rawData = newData || [];
    this.applyFilterAndSort();
  }

  /** Aplica busca e ordenação sobre os dados */
  applyFilterAndSort() {
    let result = [...this.rawData];

    // 1. Busca textual
    if (this.searchTerm.trim()) {
      const term = this.searchTerm.toLowerCase().trim();
      result = result.filter(row => {
        if (this.searchKeys && this.searchKeys.length > 0) {
          return this.searchKeys.some(k => String(row[k] || '').toLowerCase().includes(term));
        }
        return Object.values(row).some(val => String(val || '').toLowerCase().includes(term));
      });
    }

    // 2. Ordenação
    if (this.sortColumn) {
      const col = this.columns.find(c => c.key === this.sortColumn);
      const isCustomSort = col && typeof col.sortFn === 'function';
      
      result.sort((a, b) => {
        if (isCustomSort) {
          const res = col.sortFn(a, b);
          return this.sortDirection === 'asc' ? res : -res;
        }

        let valA = a[this.sortColumn];
        let valB = b[this.sortColumn];

        if (valA === valB) return 0;
        if (valA === null || valA === undefined) return 1;
        if (valB === null || valB === undefined) return -1;

        if (typeof valA === 'number' && typeof valB === 'number') {
          return this.sortDirection === 'asc' ? valA - valB : valB - valA;
        }

        const strA = String(valA).toLowerCase();
        const strB = String(valB).toLowerCase();
        return this.sortDirection === 'asc' ? strA.localeCompare(strB, 'pt-BR') : strB.localeCompare(strA, 'pt-BR');
      });
    }

    this.filteredData = result;
    this.currentPage = 1;
    this.renderBody();
    this.renderPagination();
  }

  /** Define a ordenação por coluna */
  handleSort(columnKey) {
    if (this.sortColumn === columnKey) {
      this.sortDirection = this.sortDirection === 'asc' ? 'desc' : 'asc';
    } else {
      this.sortColumn = columnKey;
      this.sortDirection = 'asc';
    }
    this.updateHeaderSortClasses();
    this.applyFilterAndSort();
  }

  /** Atualiza as classes CSS no cabeçalho */
  updateHeaderSortClasses() {
    if (!this.element) return;
    const ths = this.element.querySelectorAll('thead th');
    ths.forEach(th => {
      const colKey = th.dataset.key;
      th.classList.remove('sorted-asc', 'sorted-desc');
      const indicator = th.querySelector('.datatable-sort-indicator');
      if (indicator) indicator.textContent = '⇅';

      if (colKey === this.sortColumn) {
        th.classList.add(this.sortDirection === 'asc' ? 'sorted-asc' : 'sorted-desc');
        if (indicator) indicator.textContent = this.sortDirection === 'asc' ? '▲' : '▼';
      }
    });
  }

  /** Renderiza o corpo da tabela */
  renderBody() {
    if (!this.element) return;
    const tbody = this.element.querySelector('tbody');
    if (!tbody) return;

    tbody.innerHTML = '';

    if (this.filteredData.length === 0) {
      tbody.innerHTML = `
        <tr>
          <td colspan="${this.columns.length}" class="datatable-empty">
            Nenhum registro encontrado para o filtro aplicado.
          </td>
        </tr>
      `;
      return;
    }

    const startIdx = (this.currentPage - 1) * this.pageSize;
    const endIdx = startIdx + this.pageSize;
    const pageRows = this.filteredData.slice(startIdx, endIdx);

    pageRows.forEach(row => {
      const tr = document.createElement('tr');
      if (this.onRowClick) {
        tr.style.cursor = 'pointer';
        tr.addEventListener('click', () => this.onRowClick(row));
      }

      this.columns.forEach(col => {
        const td = document.createElement('td');
        if (col.align) td.style.textAlign = col.align;
        if (col.width) td.style.width = col.width;

        const val = row[col.key];
        if (typeof col.render === 'function') {
          const rendered = col.render(val, row);
          if (rendered instanceof HTMLElement) {
            td.appendChild(rendered);
          } else {
            td.innerHTML = rendered !== undefined && rendered !== null ? rendered : '—';
          }
        } else {
          td.textContent = val !== undefined && val !== null ? String(val) : '—';
        }

        tr.appendChild(td);
      });

      tbody.appendChild(tr);
    });
  }

  /** Renderiza os controles de paginação */
  renderPagination() {
    if (!this.element) return;
    const paginationEl = this.element.querySelector('.datatable-pagination');
    if (!paginationEl) return;

    const total = this.filteredData.length;
    const totalPages = Math.ceil(total / this.pageSize) || 1;
    const start = total === 0 ? 0 : (this.currentPage - 1) * this.pageSize + 1;
    const end = Math.min(this.currentPage * this.pageSize, total);

    paginationEl.innerHTML = `
      <div class="datatable-page-info">
        Exibindo <strong>${start}</strong> a <strong>${end}</strong> de <strong>${total.toLocaleString('pt-BR')}</strong> registros
      </div>
      <div class="datatable-page-controls">
        <select class="datatable-page-size">
          <option value="10" ${this.pageSize === 10 ? 'selected' : ''}>10 / pág</option>
          <option value="15" ${this.pageSize === 15 ? 'selected' : ''}>15 / pág</option>
          <option value="25" ${this.pageSize === 25 ? 'selected' : ''}>25 / pág</option>
          <option value="50" ${this.pageSize === 50 ? 'selected' : ''}>50 / pág</option>
          <option value="100" ${this.pageSize === 100 ? 'selected' : ''}>100 / pág</option>
        </select>
        <button class="datatable-page-btn" data-action="prev" ${this.currentPage === 1 ? 'disabled' : ''}>&lt;</button>
        <span style="font-size: 0.85rem; font-weight: 600; padding: 0 4px;">${this.currentPage} / ${totalPages}</span>
        <button class="datatable-page-btn" data-action="next" ${this.currentPage >= totalPages ? 'disabled' : ''}>&gt;</button>
      </div>
    `;

    // Eventos de paginação
    const prevBtn = paginationEl.querySelector('[data-action="prev"]');
    const nextBtn = paginationEl.querySelector('[data-action="next"]');
    const sizeSelect = paginationEl.querySelector('.datatable-page-size');

    if (prevBtn) {
      prevBtn.addEventListener('click', () => {
        if (this.currentPage > 1) {
          this.currentPage--;
          this.renderBody();
          this.renderPagination();
        }
      });
    }

    if (nextBtn) {
      nextBtn.addEventListener('click', () => {
        if (this.currentPage < totalPages) {
          this.currentPage++;
          this.renderBody();
          this.renderPagination();
        }
      });
    }

    if (sizeSelect) {
      sizeSelect.addEventListener('change', (e) => {
        this.pageSize = parseInt(e.target.value, 10);
        this.currentPage = 1;
        this.renderBody();
        this.renderPagination();
      });
    }
  }

  /** Renderiza o componente completo */
  render() {
    const wrapper = document.createElement('div');
    wrapper.id = this.id;
    wrapper.className = 'datatable-wrapper';

    // 1. Toolbar Superior
    if (this.searchable) {
      const toolbar = document.createElement('div');
      toolbar.className = 'datatable-toolbar';
      toolbar.innerHTML = `
        <div class="datatable-search-box">
          <svg class="datatable-search-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="11" cy="11" r="8"></circle>
            <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
          </svg>
          <input type="text" class="datatable-search-input" placeholder="${this.searchPlaceholder}">
        </div>
        <div class="datatable-actions"></div>
      `;

      const searchInput = toolbar.querySelector('.datatable-search-input');
      searchInput.addEventListener('input', (e) => {
        clearTimeout(this._searchDebounceTimer);
        this._searchDebounceTimer = setTimeout(() => {
          this.searchTerm = e.target.value;
          this.applyFilterAndSort();
        }, 200);
      });

      wrapper.appendChild(toolbar);
    }

    // 2. Tabela com Scroll e Sticky Header
    const scrollArea = document.createElement('div');
    scrollArea.className = 'datatable-scroll-area';

    const table = document.createElement('table');
    table.className = 'datatable-table';

    // Header (thead)
    const thead = document.createElement('thead');
    const headerRow = document.createElement('tr');

    this.columns.forEach(col => {
      const th = document.createElement('th');
      th.dataset.key = col.key;
      if (col.align) th.style.textAlign = col.align;
      if (col.width) th.style.width = col.width;

      if (col.sortable !== false) {
        th.className = 'sortable';
        th.innerHTML = `${col.label} <span class="datatable-sort-indicator">⇅</span>`;
        th.addEventListener('click', () => this.handleSort(col.key));
      } else {
        th.textContent = col.label;
      }

      headerRow.appendChild(th);
    });

    thead.appendChild(headerRow);
    table.appendChild(thead);

    // Body (tbody)
    const tbody = document.createElement('tbody');
    table.appendChild(tbody);

    scrollArea.appendChild(table);
    wrapper.appendChild(scrollArea);

    // 3. Paginação Inferior
    const pagination = document.createElement('div');
    pagination.className = 'datatable-pagination';
    wrapper.appendChild(pagination);

    this.element = wrapper;
    this.renderBody();
    this.renderPagination();

    return wrapper;
  }

  /** Monta no elemento DOM alvo */
  mount(target) {
    const container = typeof target === 'string' ? document.querySelector(target) : target;
    if (container) {
      container.appendChild(this.render());
    }
    return this;
  }
}
