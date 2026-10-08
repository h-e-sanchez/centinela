// ficha.js — ficha genérica de un reporte de la vitrina (ficha.html?r=<slug>).
// Todo sale de reportes/catalogo.json y de reportes/<slug>/guia.md: agregar un reporte
// nuevo no requiere tocar este archivo.

const $ = (sel) => document.querySelector(sel);

function el(tag, attrs = {}, hijos = []) {
  const n = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === "texto") n.textContent = v;
    else if (k === "clase") n.className = v;
    else n.setAttribute(k, v);
  }
  for (const h of hijos) if (h) n.append(h);
  return n;
}

function tamano(bytes) {
  return bytes >= 1024 * 1024 ? `${(bytes / 1024 / 1024).toFixed(1)} MB` : `${Math.max(1, Math.round(bytes / 1024))} KB`;
}

// Devuelve el tamaño del archivo, o null si no existe (así un descargable pendiente no se muestra).
async function existe(url) {
  try {
    const r = await fetch(url, { method: "HEAD", cache: "no-store" });
    if (!r.ok) return null;
    return Number(r.headers.get("content-length")) || 0;
  } catch (e) {
    return null;
  }
}

async function iniciar() {
  const { reportes } = await fetch("reportes/catalogo.json").then((r) => r.json());
  const slug = new URLSearchParams(location.search).get("r");
  const rep = reportes.find((x) => x.slug === slug) || reportes.find((x) => x.destacado) || reportes[0];
  const base = `reportes/${rep.slug}/`;

  document.title = `centinela — ${rep.titulo}`;
  $("#f-titulo").textContent = rep.titulo;
  $("#f-resumen").textContent = rep.resumen;
  $("#f-habilidades").replaceChildren(...rep.habilidades.map((h) => el("li", { texto: h })));

  if (rep.embed_url) {
    const iframe = el("iframe", { title: `${rep.titulo} en Power BI`, src: rep.embed_url, loading: "lazy", allowfullscreen: "" });
    $("#f-embed").replaceChildren(iframe);
    window.analitica?.alVer(iframe, `reporte-cargado/${rep.slug}`);
    $("#f-pantalla").href = rep.embed_url;
  } else {
    // En preparación: el modelo y los datos ya están en el repo; falta publicarlo desde Desktop.
    $("#f-embed").replaceChildren(el("p", { clase: "placeholder", texto:
      "En preparación: el modelo y los datos ya están publicados en GitHub; el reporte interactivo se incrusta aquí al publicarlo desde Power BI." }));
    $("#f-pantalla").remove();
  }

  $("#f-historias").replaceChildren(...(rep.historias || []).map((h) =>
    el("article", { clase: `historia ${h.tono}` }, [
      el("p", { clase: "historia-industria", texto: h.industria }),
      el("p", { clase: "historia-resultado", texto: h.resultado }),
      el("p", { clase: "historia-texto", texto: h.texto }),
    ])));

  const botones = await Promise.all(rep.descargas.map(async (d) => {
    const bytes = await existe(base + d.archivo);
    if (bytes === null) return null;
    return el("a", { clase: "descarga", href: base + d.archivo, download: "" }, [
      el("span", { clase: "descarga-etiqueta", texto: d.etiqueta }),
      el("span", { clase: "descarga-detalle", texto: `${d.detalle} · ${tamano(bytes)}` }),
    ]);
  }));
  $("#f-descargas").replaceChildren(...botones.filter(Boolean));

  const md = await fetch(base + "guia.md").then((r) => r.text());
  $("#f-guia-md").href = base + "guia.md";
  $("#f-guia").innerHTML = window.marked ? window.marked.parse(md) : "";
  if (!window.marked) $("#f-guia").append(el("pre", { texto: md }));  // sin CDN: la guía en texto plano

  const glosario = await fetch(base + "glosario.md").then((r) => (r.ok ? r.text() : null));
  if (glosario) {
    $("#f-glosario-md").href = base + "glosario.md";
    $("#f-glosario").innerHTML = window.marked ? window.marked.parse(glosario) : "";
    if (!window.marked) $("#f-glosario").append(el("pre", { texto: glosario }));
  } else {
    $("#glosario").remove();
  }

  $("#f-tecnico").replaceChildren(...rep.tecnico.map((t) =>
    el("li", {}, [el("a", { href: t.url, texto: t.etiqueta })])));
}

iniciar().catch((e) => {
  $("#f-titulo").textContent = "No se pudo cargar la ficha";
  $("#f-resumen").textContent = `${e.message}. Si abriste el archivo con doble clic, sírvelo con: python -m http.server`;
});
