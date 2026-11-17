// MechHub — scripts compartilhados
(function () {
  // Gráficos: qualquer <script type="application/json" class="mh-chart" data-target="id">
  function drawCharts() {
    if (!window.Plotly) return;
    document.querySelectorAll("script.mh-chart").forEach(function (node) {
      var target = document.getElementById(node.dataset.target);
      if (!target) return;
      try {
        var fig = JSON.parse(node.textContent);
        Plotly.newPlot(target, fig.data, fig.layout, { responsive: true, displaylogo: false,
          modeBarButtonsToRemove: ["lasso2d", "select2d"] });
      } catch (e) { target.textContent = "Não foi possível desenhar o gráfico."; }
    });
  }

  // Menu lateral no celular
  function sidebar() {
    var btn = document.querySelector(".mh-sidebar-toggle");
    var bar = document.querySelector(".mh-sidebar");
    if (btn && bar) btn.addEventListener("click", function () { bar.classList.toggle("open"); });
  }

  // Confirmação antes de excluir
  function confirms() {
    document.querySelectorAll("form[data-confirm]").forEach(function (f) {
      f.addEventListener("submit", function (e) { if (!confirm(f.dataset.confirm)) e.preventDefault(); });
    });
  }

  document.addEventListener("DOMContentLoaded", function () { drawCharts(); sidebar(); confirms(); });
})();
