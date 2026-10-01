// vitrina.js — portada: reporte destacado y tarjetas, todo desde reportes/catalogo.json.

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

const chips = (lista) => el("ul", { clase: "chips" }, lista.map((h) => el("li", { texto: h })));

function destacado(rep) {
  const ficha = `ficha.html?r=${encodeURIComponent(rep.slug)}`;
  $("#destacado").replaceChildren(
    el("p", { clase: "eyebrow", texto: `Destacado · ${rep.tema}` }),
    el("h2", { texto: rep.titulo }),
    el("p", { clase: "hint", texto: rep.resumen }),
    chips(rep.habilidades),
    el("div", { clase: "pbi-embed" }, [
      el("iframe", { title: `${rep.titulo} en Power BI`, src: rep.embed_url, loading: "lazy", allowfullscreen: "" }),
    ]),
    el("p", { clase: "acciones-destacado" }, [
      el("a", { clase: "btn-primario", href: ficha, texto: "Ver ficha, descargas y guía →" }),
    ]),
  );
}

function tarjeta(rep) {
  const ficha = `ficha.html?r=${encodeURIComponent(rep.slug)}`;
  const img = rep.portada ? el("img", { src: `reportes/${rep.slug}/${rep.portada}`, alt: `Vista del reporte ${rep.titulo}`, loading: "lazy" }) : null;
  if (img) img.addEventListener("error", () => img.remove());  // sin captura todavía: tarjeta solo con texto
  return el("a", { clase: "tarjeta-rep", href: ficha }, [
    img,
    el("p", { clase: "eyebrow", texto: rep.tema }),
    el("h3", { texto: rep.titulo }),
    el("p", { clase: "tarjeta-resumen", texto: rep.resumen }),
    chips(rep.habilidades.slice(0, 3)),
  ]);
}

function proximo(p) {
  return el("div", { clase: "tarjeta-rep proximo" }, [
    el("p", { clase: "eyebrow", texto: `En preparación · ${p.tema}` }),
    el("h3", { texto: p.titulo }),
    el("p", { clase: "tarjeta-resumen", texto: p.resumen }),
  ]);
}

fetch("reportes/catalogo.json")
  .then((r) => r.json())
  .then(({ reportes, proximos = [] }) => {
    const top = reportes.find((r) => r.destacado) || reportes[0];
    destacado(top);
    $("#tarjetas").replaceChildren(...reportes.map(tarjeta), ...proximos.map(proximo));
  })
  .catch((e) => {
    $("#destacado").textContent = `No se pudo cargar la vitrina (${e.message}).`;
  });
