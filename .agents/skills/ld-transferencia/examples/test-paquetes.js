// Ejecuta: node test-paquetes.js  (Node >= 18: trae Blob, TextEncoder y TextDecoder)
const assert = require("assert");
const { Paquete } = require("./Paquetes.js");

(async () => {
  const maxArchivosLote = 200;
  // ida y vuelta con tildes y archivos de distinto tamaño (incluido uno vacío)
  const archivos = [new Blob([new Uint8Array([1, 2, 3])]), new Blob([]), new Blob([new Uint8Array(1000).fill(7)])];
  const texto = "ñandú.jpg|3;vacío.png|0;grande.gif|1000";
  const paquete = Paquete.Crear(texto, archivos);
  const { registros, blobs } = await Paquete.Leer(paquete);
  assert.deepStrictEqual(registros, [["ñandú.jpg", "3"], ["vacío.png", "0"], ["grande.gif", "1000"]]);
  assert.deepStrictEqual(blobs.map((b) => b.size), [3, 0, 1000]);
  assert.deepStrictEqual(Array.from(new Uint8Array(await blobs[0].arrayBuffer())), [1, 2, 3]);

  // la cabecera cuenta bytes UTF-8 (4 para "ñ|1"), no caracteres (3)
  const p2 = Paquete.Crear("ñ|1", [new Blob([new Uint8Array([65])])]);
  const cab = new Uint8Array(await p2.slice(0, 2).arrayBuffer());
  assert.strictEqual(cab[0] * 256 + cab[1], 4);

  // texto largo: el primer byte de la cabecera deja de ser 0 (base 256)
  const largo = "a|1;".repeat(100) + "z|1";
  const p3 = Paquete.Crear(largo, Array(101).fill(new Blob([new Uint8Array([1])])));
  const c3 = new Uint8Array(await p3.slice(0, 2).arrayBuffer());
  assert.ok(c3[0] > 0);
  assert.strictEqual((await Paquete.Leer(p3)).registros.length, 101);

  // paquetes inválidos
  const bueno = Paquete.Crear("a|3", [new Blob([new Uint8Array([1, 2, 3])])]);
  const malos = [new Blob([]), new Blob([new Uint8Array([0])]), bueno.slice(0, bueno.size - 1),
                 new Blob([bueno, new Uint8Array([9])]), Paquete.Crear("a|xx", [new Blob([])])];
  for (const malo of malos) await assert.rejects(() => Paquete.Leer(malo), Error);

  // el texto vacío es un paquete válido sin archivos
  assert.deepStrictEqual((await Paquete.Leer(Paquete.Crear("", []))).registros, []);

  // agrupar por tamaño (mismo caso que modPaquetes.py)
  const items = [["a", 40], ["b", 40], ["c", 40], ["d", 150], ["e", 10]].map(([id, size]) => ({ id, size }));
  assert.deepStrictEqual(Paquete.AgruparPorTamano(items, 100, maxArchivosLote), [["a", "b"], ["c"], ["d"], ["e"]]);
  assert.deepStrictEqual(Paquete.AgruparPorTamano([], 100, maxArchivosLote), []);
  assert.deepStrictEqual(
    Paquete.AgruparPorTamano(Array.from({ length: 5 }, (_, id) => ({ id, size: 0 })), 100, 2).map((v) => v.length),
    [2, 2, 1]
  );
  assert.deepStrictEqual(
    Paquete.AgruparPorTamano(Array.from({ length: 201 }, (_, id) => ({ id, size: 0 })), 100, maxArchivosLote).map((v) => v.length),
    [200, 1]
  );
  assert.throws(() => Paquete.AgruparPorTamano([], 100, 0), RangeError);

  // planificar viajes: un recorrido, en orden; pequeños en lote hasta 100; el que no cabe abre el siguiente lote;
  // el gigante cierra el lote abierto, va por bloques (I,P,P) y luego el flujo continúa con un lote nuevo
  const plan = Paquete.PlanificarViajes([["a", 40], ["b", 50], ["c", 30], ["G", 250], ["d", 60], ["e", 40], ["f", 10]]
    .map(([id, size]) => ({ id, size })), 100, 100, maxArchivosLote);
  assert.deepStrictEqual(plan.map((v) => (v.tipo == "lote" ? v.ids.join("") : v.id + v.bloque)), ["ab", "c", "G0", "G1", "G2", "de", "f"]);
  assert.deepStrictEqual(plan.filter((v) => v.tipo == "bloque").map((v) => [v.nBloques, v.inicio]), [[3, 2], [3, 2], [3, 2]]);
  assert.deepStrictEqual(Paquete.PlanificarViajes([{ id: "x", size: 100 }, { id: "y", size: 1 }], 100, 100, maxArchivosLote).map((v) => v.ids), [["x"], ["y"]]);
  assert.deepStrictEqual(Paquete.PlanificarViajes([{ id: "z", size: 0 }], 100, 100, maxArchivosLote), [{ tipo: "lote", ids: ["z"] }]);
  assert.deepStrictEqual(Paquete.PlanificarViajes([], 100, 100, maxArchivosLote), []);
  assert.deepStrictEqual(
    Paquete.PlanificarViajes(Array.from({ length: 5 }, (_, id) => ({ id, size: 1 })), 1000, 100, 2).map((v) => v.ids.length),
    [2, 2, 1]
  );
  assert.deepStrictEqual(
    Paquete.PlanificarViajes(Array.from({ length: 201 }, (_, id) => ({ id, size: 1 })), 1000, 100, maxArchivosLote).map((v) => v.ids.length),
    [200, 1]
  );
  assert.throws(() => Paquete.PlanificarViajes([], 100, 100, 0), RangeError);

  // el MISMO planificador sirve para la descarga (técnica 2): lote -> ObtenerPaquete, bloque -> ObtenerBloque por índice.
  // Todos pequeños: UN solo viaje (pocos envíos); uno grande: tantos viajes como bloques, en el orden de la lista.
  const planBaja = Paquete.PlanificarViajes([["a", 40], ["b", 50]].map(([id, size]) => ({ id, size })), 100, 100, maxArchivosLote);
  assert.deepStrictEqual(planBaja.map((v) => v.tipo), ["lote"]);
  const planBajaMixto = Paquete.PlanificarViajes([["x", 10], ["G", 250], ["y", 20]].map(([id, size]) => ({ id, size })), 100, 100, maxArchivosLote);
  assert.deepStrictEqual(planBajaMixto.map((v) => (v.tipo == "lote" ? "L" + v.ids.join("") : "B" + v.id + v.bloque)),
    ["Lx", "BG0", "BG1", "BG2", "Ly"]);

  // parámetros que entrega settings (campos ocultos): válido, inválido y ausente
  assert.deepStrictEqual(["524288", " 262144 ", "abc", "0", "-5", "1.5", "", null, undefined, "12px"].map((v) => Paquete.ParametroEntero(v, 99)),
    [524288, 262144, 99, 99, 99, 99, 99, 99, 99, 99]);

  // cantidad de bloques: 0, 1, N-1, N, N+1, 2N, 2N+1 con N = 100 KiB
  const N = 100 * 1024;
  assert.deepStrictEqual([0, 1, N - 1, N, N + 1, 2 * N, 2 * N + 1].map((s) => Paquete.CantidadBloques(s, N)), [0, 1, 1, 1, 2, 2, 3]);
  console.log("OK: Paquetes.js");
})().catch((e) => { console.error(e); process.exit(1); });
