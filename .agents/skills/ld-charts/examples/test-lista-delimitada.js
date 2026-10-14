// Ejecuta: node test-lista-delimitada.js
const assert = require("assert");
const { decodificarEntidadesXml, parseLista, aDatosGrafico, escala, alturaFila } = require("./lista-delimitada.js");

// Formato real de uspCategoriaProductosStockPyCsv
const texto = "Categoria|Total Stock;300|200;str|int;Bebidas|559;Condimentos &amp; Salsas|507;Carnes|0";
const lista = parseLista(texto);
assert.deepStrictEqual(lista.cabeceras, ["Categoria", "Total Stock"]);
assert.deepStrictEqual(lista.anchos, ["300", "200"]);
assert.strictEqual(lista.filas.length, 3);  // &amp; no parte el registro en dos
assert.strictEqual(lista.filas[1][0], "Condimentos & Salsas");
assert.throws(() => parseLista(texto, { decodificarXml: false }), /Fila 2: 1 campos/);  // sin decodificar, "&amp;" parte el registro

// Vacío / NULL del SP (EjecutarComandoCadena lo normaliza a "")
assert.strictEqual(parseLista(""), null);
assert.deepStrictEqual(aDatosGrafico(null), []);

// Solo metadatos, sin filas de datos
assert.deepStrictEqual(parseLista("A|B;1|2;str|int;").filas, []);
assert.throws(() => parseLista("A|B;1|2"), /metadatos/);

// Fila con campos de menos (un "|" ausente) se rechaza con un error claro
assert.throws(() => parseLista("A|B;1|2;str|int;x"), /Fila 1: 1 campos/);

// Entidades XML que deja FOR XML PATH('')
assert.strictEqual(decodificarEntidadesXml("Condimentos &amp; Salsas &lt;x&gt;"), "Condimentos & Salsas <x>");
const datos = aDatosGrafico(parseLista("C|S;1|2;str|int;A &amp; B|10;X|abc;Y|-5"));
assert.deepStrictEqual(datos.map((d) => d.etiqueta), ["A & B", "X", "Y"]);
assert.deepStrictEqual(datos.map((d) => d.valor), [10, 0, 0]);  // no numérico o negativo -> 0

// Un solo nombre de columna (formato de uspProductoListar3Csv, filasMeta = 1)
const una = parseLista("Codigo|Nombre;1|Papa", { filasMeta: 1 });
assert.deepStrictEqual(una.filas, [["1", "Papa"]]);

// Escala sin dividir por cero
assert.strictEqual(escala(0, 500), 0);
assert.strictEqual(escala(100, 500), 5);
assert.ok(Number.isFinite(escala(0, 500)));

// Filas: ni demasiado grandes ni fuera del lienzo
assert.strictEqual(alturaFila(3, 500), 50);
assert.ok(alturaFila(20, 500) * 20 <= 500 + 1e-9 || alturaFila(20, 500) === 18);
assert.strictEqual(alturaFila(0, 500), 50);

console.log("OK: lista-delimitada");
