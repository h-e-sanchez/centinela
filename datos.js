// datos.js — explora los 3 ejemplos reales del motor y recalcula el semáforo
// en vivo. Espeja EXACTAMENTE la aritmética de src/motor.py (clasificar /
// resumen_por_grupo) — comparación estricta (>), no inclusiva; sumas simples
// por grupo — pero NO reimplementa el generador: los datos vienen ya
// generados por Python en data/ejemplos-web.json (ver
// data/exportar_ejemplos_web.py), porque el RNG de JS no reproduce
// random.Random de Python.

const MESES_ES = ["", "Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"];
const GRUPOS_CUENTA = ["Ingresos", "Costos", "Gastos Operacionales"];

const $ = (sel) => document.querySelector(sel);

const state = {
  ejemplos: null,
  seed: "42",
  mes: "todos",
  umbralPct: 0.05,
  umbralCriticoPct: 0.15,
};

// -------------------------------------------------------------- motor (JS)

function clasificar(desviacionMonto, desviacionPct, umbralPct, umbralCriticoPct) {
  if (desviacionPct === null) {
    // Sin presupuesto (monto_presupuesto === 0): cualquier real no-cero es
    // 100% no presupuestado -- mismo criterio que _clasificar en motor.py.
    return desviacionMonto !== 0 ? "critica" : "ok";
  }
  const magnitud = Math.abs(desviacionPct);
  if (magnitud > umbralCriticoPct) return "critica";
  if (magnitud > umbralPct) return "alerta";
  return "ok";
}

function calcularDesviacion(fila, umbralPct, umbralCriticoPct) {
  const desviacionMonto = fila.monto_real - fila.monto_presupuesto;
  const desviacionPct = fila.monto_presupuesto ? desviacionMonto / fila.monto_presupuesto : null;
  const estado = clasificar(desviacionMonto, desviacionPct, umbralPct, umbralCriticoPct);
  return { ...fila, desviacion_monto: desviacionMonto, desviacion_pct: desviacionPct, estado };
}

function resumenDe(nombre, montoPresupuesto, montoReal, umbralPct, umbralCriticoPct) {
  const desviacionMonto = montoReal - montoPresupuesto;
  const desviacionPct = montoPresupuesto ? desviacionMonto / montoPresupuesto : null;
  const estado = clasificar(desviacionMonto, desviacionPct, umbralPct, umbralCriticoPct);
  return { nombre, monto_presupuesto: montoPresupuesto, monto_real: montoReal, desviacion_pct: desviacionPct, estado };
}

function resumenPorGrupo(filas, umbralPct, umbralCriticoPct) {
  const presupuesto = Object.fromEntries(GRUPOS_CUENTA.map((g) => [g, 0]));
  const real = Object.fromEntries(GRUPOS_CUENTA.map((g) => [g, 0]));
  for (const f of filas) {
    if (!(f.grupo_cuenta in presupuesto)) continue;
    presupuesto[f.grupo_cuenta] += f.monto_presupuesto;
    real[f.grupo_cuenta] += f.monto_real;
  }
  const resumenes = GRUPOS_CUENTA.map((g) => resumenDe(g, presupuesto[g], real[g], umbralPct, umbralCriticoPct));
  const resultadoPresupuesto = presupuesto["Ingresos"] - presupuesto["Costos"] - presupuesto["Gastos Operacionales"];
  const resultadoReal = real["Ingresos"] - real["Costos"] - real["Gastos Operacionales"];
  resumenes.push(resumenDe("Resultado Operacional", resultadoPresupuesto, resultadoReal, umbralPct, umbralCriticoPct));
  return resumenes;
}

// -------------------------------------------------------------- formato

const fmtMonto = (v) => "$" + Math.round(v).toLocaleString("es-CL");
const fmtPct = (v) => (v === null ? "sin presup." : (v >= 0 ? "+" : "") + (v * 100).toFixed(1).replace(".", ",") + "%");
const badge = (estado) => `<span class="estado ${estado}">${estado}</span>`;

// -------------------------------------------------------------- render

function filasDelEjemplo() {
  const todas = state.ejemplos[state.seed];
  return state.mes === "todos" ? todas : todas.filter((f) => String(f.mes) === state.mes);
}

function renderEerr(filas) {
  const tbody = $("#tabla-eerr tbody");
  tbody.innerHTML = "";
  for (const r of resumenPorGrupo(filas, state.umbralPct, state.umbralCriticoPct)) {
    const tr = document.createElement("tr");
    if (r.nombre === "Resultado Operacional") tr.className = "subtotal";
    tr.innerHTML = `<td>${r.nombre}</td><td class="num">${fmtMonto(r.monto_presupuesto)}</td>` +
      `<td class="num">${fmtMonto(r.monto_real)}</td><td class="num">${fmtPct(r.desviacion_pct)}</td>` +
      `<td>${badge(r.estado)}</td>`;
    tbody.appendChild(tr);
  }
}

function renderDetalle(filas) {
  const calculadas = filas.map((f) => calcularDesviacion(f, state.umbralPct, state.umbralCriticoPct));
  const conteo = { ok: 0, alerta: 0, critica: 0 };
  calculadas.forEach((f) => conteo[f.estado]++);
  $("#resumen-detalle").textContent =
    `${calculadas.length} líneas — ok: ${conteo.ok}, alerta: ${conteo.alerta}, crítica: ${conteo.critica}`;

  const tbody = $("#tabla-detalle tbody");
  tbody.innerHTML = "";
  for (const f of calculadas) {
    const tr = document.createElement("tr");
    const mesLabel = state.mes === "todos" ? `${MESES_ES[f.mes]} ` : "";
    tr.innerHTML = `<td>${mesLabel}${f.centro_costo}</td><td>${f.componente}</td><td>${f.grupo_cuenta}</td>` +
      `<td class="num">${fmtMonto(f.monto_presupuesto)}</td><td class="num">${fmtMonto(f.monto_real)}</td>` +
      `<td class="num">${fmtPct(f.desviacion_pct)}</td><td>${badge(f.estado)}</td>`;
    tbody.appendChild(tr);
  }
}

function render() {
  const filas = filasDelEjemplo();
  renderEerr(filas);
  renderDetalle(filas);
}

// -------------------------------------------------------------- init

function poblarSelectorMeses() {
  const sel = $("#mes-select");
  sel.innerHTML = '<option value="todos">Todos</option>';
  for (let m = 1; m <= 12; m++) {
    const opt = document.createElement("option");
    opt.value = String(m);
    opt.textContent = MESES_ES[m];
    sel.appendChild(opt);
  }
}

function wireControles() {
  $("#ejemplo-select").addEventListener("change", (e) => { state.seed = e.target.value; render(); });
  $("#mes-select").addEventListener("change", (e) => { state.mes = e.target.value; render(); });
  $("#umbral-pct").addEventListener("input", (e) => {
    const v = Number(e.target.value);
    if (Number.isFinite(v) && v >= 0) { state.umbralPct = v / 100; render(); }
  });
  $("#umbral-critico-pct").addEventListener("input", (e) => {
    const v = Number(e.target.value);
    if (Number.isFinite(v) && v >= 0) { state.umbralCriticoPct = v / 100; render(); }
  });
}

async function init() {
  poblarSelectorMeses();
  wireControles();
  const res = await fetch("data/ejemplos-web.json");
  state.ejemplos = await res.json();
  render();
}

init();
