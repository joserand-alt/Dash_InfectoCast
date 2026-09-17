/**
 * InfectoCast Component Library - HourlyActivityChart (Dark HUD)
 */

import { BaseChart } from './BaseChart.js';

export class HourlyActivityChart extends BaseChart {
  constructor(options = {}) {
    super({
      title: options.title || '⚡ Distribuição de Acessos por Horário (24h)',
      subtitle: options.subtitle || 'Identificação dos turnos com maior pico de estudo dos alunos',
      height: options.height || 260,
      ...options
    });

    this.hourlyData = options.hourlyData || new Array(24).fill(0);
  }

  setData(data24) {
    this.hourlyData = data24 || new Array(24).fill(0);
    this.draw();
  }

  getShiftColor(hour) {
    if (hour >= 0 && hour < 6) return { bg: '#818cf8', text: 'Madrugada', glow: 'rgba(129, 140, 248, 0.4)' };
    if (hour >= 6 && hour < 12) return { bg: '#00f0ff', text: 'Manhã', glow: 'rgba(0, 240, 255, 0.4)' };
    if (hour >= 12 && hour < 18) return { bg: '#00ff9d', text: 'Tarde', glow: 'rgba(0, 255, 157, 0.4)' };
    return { bg: '#fbbf24', text: 'Noite', glow: 'rgba(251, 191, 36, 0.4)' };
  }

  draw() {
    const { width, height } = this.setupCanvasDimensions();
    if (width === 0 || height === 0) return;

    const ctx = this.ctx;
    ctx.clearRect(0, 0, width, height);

    const padding = { top: 20, right: 15, bottom: 35, left: 35 };
    const chartW = width - padding.left - padding.right;
    const chartH = height - padding.top - padding.bottom;

    const maxVal = Math.max(10, ...this.hourlyData);
    const barWidth = (chartW / 24) * 0.72;
    const barStep = chartW / 24;

    // Linhas de Grade de Fundo HUD
    ctx.strokeStyle = 'rgba(56, 189, 248, 0.1)';
    ctx.lineWidth = 1;
    for (let i = 0; i <= 4; i++) {
      const y = padding.top + (chartH / 4) * i;
      ctx.beginPath();
      ctx.moveTo(padding.left, y);
      ctx.lineTo(width - padding.right, y);
      ctx.stroke();

      const valLabel = Math.round(maxVal * (1 - i / 4));
      ctx.fillStyle = '#64748b';
      ctx.font = '10px Inter, sans-serif';
      ctx.textAlign = 'right';
      ctx.fillText(String(valLabel), padding.left - 6, y + 3);
    }

    this.barsCoords = [];

    // Desenhar Barras Neon
    this.hourlyData.forEach((val, hour) => {
      const barH = (val / maxVal) * chartH;
      const x = padding.left + hour * barStep + (barStep - barWidth) / 2;
      const y = padding.top + (chartH - barH);

      const shift = this.getShiftColor(hour);

      ctx.fillStyle = shift.bg;
      ctx.beginPath();
      ctx.roundRect(x, y, barWidth, Math.max(2, barH), [4, 4, 0, 0]);
      ctx.fill();

      this.barsCoords.push({ x, y, width: barWidth, height: barH, hour, val, shift: shift.text });

      if (hour % 3 === 0 || hour === 23) {
        ctx.fillStyle = '#94a3b8';
        ctx.font = '10px Inter, sans-serif';
        ctx.textAlign = 'center';
        ctx.fillText(`${String(hour).padStart(2, '0')}h`, x + barWidth / 2, height - 12);
      }
    });

    this.setupInteractions();
  }

  setupInteractions() {
    if (this._hasInteractions) return;
    this._hasInteractions = true;

    this.canvas.addEventListener('mousemove', (e) => {
      const rect = this.canvas.getBoundingClientRect();
      const mouseX = e.clientX - rect.left;
      const hit = this.barsCoords && this.barsCoords.find(b => mouseX >= b.x - 2 && mouseX <= b.x + b.width + 2);
      if (hit) {
        this.showTooltip(hit.x + hit.width / 2, hit.y, `Horário: ${String(hit.hour).padStart(2, '0')}:00 às ${String(hit.hour).padStart(2, '0')}:59`, [
          { label: 'Acessos / Aulas', value: hit.val.toLocaleString('pt-BR'), color: '#00f0ff' },
          { label: 'Turno', value: hit.shift, color: '#00ff9d' }
        ]);
      } else {
        this.hideTooltip();
      }
    });

    this.canvas.addEventListener('mouseleave', () => this.hideTooltip());
  }

  render() {
    return this.createCardWrapper();
  }
}
