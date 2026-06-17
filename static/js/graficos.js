/**
 * graficos.js — Inicialização dos gráficos Chart.js do painel.
 *
 * Os dados chegam como JSON embutido no HTML via {{ data|json_script:"id" }}.
 * Lemos com JSON.parse(document.getElementById("id").textContent).
 * Isso é seguro: json_script escapa qualquer HTML no valor.
 */

(function () {
  "use strict";

  // ── Paleta do tema escuro ──────────────────────────────────────────────────
  const CORES_DOUGHNUT = [
    "#7a1722", "#2e7d52", "#a86412", "#a1303a",
    "#5c4a8a", "#1a8a8a", "#7a4a1a", "#4a6a8a",
  ];

  const GRID_COLOR  = "rgba(230, 226, 220, 0.9)";
  const TICK_COLOR  = "#9a938d";
  const TEXT_COLOR  = "#6f6862";
  const BAR_COLOR   = "#7a1722";
  const LINE_COLOR  = "#2e7d52";

  Chart.defaults.color = TEXT_COLOR;
  Chart.defaults.font.family = "'Segoe UI', system-ui, sans-serif";
  Chart.defaults.font.size   = 12;

  // ── Helpers ────────────────────────────────────────────────────────────────

  function lerDados(elementId) {
    const el = document.getElementById(elementId);
    if (!el) return null;
    try { return JSON.parse(el.textContent); } catch { return null; }
  }

  function formatarBRL(valor) {
    return new Intl.NumberFormat("pt-BR", {
      style: "currency", currency: "BRL", maximumFractionDigits: 0,
    }).format(valor);
  }

  function formatarMilhoes(valor) {
    if (Math.abs(valor) >= 1e9) return "R$ " + (valor / 1e9).toFixed(1) + " bi";
    if (Math.abs(valor) >= 1e6) return "R$ " + (valor / 1e6).toFixed(1) + " mi";
    return formatarBRL(valor);
  }

  // ── Gráfico de barras: convênios por ano ───────────────────────────────────

  function iniciarGraficoAnos() {
    const dados = lerDados("data-por-ano");
    const canvas = document.getElementById("grafico-por-ano");
    if (!dados || !canvas) return;

    const labels = dados.map(d => String(d.ano));
    const qtd    = dados.map(d => d.quantidade);
    const vals   = dados.map(d => d.valor_total);

    new Chart(canvas, {
      type: "bar",
      data: {
        labels,
        datasets: [
          {
            label: "Quantidade",
            data: qtd,
            backgroundColor: BAR_COLOR,
            borderRadius: 4,
            yAxisID: "yQtd",
            order: 2,
          },
          {
            label: "Valor Total",
            data: vals,
            type: "line",
            borderColor: LINE_COLOR,
            backgroundColor: "rgba(42,157,92,0.12)",
            borderWidth: 2,
            pointRadius: 4,
            fill: true,
            tension: 0.3,
            yAxisID: "yVal",
            order: 1,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { position: "top", labels: { boxWidth: 12, padding: 16 } },
          tooltip: {
            callbacks: {
              label(ctx) {
                if (ctx.datasetIndex === 1) {
                  return " " + formatarBRL(ctx.raw);
                }
                return " " + ctx.raw + " convênios";
              },
            },
          },
        },
        scales: {
          x: {
            grid: { color: GRID_COLOR },
            ticks: { color: TICK_COLOR },
          },
          yQtd: {
            position: "left",
            grid: { color: GRID_COLOR },
            ticks: { color: TICK_COLOR, precision: 0 },
            title: { display: true, text: "Qtd.", color: TICK_COLOR },
          },
          yVal: {
            position: "right",
            grid: { drawOnChartArea: false },
            ticks: {
              color: TICK_COLOR,
              callback: (v) => formatarMilhoes(v),
            },
            title: { display: true, text: "Valor", color: TICK_COLOR },
          },
        },
      },
    });
  }

  // ── Gráfico de rosca: convênios por situação ───────────────────────────────

  function iniciarGraficoSituacao() {
    const dados = lerDados("data-por-situacao");
    const canvas = document.getElementById("grafico-por-situacao");
    if (!dados || !canvas) return;

    const labels = dados.map(d => d.situacao);
    const vals   = dados.map(d => d.valor_total);

    new Chart(canvas, {
      type: "doughnut",
      data: {
        labels,
        datasets: [{
          data: vals,
          backgroundColor: CORES_DOUGHNUT.slice(0, labels.length),
          borderColor: "#ffffff",
          borderWidth: 3,
          hoverOffset: 8,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        cutout: "60%",
        plugins: {
          legend: {
            position: "bottom",
            labels: {
              boxWidth: 12,
              padding: 14,
              font: { size: 11 },
            },
          },
          tooltip: {
            callbacks: {
              label(ctx) {
                const pct = ((ctx.raw / vals.reduce((a, b) => a + b, 0)) * 100).toFixed(1);
                return ` ${formatarBRL(ctx.raw)}  (${pct}%)`;
              },
            },
          },
        },
      },
    });
  }

  // ── Bootstrap ──────────────────────────────────────────────────────────────

  document.addEventListener("DOMContentLoaded", function () {
    iniciarGraficoAnos();
    iniciarGraficoSituacao();
  });
})();
