/**
 * InfectoCast Component Library - RetentionCurveChart (Dark HUD)
 */

import { BaseChart } from './BaseChart.js';

export class RetentionCurveChart extends BaseChart {
  constructor(options = {}) {
    super({
      title: options.title || '🛡️ Curva de Retenção & Sobrevivência da Turma',
      subtitle: options.subtitle || 'Evolução percentual de alunos mantendo ritmo de aulas semana a semana',
      height: options.height || 260,
      ...options
    });

    this.survivalData = options.survivalData || [];
  }

  setData(data) {
    this.survivalData = data || [];
    this.draw();
  }

  draw() {
    const { width, height } = this.setupCanvasDimensions();
    if (width === 0 || height === 0 || this.survivalData.length === 0) return;

    const ctx = this.ctx;
    ctx.clearRect(0, 0, width, height);

    const padding = { top: 25, right: 25, bottom: 35, left: 45 };
    const chartW = width - padding.left - padding.right;
    const chartH = height - padding.top - padding.bottom;

    // Grade Y
    ctx.strokeStyle = 'rgba(56, 189, 248, 0.1)';
    ctx.lineWidth = 1;
    for (let i = 0; i <= 4; i++) {
      const y = padding.top + (chartH / 4) * i;
      ctx.beginPath();
      ctx.moveTo(padding.left, y);
      ctx.lineTo(width - padding.right, y);
      ctx.stroke();

      const pct = 100 - i * 25;
      ctx.fillStyle = '#64748b';
      ctx.font = '10px Inter, sans-serif';
      ctx.textAlign = 'right';
      ctx.fillText(`${pct}%`, padding.left - 6, y + 3);
    }

    const stepX = chartW / (this.survivalData.length - 1 || 1);
    const points = this.survivalData.map((d, i) => {
      const x = padding.left + i * stepX;
      const y = padding.top + chartH * (1 - (d.retencao || 0) / 100);
      return { x, y, semana: d.semana, retencao: d.retencao };
    });

    this.pointsCoords = points;

    // Área Gradiente Neon
    const grad = ctx.createLinearGradient(0, padding.top, 0, padding.top + chartH);
    grad.addColorStop(0, 'rgba(0, 240, 255, 0.35)');
    grad.addColorStop(1, 'rgba(0, 240, 255, 0.00)');

    ctx.fillStyle = grad;
    ctx.beginPath();
    ctx.moveTo(points[0].x, padding.top + chartH);
    points.forEach(p => ctx.lineTo(p.x, p.y));
    ctx.lineTo(points[points.length - 1].x, padding.top + chartH);
    ctx.closePath();
    ctx.fill();

    // Linha Neon
    ctx.strokeStyle = '#00f0ff';
    ctx.lineWidth = 3;
    ctx.shadowColor = 'rgba(0, 240, 255, 0.6)';
    ctx.shadowBlur = 10;
    ctx.beginPath();
    points.forEach((p, i) => {
      if (i === 0) ctx.moveTo(p.x, p.y);
      else ctx.lineTo(p.x, p.y);
    });
    ctx.stroke();
    ctx.shadowBlur = 0;

    // Nós com Brilho
    points.forEach((p) => {
      ctx.fillStyle = '#030712';
      ctx.strokeStyle = '#00f0ff';
      ctx.lineWidth = 2.5;
      ctx.beginPath();
      ctx.arc(p.x, p.y, 4.5, 0, Math.PI * 2);
      ctx.fill();
      ctx.stroke();

      ctx.fillStyle = '#94a3b8';
      ctx.font = '10px Inter, sans-serif';
      ctx.textAlign = 'center';
      ctx.fillText(p.semana, p.x, height - 12);
    });

    this.setupInteractions();
  }

  setupInteractions() {
    if (this._hasInteractions) return;
    this._hasInteractions = true;

    this.canvas.addEventListener('mousemove', (e) => {
      const rect = this.canvas.getBoundingClientRect();
      const mouseX = e.clientX - rect.left;
      const hit = this.pointsCoords && this.pointsCoords.find(p => Math.abs(mouseX - p.x) < 16);
      if (hit) {
        this.showTooltip(hit.x, hit.y, `${hit.semana}`, [
          { label: 'Taxa de Retenção', value: `${hit.retencao.toFixed(1)}%`, color: '#00f0ff' },
          { label: 'Evasão Acumulada', value: `${(100 - hit.retencao).toFixed(1)}%`, color: '#ff3366' }
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
