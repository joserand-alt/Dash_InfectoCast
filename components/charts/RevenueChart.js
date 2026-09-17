/**
 * InfectoCast Component Library - RevenueChart (Dark HUD)
 */

import { BaseChart } from './BaseChart.js';

export class RevenueChart extends BaseChart {
  constructor(options = {}) {
    super({
      title: options.title || '💰 Faturamento Mensal (Asaas & Vindi)',
      subtitle: options.subtitle || 'Comparativo de receita realizada (paga) vs parcelas a receber',
      height: options.height || 280,
      ...options
    });

    this.months = options.months || [];
  }

  setData(months) {
    this.months = months || [];
    this.draw();
  }

  draw() {
    const { width, height } = this.setupCanvasDimensions();
    if (width === 0 || height === 0 || this.months.length === 0) return;

    const ctx = this.ctx;
    ctx.clearRect(0, 0, width, height);

    const padding = { top: 25, right: 20, bottom: 40, left: 65 };
    const chartW = width - padding.left - padding.right;
    const chartH = height - padding.top - padding.bottom;

    const maxVal = Math.max(10000, ...this.months.map(m => (m.recebido || 0) + (m.futuro || 0))) * 1.15;
    const barStep = chartW / this.months.length;
    const barWidth = Math.min(36, barStep * 0.65);

    // Linhas de Grade HUD
    ctx.strokeStyle = 'rgba(56, 189, 248, 0.1)';
    ctx.lineWidth = 1;
    for (let i = 0; i <= 4; i++) {
      const y = padding.top + (chartH / 4) * i;
      ctx.beginPath();
      ctx.moveTo(padding.left, y);
      ctx.lineTo(width - padding.right, y);
      ctx.stroke();

      const valLabel = Math.round((maxVal * (1 - i / 4)) / 1000);
      ctx.fillStyle = '#64748b';
      ctx.font = '10px Inter, sans-serif';
      ctx.textAlign = 'right';
      ctx.fillText(`R$ ${valLabel}k`, padding.left - 8, y + 3);
    }

    this.barsCoords = [];

    // Barras Empilhadas
    this.months.forEach((m, idx) => {
      const x = padding.left + idx * barStep + (barStep - barWidth) / 2;
      const recH = ((m.recebido || 0) / maxVal) * chartH;
      const futH = ((m.futuro || 0) / maxVal) * chartH;

      const yRec = padding.top + chartH - recH;
      ctx.fillStyle = '#00ff9d';
      ctx.beginPath();
      ctx.roundRect(x, yRec, barWidth, Math.max(2, recH), (futH > 0 ? [0, 0, 0, 0] : [4, 4, 0, 0]));
      ctx.fill();

      if (futH > 0) {
        const yFut = yRec - futH;
        ctx.fillStyle = '#00f0ff';
        ctx.beginPath();
        ctx.roundRect(x, yFut, barWidth, futH, [4, 4, 0, 0]);
        ctx.fill();
      }

      this.barsCoords.push({
        x, y: yRec - futH, width: barWidth, height: recH + futH,
        mes: m.mes, recebido: m.recebido || 0, futuro: m.futuro || 0,
        total: (m.recebido || 0) + (m.futuro || 0)
      });

      ctx.fillStyle = '#94a3b8';
      ctx.font = '11px Inter, sans-serif';
      ctx.textAlign = 'center';
      ctx.fillText(m.mes, x + barWidth / 2, height - 15);
    });

    this.setupInteractions();
  }

  setupInteractions() {
    if (this._hasInteractions) return;
    this._hasInteractions = true;

    this.canvas.addEventListener('mousemove', (e) => {
      const rect = this.canvas.getBoundingClientRect();
      const mouseX = e.clientX - rect.left;
      const hit = this.barsCoords && this.barsCoords.find(b => mouseX >= b.x - 4 && mouseX <= b.x + b.width + 4);
      if (hit) {
        this.showTooltip(hit.x + hit.width / 2, hit.y, `Mês: ${hit.mes}`, [
          { label: 'Realizado (Pago)', value: hit.recebido.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' }), color: '#00ff9d' },
          { label: 'A Receber (Futuro)', value: hit.futuro.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' }), color: '#00f0ff' },
          { label: 'Total Projetado', value: hit.total.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' }), color: '#ffffff' }
        ]);
      } else {
        this.hideTooltip();
      }
    });

    this.canvas.addEventListener('mouseleave', () => this.hideTooltip());
  }

  render() {
    const legendHtml = `
      <div class="chart-legend" style="margin-top: 14px; justify-content: center;">
        <div class="chart-legend-item">
          <span class="chart-legend-color" style="background: #00ff9d; box-shadow: 0 0 8px #00ff9d;"></span>
          <span>Realizado / Pago</span>
        </div>
        <div class="chart-legend-item">
          <span class="chart-legend-color" style="background: #00f0ff; box-shadow: 0 0 8px #00f0ff;"></span>
          <span>A Receber / Futuro</span>
        </div>
      </div>
    `;
    return this.createCardWrapper(legendHtml);
  }
}
