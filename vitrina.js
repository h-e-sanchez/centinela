// vitrina.js — portada: todos los reportes en una pantalla y tarjetas, todo desde reportes/catalogo.json.

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
const fichaDe = (rep) => `ficha.html?r=${encodeURIComponent(rep.slug)}`;

// ------------------------------------------------------------------ panel "en una pantalla"
// Una opción por reporte (publicados y en preparación) a la izquierda; a la derecha, el resumen,
// las cifras de la historia y el reporte embebido de la opción elegida.

function opcion(rep, i, alElegir) {
  const cifra = rep.historias?.[0];
  const boton = el("button", { type: "button", role: "tab", clase: "opcion", id: `opcion-${i}`,
                               "aria-controls": "visor", "aria-selected": "false" }, [
    el("span", { clase: "eyebrow", texto: rep.publicado ? rep.tema : `En preparación · ${rep.tema}` }),
    el("strong", { texto: rep.titulo }),
    cifra ? el("span", { clase: `opcion-cifra ${cifra.tono}`, texto: `${cifra.resultado} · ${cifra.industria}` }) : null,
  ]);
  boton.addEventListener("click", () => alElegir(i));
  return boton;
}

function visor(rep) {
  const partes = [
    el("h2", { texto: rep.titulo }),
    el("p", { clase: "hint", texto: rep.resumen }),
  ];
  if (rep.historias?.length) {
    partes.push(el("ul", { clase: "cifras" }, rep.historias.map((h) =>
      el("li", { clase: h.tono, title: h.texto }, [el("strong", { texto: h.resultado }), el("span", { texto: h.industria })])
    )));
  }
  if (rep.publicado) {
    partes.push(
      el("div", { clase: "pbi-embed" }, [
        el("iframe", { title: `${rep.titulo} en Power BI`, src: rep.embed_url, loading: "lazy", allowfullscreen: "" }),
      ]),
      el("p", { clase: "acciones-destacado" }, [
        el("a", { clase: "btn-primario", href: fichaDe(rep), texto: "Ver ficha, descargas y guía →" }),
        el("span", { clase: "hint", texto: ` ${rep.habilidades.slice(0, 4).join(" · ")}` }),
      ]),
    );
  } else {
    partes.push(el("div", { clase: "pbi-embed" }, [
      el("div", { clase: "placeholder", texto: "En construcción: datos sintéticos, modelo y guía en camino." }),
    ]));
  }
  return partes;
}

function panel(lista, inicial) {
  const selector = el("div", { clase: "selector", role: "tablist", "aria-label": "Reportes de la vitrina" });
  const contenido = el("div", { clase: "visor", id: "visor", role: "tabpanel" });
  const elegir = (i) => {
    selector.querySelectorAll(".opcion").forEach((b, j) => b.setAttribute("aria-selected", String(i === j)));
    contenido.setAttribute("aria-labelledby", `opcion-${i}`);
    contenido.replaceChildren(...visor(lista[i]));
  };
  lista.forEach((rep, i) => selector.append(opcion(rep, i, elegir)));
  $("#destacado").replaceChildren(
    el("p", { clase: "eyebrow", texto: `La vitrina en una pantalla · ${lista.length} reportes` }),
    el("div", { clase: "panel-vitrina" }, [selector, contenido]),
  );
  elegir(inicial);
}

// ------------------------------------------------------------------ tarjetas

function tarjeta(rep) {
  const img = rep.portada ? el("img", { src: `reportes/${rep.slug}/${rep.portada}`, alt: `Vista del reporte ${rep.titulo}`, loading: "lazy" }) : null;
  if (img) img.addEventListener("error", () => img.remove());  // sin captura todavía: tarjeta solo con texto
  const tema = rep.estado === "en-preparacion" ? `En preparación · ${rep.tema}` : rep.tema;
  return el("a", { clase: "tarjeta-rep", href: fichaDe(rep) }, [
    img,
    el("p", { clase: "eyebrow", texto: tema }),
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
    const lista = [
      ...reportes.map((r) => ({ ...r, publicado: Boolean(r.embed_url) && r.estado !== "en-preparacion" })),
      ...proximos.map((p) => ({ ...p, publicado: false })),
    ];
    const inicial = Math.max(0, lista.findIndex((r) => r.destacado && r.publicado));
    panel(lista, inicial);
    $("#tarjetas").replaceChildren(...reportes.map(tarjeta), ...proximos.map(proximo));
  })
  .catch((e) => {
    $("#destacado").textContent = `No se pudo cargar la vitrina (${e.message}).`;
  });
