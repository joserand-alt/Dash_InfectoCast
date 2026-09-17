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

    // Fechar ao clicar no backdrop (fora da caixa de diálogo)
    overlay.addEventListener('click', (e) => {
      if (e.target === overlay) this.close();
    });

    document.body.appendChild(overlay);

    this.overlay = overlay;
    this.dialog = overlay.querySelector('.modal-dialog');
    this.bodyEl = overlay.querySelector('.modal-body');
  }

  /** Renderiza ou move o modal para um container (compatibilidade) */
  render(target) {
    if (target) {
      const container = typeof target === 'string' ? document.getElementById(target.replace('#', '')) : target;
      if (container && this.overlay && this.overlay.parentElement !== container) {
        container.appendChild(this.overlay);
      }
    }
    return this.overlay;
  }

  /** Abre o modal */
  open() {
    if (!this.overlay) this.create();
    
    this.overlay.classList.add('active');
    document.body.classList.add('modal-open');
    this.isOpen = true;

    document.addEventListener('keydown', this._onKeyDown);

    if (typeof this.onOpen === 'function') {
      this.onOpen(this);
    }
  }

  /** Fecha o modal */
  close() {
    if (!this.overlay || !this.isOpen) return;

    this.overlay.classList.remove('active');
    document.body.classList.remove('modal-open');
    this.isOpen = false;

    document.removeEventListener('keydown', this._onKeyDown);

    if (typeof this.onClose === 'function') {
      this.onClose(this);
    }
  }

  /** Trata tecla ESC */
  _onKeyDown(e) {
    if (e.key === 'Escape' || e.key === 'Esc') {
      this.close();
    }
  }

  /** Destrói o modal do DOM */
  destroy() {
    this.close();
    if (this.overlay && this.overlay.parentNode) {
      this.overlay.parentNode.removeChild(this.overlay);
    }
    this.overlay = null;
    this.dialog = null;
    this.bodyEl = null;
  }
}
