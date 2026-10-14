// Barras horizontales 2D en <canvas> (patrón de appDemo19), con las protecciones que los demos no
// tienen: datos vacíos, máximo 0, muchas filas y texto decodificado. Requiere lista-delimitada.js.
// HTML: <canvas id="canvas" width="1000" height="600" role="img" aria-label="Stock por categoría">
// junto a un div con Gui.Grilla(...) con los mismos datos, que sirve de alternativa accesible.

function dibujarBarrasCanvas(canvas, datos, { titulo = "", margenIzq = 150, margenDer = 100 } = {}) {
  const ctx = canvas.getContext("2d");
  const { width: ancho, height: alto } = canvas;
  ctx.fillStyle = "black";
  ctx.fillRect(0, 0, ancho, alto);
  ctx.fillStyle = "yellow";
  ctx.font = "32px Arial";
  ctx.fillText(titulo, 40, 50);

  if (datos.length === 0) {
    ctx.fillStyle = "white";
    ctx.font = "20px Arial";
    ctx.fillText("Sin datos para mostrar", 40, 110);
    return;
  }
  const top = 80;
  const fila = alturaFila(datos.length, alto - top - 20);
  const grosor = Math.round(fila * 0.6);
  const k = escala(Math.max(...datos.map((d) => d.valor)), ancho - margenIzq - margenDer);

  datos.forEach((d, i) => {
    const y = top + i * fila;
    const largo = d.valor * k;
    ctx.fillStyle = "white";
    ctx.font = "15px Arial";
    ctx.fillText(d.etiqueta.slice(0, 18), 20, y + grosor * 0.75);
    const grad = ctx.createLinearGradient(margenIzq, 0, margenIzq + Math.max(largo, 1), 0);
    grad.addColorStop(0, "aqua");
    grad.addColorStop(1, "blue");
    ctx.fillStyle = grad;
    ctx.fillRect(margenIzq, y, largo, grosor);
    ctx.fillStyle = "white";
    ctx.fillText(String(d.valor), margenIzq + largo + 10, y + grosor * 0.75);
  });
}

// Descarga PNG. toDataURL falla (SecurityError) si el lienzo se "contaminó" con imágenes de otro origen.
function descargarPng(canvas, nombre = "grafico.png") {
  const enlace = document.createElement("a");
  enlace.href = canvas.toDataURL("image/png");
  enlace.download = nombre;
  enlace.click();
}

// Uso (en window.onload, tras fetch):
//   const lista = parseLista(await respuesta.text());            // 3 filas de metadatos
//   dibujarBarrasCanvas(canvas, aDatosGrafico(lista), { titulo: "Stock por categoría" });
