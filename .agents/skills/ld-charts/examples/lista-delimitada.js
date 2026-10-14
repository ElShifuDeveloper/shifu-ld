// Lectura de las listas delimitadas de los SP "...PyCsv" (adaptado de appDemo19-25) y utilidades
// de escala. Formato: filas separadas por `;`, campos por `|`; las 3 primeras filas son
// nombres, anchos y tipos de columna y los datos empiezan en la cuarta (ver ld-crud).
// Sin dependencias del DOM: se puede probar con Node.

const ENTIDADES_XML = { "&amp;": "&", "&lt;": "<", "&gt;": ">", "&quot;": '"', "&apos;": "'" };

// Los SP que arman texto con FOR XML PATH('') entregan &amp; &lt; &gt;. La entidad termina en `;`,
// el separador de registros de los SP "...PyCsv": "Condimentos &amp; Salsas" se partiría en dos
// registros. Por eso parseLista decodifica el texto completo ANTES de separarlo. La solución de
// fondo es corregir el SP (FOR XML PATH(''), TYPE).value('.', 'varchar(max)').
function decodificarEntidadesXml(texto) {
  return String(texto).replace(/&(amp|lt|gt|quot|apos);/g, (m) => ENTIDADES_XML[m]);
}

// Devuelve { cabeceras, anchos, tipos, filas } o null si no hay datos (texto vacío/NULL del SP).
// filasMeta = 3 para los SP con nombres+anchos+tipos; 1 para los que solo traen nombres.
function parseLista(texto, { sepReg = ";", sepCampo = "|", filasMeta = 3, decodificarXml = true } = {}) {
  if (typeof texto !== "string" || texto.trim() === "") return null;
  const registros = (decodificarXml ? decodificarEntidadesXml(texto) : texto).split(sepReg);
  if (registros.length < filasMeta) throw new Error("Lista sin las filas de metadatos esperadas");
  const cabeceras = registros[0].split(sepCampo);
  const anchos = filasMeta >= 2 ? registros[1].split(sepCampo) : [];
  const tipos = filasMeta >= 3 ? registros[2].split(sepCampo) : [];
  // Se ignoran los registros totalmente vacíos (p. ej. un `;` final), no las filas con campos vacíos.
  const filas = registros.slice(filasMeta).filter((r) => r !== "").map((registro, i) => {
    const campos = registro.split(sepCampo);
    if (campos.length !== cabeceras.length) {
      throw new Error(`Fila ${i + 1}: ${campos.length} campos, se esperaban ${cabeceras.length}`);
    }
    return campos;
  });
  return { cabeceras, anchos, tipos, filas };
}

// Convierte la lista en [{ etiqueta, valor }] para graficar. `valor` inválido o negativo cuenta como 0.
function aDatosGrafico(lista, { colEtiqueta = 0, colValor = 1 } = {}) {
  if (!lista) return [];
  return lista.filas.map((campos) => {
    const n = Number(campos[colValor]);
    return {
      id: campos[0],
      etiqueta: campos[colEtiqueta],
      valor: Number.isFinite(n) && n > 0 ? n : 0,
    };
  });
}

// Factor píxeles/unidad. El demo divide por el máximo sin comprobarlo: con todos los valores en 0
// (o sin filas) da Infinity/NaN y la gráfica sale en blanco o sin barras.
function escala(valorMaximo, espacioPx) {
  return valorMaximo > 0 ? espacioPx / valorMaximo : 0;
}

// Reparte N barras en el alto disponible sin salirse del lienzo (los demos fijan 50 px por fila
// y desbordan a partir de ~10 categorías en un lienzo de 600 px).
function alturaFila(n, altoDisponible, maxFila = 50, minFila = 18) {
  if (n <= 0) return maxFila;
  return Math.max(minFila, Math.min(maxFila, altoDisponible / n));
}

if (typeof module !== "undefined") {
  module.exports = { decodificarEntidadesXml, parseLista, aDatosGrafico, escala, alturaFila };
}
