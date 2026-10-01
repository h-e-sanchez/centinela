/* tema día/noche — mismo patrón que reporte.html y datos.html: por defecto claro; el oscuro
   se activa solo por elección explícita guardada en localStorage ("centinela:theme").
   Se carga en <head> sin defer para pintar el tema antes del primer render. */
(function () {
  var root = document.documentElement;
  var read = function () { try { return JSON.parse(localStorage.getItem("centinela:theme") || "null"); } catch (e) { return null; } };
  var current = function () { return read() === "dark" ? "dark" : "light"; };
  if (current() === "dark") root.dataset.theme = "dark";
  document.addEventListener("DOMContentLoaded", function () {
    var btn = document.getElementById("theme-toggle");
    if (!btn) return;
    var paint = function () {
      var c = current();
      btn.textContent = c === "dark" ? "día" : "noche";
      btn.setAttribute("aria-pressed", String(c === "dark"));
    };
    paint();
    btn.addEventListener("click", function () {
      var next = current() === "dark" ? "light" : "dark";
      if (next === "dark") root.dataset.theme = "dark"; else root.removeAttribute("data-theme");
      try { localStorage.setItem("centinela:theme", JSON.stringify(next)); } catch (e) {}
      paint();
    });
  });
})();
