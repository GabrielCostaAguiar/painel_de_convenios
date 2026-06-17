/* =============================================================
   Painel de Convênios DCGCE — shell interativo
   Recolher sidebar · popover "Dados de carga" · sub-abas
   ============================================================= */

(function () {
  'use strict';

  // ── Toggle do menu lateral ──────────────────────────────────
  var toggle = document.getElementById('toggle');
  var app    = document.getElementById('app');
  if (toggle && app) {
    toggle.addEventListener('click', function () {
      app.classList.toggle('collapsed');
    });
  }

  // ── Popover "Dados de carga" ────────────────────────────────
  var loadBtn = document.getElementById('loadBtn');
  var loadPop = document.getElementById('loadPop');
  if (loadBtn && loadPop) {
    loadBtn.addEventListener('click', function (e) {
      e.stopPropagation();
      loadPop.classList.toggle('open');
      if (exportPop) exportPop.classList.remove('open');
    });
  }

  // ── Popover "Exportar" (presente apenas em páginas com tabela) ─
  var exportBtn = document.getElementById('exportBtn');
  var exportPop = document.getElementById('exportPop');
  if (exportBtn && exportPop) {
    exportBtn.addEventListener('click', function (e) {
      e.stopPropagation();
      exportPop.classList.toggle('open');
      if (loadPop) loadPop.classList.remove('open');
    });
  }

  // ── Fecha todos os popovers ao clicar fora ──────────────────
  document.addEventListener('click', function () {
    if (loadPop)   loadPop.classList.remove('open');
    if (exportPop) exportPop.classList.remove('open');
  });

  // ── Sub-abas (presentes apenas em páginas com .subtabs) ────
  document.querySelectorAll('.subtabs').forEach(function (group) {
    group.querySelectorAll('.subtab').forEach(function (tab) {
      tab.addEventListener('click', function () {
        group.querySelectorAll('.subtab').forEach(function (t) {
          t.classList.remove('active');
        });
        tab.classList.add('active');
      });
    });
  });

})();
