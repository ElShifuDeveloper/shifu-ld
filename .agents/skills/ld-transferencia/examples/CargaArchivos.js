// Carga de muchos archivos (imágenes) a una carpeta del servidor, con vista previa y progreso por viajes.
// Combina dos técnicas de tus demos:
//   - Archivos GRANDES: bloques (LD_SIZE_BLOQUE) con indicador I (primer bloque) / P (siguientes)  -> appDemo13
//   - Archivos PEQUEÑOS: agrupados en lotes (LD_SIZE_LOTE), un paquete de bytes por viaje        -> appDemo10 (en sentido inverso)
// Estilo de los demos: variables globales, async/await recursivo, respuestas "OK" / "Error - ...",
// <progress> y <span> de avance, CSRF en FormData. Requiere Paquetes.js (objeto Paquete).
// Elementos: lstArchivos (div de miniaturas), fupArchivos (input file multiple), txtCarpeta, btnGrabar,
// btnCancelar, progreso (<progress>), spnValida, spnTotalArchivos, divZona (zona de arrastre), {% csrf_token %}.

var items = [];                  // [{ file, nombre }]: nombre = nombre a guardar (único dentro de la tanda)
// Tamaños del protocolo: NO se escriben aquí. Salen de settings.LD_SIZE_BLOQUE y settings.LD_SIZE_LOTE del servidor, que la vista
// PantallaCarga entrega los límites del protocolo en campos ocultos; el máximo de archivos es obligatorio para no divergir del
// servidor. Los valores por defecto de bytes solo son un respaldo para los tamaños de los ejemplos.
var sizeBloque = Paquete.ParametroEntero(campoOculto("hdfSizeBloque"), 256 * 1024);   // appDemo13: bytes por bloque I/P
var sizeLote = Paquete.ParametroEntero(campoOculto("hdfSizeLote"), 512 * 1024);       // appDemo10: bytes de datos de un lote
var maxArchivosLote = Paquete.ParametroEntero(campoOculto("hdfMaxArchivosLote"), 0);
if (maxArchivosLote <= 0) throw new Error("PantallaCarga debe entregar hdfMaxArchivosLote desde settings.");
function campoOculto(id) { var e = document.getElementById(id); return e ? e.value : null; }
// Sin tope por defecto: los bloques permiten archivos de cualquier tamaño y el avance se ve viaje a viaje.
// Un límite solo existe si la especificación lo pide: ponlo aquí (bytes o cantidad) y en settings.LD_MAX_ARCHIVO.
var maxArchivo = 0;              // 0 = sin límite por archivo
var maxArchivos = 0;             // 0 = sin límite de cantidad por tanda
var maxTotalTanda = 0;           // 0 = sin límite de tamaño total por tanda
var cola = [];                   // viajes: { tipo: "lote" | "bloque", ... }
var cViajes = 0;
var nViajes = 0;
var carpeta = "";
var cancelado = false;
var urlsMiniaturas = [];
var reintento = false;           // true tras un error: Grabar continúa en el viaje que falló

window.onload = function () {
	// Arrastrar y soltar (appDemo13: lstArchivos.ondrop) y selector de archivos.
	divZona.ondragover = function (event) { event.preventDefault(); divZona.classList.add("activo"); }
	divZona.ondragleave = function () { divZona.classList.remove("activo"); }
	divZona.ondrop = function (event) {
		event.preventDefault();
		divZona.classList.remove("activo");
		agregarArchivos(event.dataTransfer.files);
	}
	fupArchivos.onchange = function () {
		agregarArchivos(this.files);
		this.value = "";
	}
	btnGrabar.onclick = grabarCarpeta;
	btnCancelar.onclick = function () { cancelado = true; }
	// Advierte al abandonar la página mientras haya una tanda sin guardar por completo.
	window.onbeforeunload = function () { if (items.length > 0 && !(nViajes > 0 && cViajes >= nViajes)) return "Hay imágenes sin guardar"; }
}

// Muestra un aviso con el estilo adecuado (LD.css): error, éxito o información. Texto vacío = lo oculta.
function mensaje(texto) {
	spnValida.textContent = texto;
	var tipo = /^Error|reintentar|Nombre de carpeta|No hay imágenes|Ocurrio/.test(texto) ? "error" : /^Se guardaron/.test(texto) ? "ok" : "info";
	spnValida.className = texto == "" ? "" : "ld-alerta " + tipo;
}

// Valida cada archivo (tipo y tamaño), le asigna un nombre único y crea su vista previa.
function agregarArchivos(lista) {
	var rechazados = [];
	for (var i = 0; i < lista.length; i++) {
		var file = lista[i];
		if (!file.type.startsWith("image/")) { rechazados.push(file.name + " (no es imagen)"); continue; }
		if (maxArchivo > 0 && file.size > maxArchivo) { rechazados.push(file.name + " (supera el límite por archivo)"); continue; }
		if (maxArchivos > 0 && items.length >= maxArchivos) { rechazados.push("Límite de la tanda alcanzado: no se agregaron los archivos restantes"); break; }
		if (maxTotalTanda > 0 && tamanoTotal() + file.size > maxTotalTanda) { rechazados.push(file.name + " (la tanda superaría el límite de tamaño)"); continue; }
		items.push({ file: file, nombre: nombreUnico(file.name) });
	}
	if (rechazados.length > 0) alert("No se agregaron:\n" + rechazados.join("\n"));
	dibujarMiniaturas();
}

function tamanoTotal() {
	var total = 0;
	items.forEach(function (it) { total += it.file.size; });
	return total;
}

// Dos archivos con el mismo nombre en la tanda: foto.jpg, foto (2).jpg, ...
function nombreUnico(nombre) {
	var usados = items.map(function (it) { return it.nombre.toLowerCase(); });
	if (usados.indexOf(nombre.toLowerCase()) < 0) return nombre;
	var punto = nombre.lastIndexOf(".");
	var base = punto > 0 ? nombre.substring(0, punto) : nombre;
	var ext = punto > 0 ? nombre.substring(punto) : "";
	var n = 2;
	while (usados.indexOf((base + " (" + n + ")" + ext).toLowerCase()) >= 0) n++;
	return base + " (" + n + ")" + ext;
}

// Vista previa con URL.createObjectURL (appDemo12 usa FileReader.readAsDataURL, que crea una cadena base64
// por imagen: con muchas imágenes consume mucha memoria). Se liberan las URLs al redibujar.
function dibujarMiniaturas() {
	urlsMiniaturas.forEach(URL.revokeObjectURL);
	urlsMiniaturas = [];
	lstArchivos.innerHTML = "";
	items.forEach(function (it, i) {
		var url = URL.createObjectURL(it.file);
		urlsMiniaturas.push(url);
		var div = document.createElement("div");
		div.className = "MarcoImagen2";
		var img = document.createElement("img");
		img.src = url;
		img.className = "Imagen";
		var nombre = document.createElement("div");
		nombre.textContent = it.nombre;                      // nombre del archivo del usuario: siempre como texto
		var quitar = document.createElement("input");
		quitar.type = "button";
		quitar.value = "Quitar";
		quitar.className = "Boton Secundario BotonSmall";
		quitar.onclick = function () { items.splice(i, 1); dibujarMiniaturas(); }
		div.append(img, nombre, quitar);
		lstArchivos.appendChild(div);
	});
	spnTotalArchivos.textContent = items.length;
}

// 1) Crea la carpeta; 2) arma los viajes; 3) los envía de uno en uno.
async function grabarCarpeta() {
	if (reintento) {                       // tras un error: sigue en el viaje que falló, sin volver a crear la carpeta
		reintento = false;
		cancelado = false;
		await procesarCola();
		return;
	}
	carpeta = txtCarpeta.value.trim();
	if (!/^[A-Za-z0-9_-]{1,60}$/.test(carpeta)) { mensaje("Nombre de carpeta: 1 a 60 letras, dígitos, - o _"); return; }
	if (items.length == 0) { mensaje("No hay imágenes en la tanda"); return; }
	mensaje("");
	var frm = new FormData();
	frm.append("Carpeta", carpeta);
	frm.append("csrfmiddlewaretoken", document.getElementsByName("csrfmiddlewaretoken")[0].value);
	var rptaHttp = await fetch("CrearCarpeta", { method: "POST", body: frm });
	if (!rptaHttp.ok) { mensaje("Ocurrio un error en el servidor"); return; }
	var rpta = await rptaHttp.text();
	if (rpta != "OK") { mensaje(rpta); return; }     // "Error - La carpeta ya existe", etc.
	prepararCola();
	cancelado = false;
	cViajes = 0;
	progreso.max = nViajes;
	progreso.value = 0;
	await procesarCola();
}

// Un solo recorrido en orden (Paquete.PlanificarViajes): los pequeños se acumulan en un lote mientras la suma sea <= sizeLote;
// el que no cabe abre el siguiente lote; un archivo mayor que sizeLote cierra el lote abierto, va por bloques I/P (appDemo13)
// y, al terminar su último bloque, el recorrido sigue con los demás. Los archivos no se reordenan.
function prepararCola() {
	cola = Paquete.PlanificarViajes(items.map(function (it, i) { return { id: i, size: it.file.size }; }), sizeLote, sizeBloque, maxArchivosLote)
		.map(function (v) {
			return v.tipo == "lote" ? { tipo: "lote", indices: v.ids }
				: { tipo: "bloque", indice: v.id, bloque: v.bloque, nBloques: v.nBloques, inicio: v.inicio };
		});
	nViajes = cola.length;
}

// Un viaje por llamada; avanza solo cuando el servidor responde "OK" (como enviarBloqueArchivo de appDemo13).
async function procesarCola() {
	if (cViajes >= nViajes) {
		mensaje("Se guardaron " + items.length + " imágenes en la carpeta " + carpeta);
		return;
	}
	if (cancelado) { mensaje("Cancelado en el viaje " + cViajes + "/" + nViajes); return; }
	var viaje = cola[cViajes];
	var frm = new FormData();
	frm.append("Carpeta", carpeta);
	frm.append("csrfmiddlewaretoken", document.getElementsByName("csrfmiddlewaretoken")[0].value);
	var url;
	if (viaje.tipo == "lote") {
		var texto = viaje.indices.map(function (i) { return items[i].nombre + "|" + items[i].file.size; }).join(";");
		frm.append("Blob", Paquete.Crear(texto, viaje.indices.map(function (i) { return items[i].file; })));
		url = "GrabarLote";
	} else {
		var it = items[viaje.indice];
		frm.append("Nombre", it.nombre);
		frm.append("Flag", viaje.bloque == 0 ? "I" : "P");
		frm.append("Blob", it.file.slice(viaje.bloque * sizeBloque, (viaje.bloque + 1) * sizeBloque));
		url = "GrabarBloque";
	}
	var rpta = "";
	try {
		var rptaHttp = await fetch(url, { method: "POST", body: frm });
		if (rptaHttp.ok) rpta = await rptaHttp.text();
	} catch (e) { rpta = "Error - Sin conexión"; }
	if (rpta == "OK") {
		cViajes++;
		progreso.value = cViajes;
		mensaje("Viaje: " + cViajes + "/" + nViajes);
		await procesarCola();
	} else {
		// Si falla un bloque P, se reintenta el archivo completo desde su primer bloque (I): reenviar un P que
		// el servidor ya anexó duplicaría bytes. Los lotes se pueden reenviar tal cual.
		if (viaje.tipo == "bloque") cViajes = viaje.inicio;
		mensaje((rpta != "" ? rpta : "Error") + ". Pulsa Grabar para reintentar desde el viaje " + (cViajes + 1));
		reintento = true;
	}
}
