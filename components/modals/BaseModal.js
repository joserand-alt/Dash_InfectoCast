/**
 * InfectoCast Component Library - BaseModal
 * Motor genérico de modais com overlay, trava de scroll, tecla ESC e ciclo de vida.
 */

export class BaseModal {
  /**
   * @param {Object} options
   * @param {string} [options.id] - ID único
   * @param {string} [options.title='Modal'] - Título do cabeçalho
   * @param {string} [options.size='default'] - 'default' | 'large' | 'small'
   * @param {Function} [options.onOpen] - Callback ao abrir
   * @param {Function} [options.onClose] - Callback ao fechar
   */
  constructor(options = {}) {
    this.id = options.id || `modal-${Math.random().toString(36).substr(2, 9)}`;
    this.title = options.title || 'Modal';
    this.size = options.size || 'default';
    this.onOpen = options.onOpen || null;
    this.onClose = options.onClose || null;
    this.isOpen = false;

    this.overlay = null;
    this.dialog = null;
    this.bodyEl = null;

    this._onKeyDown = this._onKeyDown.bind(this);
    this.create();
  }

  /** Cria a estrutura do modal e anexa ao body */
  create() {
    // Remove instância antiga se existir
    const old = document.getElementById(this.id);
    if (old && old.parentNode) old.parentNode.removeChild(old);

    const overlay = document.createElement('div');
    overlay.id = this.id;
    overlay.className = 'modal-overlay';

    let sizeClass = '';
    if (this.size === 'large') sizeClass = 'modal-dialog-large';
    if (this.size === 'small') sizeClass = 'modal-dialog-small';

    overlay.innerHTML = `
      <div class="modal-dialog ${sizeClass}">
        <div class="modal-header">
          <div class="modal-title-wrap">
            <h3 class="modal-title">${this.title}</h3>
          </div>
          <button class="modal-close-btn" title="Fechar (ESC)">&times;</button>
        </div>
        <div class="modal-body"></div>
      </div>
    `;

    // Fechar ao clicar no X
    overlay.querySelector('.modal-close-btn').addEventListener('click', () => this.close());

    // Fechar ao clicar no backdrop (fora do diálogo)
    overlay.addEventListener('click', (e) => {
      if (e.target === overlay) this.close();
    });

    document.body.appendChild(overlay);

    this.overlay = overlay;
    this.dialog = overlay.querySelector('.modal-dialog');
    this.bodyEl = overlay.querySelector('.modal-body');
  }

  /** Define o título do cabeçalho */
  setTitle(title) {
    this.title = title;
    const titleEl = this.overlay.querySelector('.modal-title');
    if (titleEl) titleEl.textContent = title;
  }

  /** Define o conteúdo interno do modal (HTML ou Elemento) */
  setContent(content) {
    if (!this.bodyEl) return;
    if (content instanceof HTMLElement) {
      this.bodyEl.innerHTML = '';
      this.bodyEl.appendChild(content);
    } else {
      this.bodyEl.innerHTML = String(content || '');
    }
  }

  /** Abre o modal */
  open(content = null) {
    if (content !== null) this.setContent(content);

    this.isOpen = true;
    this.overlay.classList.add('open');
    document.body.classList.add('modal-open');

    document.addEventListener('keydown', this._onKeyDown);

    if (typeof this.onOpen === 'function') this.onOpen(this);
    return this;
  }

  /** Fecha o modal */
  close() {
    if (!this.isOpen) return;
    this.isOpen = false;
    this.overlay.classList.remove('open');
    document.body.classList.remove('modal-open');

    document.removeEventListener('keydown', this._onKeyDown);

    if (typeof this.onClose === 'function') this.onClose(this);
    return this;
  }

  _onKeyDown(e) {
    if (e.key === 'Escape') this.close();
  }

  /** Destrói o elemento do DOM */
  destroy() {
    this.close();
    if (this.overlay && this.overlay.parentNode) {
      this.overlay.parentNode.removeChild(this.overlay);
    }
  }
}
