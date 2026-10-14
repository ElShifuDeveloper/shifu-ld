// Barras SVG interactivas con navegación al detalle (patrón de appDemo23-25), construidas con el DOM
// en lugar de concatenar cadenas: el texto va por textContent/setAttribute, así que un nombre con
// comillas, `<` o `&` ni rompe el SVG ni ejecuta código (los demos lo insertan con innerHTML).
// Requiere lista-delimitada.js. HTML: <svg id="svg" xmlns="http://www.w3.org/2000/svg" width="1000" height="600" role="img" aria-label="...">

const NS = "http://www.w3.org/2000/svg";

function el(nombre, atributos = {}, texto = null) {
  const nodo = document.createElementNS(NS, nombre);
  for (const [k, v] of Object.entries(atributos)) nodo.setAttribute(k, String(v));
  if (texto !== null) nodo.textContent = texto;
  return nodo;
}

// alAbrir(dato) se invoca con clic, Enter o Espacio sobre una barra.
function dibujarBarrasSvg(svg, datos, { titulo = "", alAbrir = null, margenIzq = 150, margenDer = 100 } = {}) {
  const ancho = svg.width.baseVal.value;
  const alto = svg.height.baseVal.value;
  svg.replaceChildren(
    el("defs", {}, null),
    el("rect", { x: 0, y: 0, width: ancho, height: alto, fill: "black" }),
    el("text", { x: 40, y: 50, fill: "yellow", "font-size": 32, "font-family": "arial" }, titulo)
  );
  const grad = el("linearGradient", { id: "deg", x1: "0%", x2: "100%", y1: "0%", y2: "0%" });
  grad.append(el("stop", { offset: "0%", "stop-color": "aqua" }), el("stop", { offset: "100%", "stop-color": "blue" }));
  svg.querySelector("defs").append(grad);

  const top = 80;
  const fila = alturaFila(datos.length, alto - top - 20);
  const grosor = Math.round(fila * 0.6);
  const k = escala(Math.max(0, ...datos.map((d) => d.valor)), ancho - margenIzq - margenDer);

  datos.forEach((d, i) => {
    const y = top + i * fila;
    const largo = d.valor * k;
    svg.append(el("text", { x: 20, y: y + grosor * 0.75, fill: "white", "font-size": 15, "font-family": "arial" }, d.etiqueta.slice(0, 18)));
    const barra = el("rect", {
      x: margenIzq, y, width: largo, height: grosor, fill: "url(#deg)", stroke: "blue",
      "data-id": d.id, class: "barra",
      ...(alAbrir ? { tabindex: 0, role: "button", "aria-label": `${d.etiqueta}: ${d.valor}` } : {}),
    });
    if (alAbrir) {
      barra.addEventListener("click", () => alAbrir(d));
      barra.addEventListener("keydown", (e) => {
        if (e.key === "Enter" || e.key === " ") { e.preventDefault(); alAbrir(d); }
      });
    }
    svg.append(barra, el("text", { x: margenIzq + largo + 10, y: y + grosor * 0.75, fill: "white", "font-size": 15, "font-family": "arial" }, String(d.valor)));
  });
}

// Guarda el SVG como archivo .svg válido (el demo usa type "text/plain").
function descargarSvg(svg, nombre = "grafico.svg") {
  const texto = new XMLSerializer().serializeToString(svg);
  const url = URL.createObjectURL(new Blob([texto], { type: "image/svg+xml;charset=utf-8" }));
  const enlace = document.createElement("a");
  enlace.href = url;
  enlace.download = nombre;
  enlace.click();
  setTimeout(() => URL.revokeObjectURL(url), 0);
}

// Detalle: en lugar de sessionStorage + redirección (el demo guarda IdCategoria/NombreCategoria),
// pasa el id por la URL para que el detalle se pueda recargar y compartir:
//   dibujarBarrasSvg(svg, datos, { alAbrir: (d) => { location.href = "GraficoColumnas3D?idCat=" + encodeURIComponent(d.id); } });
// y en la vista de detalle valida idCat en el servidor (entero) antes de llamar al SP.
