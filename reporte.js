// reporte.js — el reporte del modelo Power BI de centinela, recalculado en el navegador.
//
// - Datos: data/escenarios-web.json, generado desde data/escenarios/*.csv (los mismos CSV
//   que carga el modelo vía el parámetro UrlDatos): tres industrias, así los números
//   coinciden con el reporte de Power BI.
// - DAX: se lee en vivo desde el TMDL versionado en powerbi/, no se copia aquí. La página
//   y el modelo no pueden divergir.
// - La aritmética espeja las medidas: SUM, DIVIDE (blank si el denominador es 0) y el
//   semáforo estricto (>) con alerta >5% y crítica >15%, igual que src/motor.py.

// URL de "Publicar en la Web" (app.powerbi.com/view?r=...). Vacía = se muestra el aviso.
const PBI_EMBED_URL = "https://app.powerbi.com/view?r=eyJrIjoiZjBhYmEyY2UtODgwOS00YjcyLTlhYjgtMmZlMjFiMjJmZWEzIiwidCI6IjdjMTM5MTRjLTZiZTAtNDM2OC05MjMwLTVhMjNlYjhmZjQ3ZiIsImMiOjR9&pageName=portada";

const TMDL = "powerbi/presupuesto-vs-real/centinela.SemanticModel/definition/tables/desviacion.tmdl";
const MESES = ["", "Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"];
const UMBRAL = 0.05;
const UMBRAL_CRITICO = 0.15;

const $ = (sel) => document.querySelector(sel);
const clp = new Intl.NumberFormat("es-CL", { style: "currency", currency: "CLP", maximumFractionDigits: 0 });
const pct = (v) => (v === null ? "—" : (v * 100).toLocaleString("es-CL", { minimumFractionDigits: 1, maximumFractionDigits: 1 }) + "%");
const millones = (v) => (v < 0 ? "-$" : "$") + (Math.abs(v) / 1e6).toLocaleString("es-CL", { maximumFractionDigits: 1 }) + " MM";

const estado = { datos: {}, filas: [], dax: {}, industria: "todas", mes: "todos", centro: "todos" };
const NOMBRE_INDUSTRIA = { Manufactura: "Manufactura", Energia: "Energía", Salud: "Salud" };
const ORDEN_INDUSTRIAS = ["Manufactura", "Energia", "Salud"]; // la historia: positivo → neutro → rojo
const industrias = () => ORDEN_INDUSTRIAS.filter((i) => i in estado.datos);

// -------------------------------------------------------------- "medidas"

const divide = (a, b) => (b ? a / b : null);
const suma = (filas, campo) => filas.reduce((s, f) => s + f[campo], 0);

function semaforo(ppto, real) {
  if (ppto === 0) return real !== 0 ? "Crítica" : "OK";
  const m = Math.abs((real - ppto) / ppto);
  if (m > UMBRAL_CRITICO) return "Crítica";
  if (m > UMBRAL) return "Alerta";
  return "OK";
}

function filtradas({ ignorarMes = false } = {}) {
  return estado.filas.filter((f) =>
    (ignorarMes || estado.mes === "todos" || f.mes === Number(estado.mes)) &&
    (estado.centro === "todos" || f.centro_costo === estado.centro));
}

function resultadoOperacional(filas, campo) {
  const g = (nombre) => suma(filas.filter((f) => f.grupo_cuenta === nombre), campo);
  return g("Ingresos") - g("Costos") - g("Gastos Operacionales");
}

// -------------------------------------------------------------- DAX desde TMDL

function parsearTmdl(texto) {
  const lineas = texto.replace(/\r\n/g, "\n").split("\n");
  const objetos = {};
  for (let i = 0; i < lineas.length; i++) {
    const m = lineas[i].match(/^\t(measure|column) (?:'((?:[^']|'')+)'|(\S+)) =(.*)$/);
    if (!m) continue;
    const nombre = (m[2] || m[3]).replace(/''/g, "'");
    const descripcion = (lineas[i - 1] || "").startsWith("\t/// ") ? lineas[i - 1].slice(5) : "";
    let cuerpo = m[4].trim();
    if (!cuerpo) {
      const partes = [];
      for (let j = i + 1; j < lineas.length && lineas[j].startsWith("\t\t\t"); j++) partes.push(lineas[j].slice(3));
      cuerpo = partes.join("\n");
    }
    const tipo = m[1] === "measure" ? "medida" : "columna calculada";
    objetos[nombre] = { tipo, descripcion, dax: `${nombre} =\n${cuerpo}` };
  }
  return objetos;
}

function mostrarDax(boton) {
  const caja = boton.closest(".visual, .kpi").querySelector(".dax");
  if (!caja.hidden) { caja.hidden = true; boton.setAttribute("aria-expanded", "false"); return; }
  caja.replaceChildren();
  for (const nombre of boton.dataset.medidas.split("|")) {
    const obj = estado.dax[nombre];
    const p = document.createElement("p");
    p.className = "dax-meta";
    p.textContent = obj ? `${obj.tipo} · ${obj.descripcion}` : `${nombre}: no encontrada en el TMDL`;
    const pre = document.createElement("pre");
    pre.textContent = obj ? obj.dax : "";
    caja.append(p, pre);
  }
  caja.hidden = false;
  boton.setAttribute("aria-expanded", "true");
}

// -------------------------------------------------------------- visuales

function kpis() {
  const f = filtradas();
  const ppto = suma(f, "monto_presupuesto");
  const real = suma(f, "monto_real");
  const alerta = f.filter((x) => semaforo(x.monto_presupuesto, x.monto_real) !== "OK").length;
  const tarjetas = [
    ["Monto Presupuesto", millones(ppto)],
    ["Monto Real", millones(real)],
    ["Desviación %", pct(divide(real - ppto, ppto))],
    ["% Cumplimiento", pct(divide(real, ppto))],
    ["Líneas en Alerta", `${alerta} de ${f.length}`],
    ["Resultado Operacional", millones(resultadoOperacional(f, "monto_real"))],
  ];
  const grid = $("#kpi-grid");
  grid.replaceChildren();
  for (const [nombre, valor] of tarjetas) {
    const art = document.createElement("article");
    art.className = "kpi";
    art.innerHTML = `<p class="kpi-nombre"></p><p class="kpi-valor"></p>
      <button type="button" class="btn-dax" aria-expanded="false">DAX</button><div class="dax" hidden></div>`;
    art.querySelector(".kpi-nombre").textContent = nombre;
    art.querySelector(".kpi-valor").textContent = valor;
    art.querySelector(".btn-dax").dataset.medidas = nombre;
    grid.append(art);
  }
}

function svg(ancho, alto, contenido) {
  return `<svg viewBox="0 0 ${ancho} ${alto}" role="img" preserveAspectRatio="xMidYMid meet">${contenido}</svg>`;
}

function tendencia() {
  const f = filtradas({ ignorarMes: true });
  const meses = [...new Set(estado.filas.map((x) => x.mes))].sort((a, b) => a - b);
  const serie = (campo) => meses.map((m) => suma(f.filter((x) => x.mes === m), campo));
  const ppto = serie("monto_presupuesto");
  const real = serie("monto_real");
  const W = 720, H = 260, L = 64, R = 16, T = 16, B = 32;
  // Eje que no parte en cero (como el "mínimo automático" de Power BI): la brecha
  // presupuesto vs. real es de pocos puntos y con el eje en cero se vería plana.
  const todos = [...ppto, ...real];
  const max = Math.max(...todos) * 1.04 || 1;
  const min = Math.min(...todos) * 0.96;
  const x = (i) => L + (i * (W - L - R)) / Math.max(meses.length - 1, 1);
  const y = (v) => T + (H - T - B) * (1 - (v - min) / (max - min || 1));
  const linea = (vals, clase) =>
    `<polyline class="${clase}" points="${vals.map((v, i) => `${x(i)},${y(v)}`).join(" ")}" />`;
  let ejes = "";
  for (let k = 0; k <= 4; k++) {
    const v = min + ((max - min) * k) / 4;
    ejes += `<line class="grilla" x1="${L}" x2="${W - R}" y1="${y(v)}" y2="${y(v)}" />` +
      `<text class="eje" x="${L - 8}" y="${y(v) + 4}" text-anchor="end">${(v / 1e6).toLocaleString("es-CL", { maximumFractionDigits: 0 })}</text>`;
  }
  meses.forEach((m, i) => {
    const sel = estado.mes !== "todos" && Number(estado.mes) === m;
    ejes += `<text class="eje${sel ? " sel" : ""}" x="${x(i)}" y="${H - 10}" text-anchor="middle">${MESES[m]}</text>`;
  });
  const puntos = real.map((v, i) => `<circle class="punto-real" cx="${x(i)}" cy="${y(v)}" r="3"><title>${MESES[meses[i]]}: real ${clp.format(v)} · ppto ${clp.format(ppto[i])}</title></circle>`).join("");
  $("#g-tendencia").innerHTML =
    svg(W, H, ejes + linea(ppto, "serie-ppto") + linea(real, "serie-real") + puntos) +
    `<p class="leyenda"><span class="sw sw-ppto"></span>Monto Presupuesto <span class="sw sw-real"></span>Monto Real <span class="eje-nota">(millones de $)</span></p>`;
}

function centros() {
  const f = filtradas();
  const nombres = [...new Set(f.map((x) => x.centro_costo))].sort();
  const datos = nombres.map((n) => {
    const g = f.filter((x) => x.centro_costo === n);
    const ppto = suma(g, "monto_presupuesto"), real = suma(g, "monto_real");
    return { n, d: divide(real - ppto, ppto), est: semaforo(ppto, real) };
  });
  const W = 720, fila = 30, L = 190, H = fila * datos.length + 24;
  const maxAbs = Math.max(0.2, ...datos.map((x) => Math.abs(x.d || 0)));
  const cero = L + (W - L - 60) / 2;
  const esc = (v) => ((W - L - 60) / 2) * (v / maxAbs);
  let cuerpo = `<line class="grilla" x1="${cero}" x2="${cero}" y1="0" y2="${H - 20}" />`;
  datos.forEach((x, i) => {
    const yy = i * fila + 6, w = esc(x.d || 0);
    const clase = { OK: "ok", Alerta: "alerta", Crítica: "critica" }[x.est];
    cuerpo += `<text class="eje" x="${L - 10}" y="${yy + 15}" text-anchor="end">${x.n}</text>` +
      `<rect class="barra ${clase}" x="${Math.min(cero, cero + w)}" y="${yy}" width="${Math.abs(w)}" height="20"><title>${x.n}: ${pct(x.d)} (${x.est})</title></rect>` +
      `<text class="eje" x="${cero + w + (w >= 0 ? 6 : -6)}" y="${yy + 15}" text-anchor="${w >= 0 ? "start" : "end"}">${pct(x.d)}</text>`;
  });
  $("#g-centros").innerHTML = svg(W, H, cuerpo) +
    `<p class="leyenda">Color según el semáforo: <span class="estado ok">ok</span> <span class="estado alerta">alerta &gt;5%</span> <span class="estado critica">crítica &gt;15%</span></p>`;
}

function matriz() {
  const f = filtradas();
  const fila = (nivel, nombre, g) => {
    const ppto = suma(g, "monto_presupuesto"), real = suma(g, "monto_real");
    const est = semaforo(ppto, real);
    const clase = { OK: "ok", Alerta: "alerta", Crítica: "critica" }[est];
    return `<tr class="${nivel}"><td>${nombre}</td><td class="num">${clp.format(ppto)}</td><td class="num">${clp.format(real)}</td>` +
      `<td class="num">${pct(divide(real - ppto, ppto))}</td><td><span class="estado ${clase}">${est}</span></td></tr>`;
  };
  let html = "<thead><tr><th>Centro de costo / componente</th><th class=\"num\">Presupuesto</th><th class=\"num\">Real</th><th class=\"num\">Desv. %</th><th>Estado</th></tr></thead><tbody>";
  for (const cc of [...new Set(f.map((x) => x.centro_costo))].sort()) {
    const g = f.filter((x) => x.centro_costo === cc);
    html += fila("nivel-1", cc, g);
    for (const comp of [...new Set(g.map((x) => x.componente))].sort()) {
      html += fila("nivel-2", comp, g.filter((x) => x.componente === comp));
    }
  }
  html += fila("subtotal", "Total", f) + "</tbody>";
  $("#t-matriz").innerHTML = html;
}

function eerr() {
  const f = filtradas();
  const g = (n, campo) => suma(f.filter((x) => x.grupo_cuenta === n), campo);
  const fila = (nombre, ppto, real, clase = "") => {
    const est = semaforo(ppto, real);
    const c = { OK: "ok", Alerta: "alerta", Crítica: "critica" }[est];
    return `<tr class="${clase}"><td>${nombre}</td><td class="num">${clp.format(ppto)}</td><td class="num">${clp.format(real)}</td>` +
      `<td class="num">${pct(divide(real - ppto, ppto))}</td><td><span class="estado ${c}">${est}</span></td></tr>`;
  };
  let html = "<thead><tr><th>Grupo</th><th class=\"num\">Presupuesto</th><th class=\"num\">Real</th><th class=\"num\">Desv. %</th><th>Estado</th></tr></thead><tbody>";
  for (const n of ["Ingresos", "Costos", "Gastos Operacionales"]) html += fila(n, g(n, "monto_presupuesto"), g(n, "monto_real"));
  html += fila("Resultado Operacional", resultadoOperacional(f, "monto_presupuesto"), resultadoOperacional(f, "monto_real"), "subtotal");
  $("#t-eerr").innerHTML = html + "</tbody>";
}

function escenarios() {
  const fila = (nombre, filas) => {
    const f = filas.filter((x) => estado.mes === "todos" || x.mes === Number(estado.mes));
    const ppto = resultadoOperacional(f, "monto_presupuesto");
    const real = resultadoOperacional(f, "monto_real");
    const d = ppto ? (real - ppto) / Math.abs(ppto) : null;
    // Mismo criterio que la medida Color Resultado: verde >= +2%, rojo <= -2%, gris si es neutro.
    const [clase, texto] = d === null ? ["neutro", "—"] : d >= 0.02 ? ["ok", "Positivo"] : d <= -0.02 ? ["critica", "Rojo"] : ["neutro", "Neutro"];
    const sel = estado.industria === nombre ? ' class="seleccionada"' : "";
    return `<tr${sel}><td>${NOMBRE_INDUSTRIA[nombre] || nombre}</td><td class="num">${millones(ppto)}</td>` +
      `<td class="num">${millones(real)}</td><td class="num">${pct(d)}</td><td><span class="estado ${clase}">${texto}</span></td></tr>`;
  };
  let html = '<thead><tr><th>Industria</th><th class="num">RO presupuestado</th><th class="num">RO real</th><th class="num">Desv. %</th><th>Escenario</th></tr></thead><tbody>';
  for (const nombre of industrias()) html += fila(nombre, estado.datos[nombre]);
  $("#t-escenarios").innerHTML = html + "</tbody>";
}

function render() {
  escenarios();
  kpis();
  tendencia();
  centros();
  matriz();
  eerr();
}

// -------------------------------------------------------------- arranque

function opciones(select, valores, etiqueta) {
  select.replaceChildren(new Option("Todos", "todos"), ...valores.map((v) => new Option(etiqueta(v), v)));
}

async function iniciar() {
  if (PBI_EMBED_URL) {
    const iframe = document.createElement("iframe");
    iframe.src = PBI_EMBED_URL;
    iframe.title = "Reporte de centinela en Power BI";
    iframe.allowFullscreen = true;
    iframe.loading = "lazy";
    $("#pbi-embed").replaceChildren(iframe);
    window.analitica?.alVer(iframe, "reporte-cargado/presupuesto-vs-real");
  }
  const [datos, tmdl] = await Promise.all([
    fetch("data/escenarios-web.json").then((r) => r.json()),
    fetch(TMDL).then((r) => (r.ok ? r.text() : "")).catch(() => ""),
  ]);
  estado.datos = datos;
  estado.dax = parsearTmdl(tmdl);
  const usarIndustria = (valor) => {
    estado.industria = valor;
    estado.filas = valor === "todas" ? Object.values(datos).flat() : datos[valor];
    estado.centro = "todos";
    opciones($("#f-centro"), [...new Set(estado.filas.map((f) => f.centro_costo))].sort(), (c) => c);
  };
  usarIndustria("todas");

  $("#f-industria").replaceChildren(new Option("Todas (consolidado)", "todas"),
    ...industrias().map((i) => new Option(NOMBRE_INDUSTRIA[i] || i, i)));
  $("#f-industria").addEventListener("change", (e) => { usarIndustria(e.target.value); render(); });
  opciones($("#f-mes"), [...new Set(estado.filas.map((f) => f.mes))].sort((a, b) => a - b), (m) => MESES[m]);
  $("#f-mes").addEventListener("change", (e) => { estado.mes = e.target.value; render(); });
  $("#f-centro").addEventListener("change", (e) => { estado.centro = e.target.value; render(); });
  document.addEventListener("click", (e) => {
    const b = e.target.closest(".btn-dax");
    if (b) mostrarDax(b);
  });
  render();
}

iniciar().catch((e) => {
  $("#kpi-grid").textContent = `No se pudo cargar el reporte (${e.message}). Si abriste el archivo con doble clic, sírvelo con: python -m http.server`;
});
