/* Pengaturan bersama grafik Chart.js dan fungsi bantu tampilan. */
(function () {
  "use strict";
  var SP = (window.SP = window.SP || {});

  // Palet kategori (urutan tetap - warna mengikuti domain, bukan peringkat)
  SP.warnaDomain = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"];
  SP.warnaStatus = { "sesuai": "#0ca30c", "perlu perhatian": "#fab219", "terlambat": "#ec835a", "belum terlihat": "#d03b3b" };
  SP.naik = "#2a78d6";
  SP.turun = "#e34948";
  SP.ink = "#1f2937";
  SP.muted = "#6b7280";
  SP.grid = "#e9ecf1";
  SP.axis = "#cfd6e0";
  SP.surface = "#ffffff";

  SP.angka = function (v) {
    if (v === null || v === undefined || isNaN(v)) return "-";
    return (Math.round(v * 10) / 10).toLocaleString("id-ID");
  };
  SP.persen = function (v) { return v === null || v === undefined ? "-" : SP.angka(v) + "%"; };
  SP.poin = function (v) {
    if (v === null || v === undefined) return "-";
    return (v > 0 ? "+" : v < 0 ? "−" : "") + SP.angka(Math.abs(v)) + " poin";
  };
  SP.data = function (id) {
    var el = document.getElementById(id);
    return el ? JSON.parse(el.textContent) : null;
  };

  if (window.Chart) {
    var fam = getComputedStyle(document.body).fontFamily;
    Chart.defaults.font.family = fam;
    Chart.defaults.font.size = 12;
    Chart.defaults.color = SP.muted;
    Chart.defaults.maintainAspectRatio = false;
    Chart.defaults.plugins.legend.display = false; // legenda dibuat di HTML
    var tt = Chart.defaults.plugins.tooltip;
    tt.backgroundColor = "#111827";
    tt.padding = 10;
    tt.cornerRadius = 8;
    tt.boxPadding = 4;
    tt.titleFont = { weight: "700" };
    Chart.defaults.animation.duration = 450;
  }

  SP.skalaPersen = function (opsi) {
    opsi = opsi || {};
    return {
      min: opsi.min !== undefined ? opsi.min : 0,
      max: opsi.max !== undefined ? opsi.max : 100,
      ticks: { stepSize: opsi.step || 20, callback: function (v) { return v + (opsi.satuan || "%"); } },
      grid: { color: SP.grid },
      border: { display: false },
    };
  };
  SP.skalaKategori = function () {
    return { grid: { display: false }, border: { color: SP.axis }, ticks: { color: SP.ink, font: { weight: "600" } } };
  };

  // Label nilai di ujung batang (dipakai selektif pada grafik satu seri)
  SP.labelUjung = {
    id: "labelUjung",
    afterDatasetsDraw: function (chart, args, opts) {
      if (!opts || !opts.aktif) return;
      var ctx = chart.ctx;
      var horizontal = chart.options.indexAxis === "y";
      chart.data.datasets.forEach(function (ds, i) {
        var meta = chart.getDatasetMeta(i);
        if (meta.hidden || (opts.hanya !== undefined && opts.hanya !== i)) return;
        meta.data.forEach(function (el, j) {
          var v = ds.data[j];
          if (v === null || v === undefined) return;
          ctx.save();
          ctx.fillStyle = SP.ink;
          ctx.font = "700 11px " + Chart.defaults.font.family;
          var teks = opts.format ? opts.format(v) : SP.persen(v);
          if (horizontal) {
            ctx.textBaseline = "middle";
            if (v < 0) { ctx.textAlign = "right"; ctx.fillText(teks, el.x - 6, el.y); }
            else { ctx.textAlign = "left"; ctx.fillText(teks, el.x + 6, el.y); }
          } else {
            ctx.textAlign = "center";
            ctx.textBaseline = "bottom";
            ctx.fillText(teks, el.x, el.y - 5);
          }
          ctx.restore();
        });
      });
    },
  };

  // Garis nol untuk grafik selisih
  SP.garisNol = {
    id: "garisNol",
    beforeDatasetsDraw: function (chart) {
      var x = chart.scales.x;
      if (!x || x.min > 0 || x.max < 0) return;
      var px = x.getPixelForValue(0);
      var ctx = chart.ctx;
      ctx.save();
      ctx.strokeStyle = "#9aa3af";
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(px, chart.chartArea.top);
      ctx.lineTo(px, chart.chartArea.bottom);
      ctx.stroke();
      ctx.restore();
    },
  };

  SP.batang = function (warna) {
    return { backgroundColor: warna, borderRadius: 4, borderSkipped: "start", maxBarThickness: 22, categoryPercentage: 0.72, barPercentage: 0.9 };
  };
  SP.garis = function (warna, tebal) {
    return {
      borderColor: warna, backgroundColor: warna, borderWidth: tebal || 2, pointRadius: 4, pointHoverRadius: 6,
      pointBorderColor: SP.surface, pointBorderWidth: 2, tension: 0.25, spanGaps: true,
    };
  };

  // Tombol "Tabel" <-> "Grafik" pada setiap kartu grafik
  document.addEventListener("click", function (e) {
    var b = e.target.closest("[data-toggle-tabel]");
    if (!b) return;
    var tabel = document.getElementById(b.getAttribute("data-toggle-tabel"));
    var grafik = document.getElementById(b.getAttribute("data-grafik"));
    if (!tabel) return;
    var tampil = !tabel.classList.contains("tampil");
    tabel.classList.toggle("tampil", tampil);
    if (grafik) grafik.style.display = tampil ? "none" : "";
    b.setAttribute("aria-expanded", tampil ? "true" : "false");
    b.innerHTML = tampil ? '<i class="bi bi-bar-chart-line"></i> Grafik' : '<i class="bi bi-table"></i> Tabel';
  });
})();
