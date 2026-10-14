// Galería de imágenes descargadas por viajes (appDemo10_2 / appDemo09 / appDemo14 + la extensión de descarga simétrica).
// MISMA regla de decisión que la subida (CargaArchivos.js): los archivos de sizeLote o menos viajan agrupados en paquetes
// de bytes (POST ObtenerPaquete) y los mayores se piden por bloques (GET ObtenerBloque, uno por viaje) que el cliente
// acumula y une con new Blob(partes). El plan sale de Paquete.PlanificarViajes: un solo recorrido, en orden.
// Los demos solo bajaban iconos y miniaturas (todo cabía en lotes de 100 KB); la parte de bloques es el inverso exacto
// de appDemo13 (allí el cliente corta con slice; aquí recibe los trozos y los une). Requiere Paquetes.js.
// Elementos: divGaleria, progreso (<progress>), spnMensaje, txtCarpeta, campos ocultos hdfSizeLote, hdfSizeBloque
// y hdfMaxArchivosLote
// (los entrega PantallaConsulta desde settings) y {% csrf_token %}.

var items = [];                  // [{ id: nombre, size }] de ListarCodigosSize
// Límites del protocolo: la vista PantallaConsulta los entrega desde settings en campos ocultos, igual que PantallaCarga.
// Los valores por defecto de bytes solo respaldan los tamaños del ejemplo; el máximo de archivos es obligatorio.
var sizeLote = Paquete.ParametroEntero(campoOculto("hdfSizeLote"), 512 * 1024);
var sizeBloque = Paquete.ParametroEntero(campoOculto("hdfSizeBloque"), 256 * 1024);
var maxArchivosLote = Paquete.ParametroEntero(campoOculto("hdfMaxArchivosLote"), 0);
if (maxArchivosLote <= 0) throw new Error("PantallaConsulta debe entregar hdfMaxArchivosLote desde settings.");
function campoOculto(id) { var e = document.getElementById(id); return e ? e.value : null; }
var cola = [];                   // viajes: { tipo: "lote" | "bloque", ... } (misma forma que en la subida)
var cViajes = 0;
var nViajes = 0;
var partes = {};                 // nombre -> [Blob, ...] de los bloques recibidos de un archivo grande
var urlsGaleria = [];
var cImagenes = 0;
var nImagenes = 0;
var carpetaActual = "";
var fallo = false;               // true tras un error: consultar la misma carpeta continúa en el viaje que falló

async function consultarCarpeta(carpeta) {
	if (fallo && carpeta == carpetaActual) {        // reintento: la descarga es idempotente, sigue donde quedó
		fallo = false;
		await procesarCola();
		return;
	}
	carpetaActual = carpeta;
	urlsGaleria.forEach(URL.revokeObjectURL);
	urlsGaleria = [];
	divGaleria.innerHTML = "";
	partes = {};
	cImagenes = 0;
	fallo = false;
	// "nombre|size;nombre|size" (appDemo10: ListarCodigosSizeImg)
	var rptaHttp;
	try {
		rptaHttp = await fetch("ListarCodigosSize?Carpeta=" + encodeURIComponent(carpeta));
	} catch (e) { spnMensaje.textContent = "Error - Sin conexión"; return; }
	if (!rptaHttp.ok) { spnMensaje.textContent = "Error - Ocurrio un error en el servidor"; return; }
	var data = await rptaHttp.text();
	if (data.indexOf("Error - ") == 0) { spnMensaje.textContent = data; return; }
	if (data == "") { spnMensaje.textContent = "La carpeta no tiene imágenes"; return; }
	items = data.split(";").map(function (r) {
		var c = r.split("|");
		return { id: c[0], size: +c[1] };
	});
	nImagenes = items.length;
	// Un solo recorrido, en orden: pequeños en lotes, grandes por bloques (igual que prepararCola en la subida).
	cola = Paquete.PlanificarViajes(items, sizeLote, sizeBloque, maxArchivosLote);
	nViajes = cola.length;
	cViajes = 0;
	progreso.max = nViajes;
	progreso.value = 0;
	await procesarCola();
}

// Un viaje por llamada; avanza solo con una respuesta válida. Ante un fallo se detiene y deja reintentar:
// leer el mismo lote o bloque devuelve los mismos bytes, así que el viaje fallido se reenvía tal cual.
async function procesarCola() {
	if (cViajes >= nViajes) {
		spnMensaje.textContent = nImagenes + " imágenes en la carpeta " + carpetaActual;
		return;
	}
	var viaje = cola[cViajes];
	var error = viaje.tipo == "lote" ? await obtenerLote(viaje) : await obtenerBloque(viaje);
	if (error != null) {
		fallo = true;
		spnMensaje.textContent = error + ". Vuelve a consultar para reintentar desde el viaje " + (cViajes + 1);
		return;
	}
	cViajes++;
	progreso.value = cViajes;
	spnMensaje.textContent = "Viaje " + cViajes + "/" + nViajes + " · " + cImagenes + " de " + nImagenes + " imágenes";
	await procesarCola();
}

// Lote de archivos pequeños: POST ObtenerPaquete -> UN paquete de bytes -> Paquete.Leer -> una imagen por registro.
async function obtenerLote(viaje) {
	var frm = new URLSearchParams();                      // appDemo10_2 usa URLSearchParams para este POST
	frm.append("Carpeta", carpetaActual);
	frm.append("Nombres", viaje.ids.join("|"));
	frm.append("csrfmiddlewaretoken", document.getElementsByName("csrfmiddlewaretoken")[0].value);
	var rptaHttp;
	try {
		rptaHttp = await fetch("ObtenerPaquete", {
			method: "POST",
			headers: { "Content-Type": "application/x-www-form-urlencoded" },
			body: frm
		});
	} catch (e) { return "Error - Sin conexión"; }
	if (!rptaHttp.ok) return "Error - Ocurrio un error en el servidor";
	if ((rptaHttp.headers.get("Content-Type") || "").indexOf("octet-stream") < 0) return await rptaHttp.text();   // "Error - ..." de dominio
	var paquete;
	try { paquete = await Paquete.Leer(await rptaHttp.blob()); }
	catch (e) { return e.message; }                                  // paquete truncado: no se muestran imágenes a medias
	paquete.registros.forEach(function (campos, i) { dibujar(paquete.blobs[i], campos[0]); });
	cImagenes += paquete.registros.length;
	return null;
}

// Bloque de un archivo grande: GET ObtenerBloque?Indice=n -> bytes; se acumulan y en el último se unen y se
// comprueba el tamaño anunciado. Es el inverso de enviarBloqueArchivo (appDemo13): allí el cliente corta con
// slice(file, ...); aquí los trozos llegan por viaje y new Blob(partes) los une sin copias intermedias.
async function obtenerBloque(viaje) {
	var url = "ObtenerBloque?Carpeta=" + encodeURIComponent(carpetaActual) +
		"&Nombre=" + encodeURIComponent(viaje.id) + "&Indice=" + viaje.bloque;
	var rptaHttp;
	try { rptaHttp = await fetch(url); } catch (e) { return "Error - Sin conexión"; }
	if (!rptaHttp.ok) return "Error - Ocurrio un error en el servidor";
	if ((rptaHttp.headers.get("Content-Type") || "").indexOf("octet-stream") < 0) return await rptaHttp.text();   // "Error - ..." de dominio
	if (partes[viaje.id] == null) partes[viaje.id] = [];
	partes[viaje.id].push(await rptaHttp.blob());
	if (viaje.bloque < viaje.nBloques - 1) return null;    // faltan bloques: el archivo aún no se puede mostrar
	var completo = new Blob(partes[viaje.id], { type: "image/jpeg" });      // el tipo real lo valida el servidor al subir
	delete partes[viaje.id];
	var esperado = items.filter(function (it) { return it.id == viaje.id; })[0];
	if (esperado != null && completo.size != esperado.size) return "Error - Descarga incompleta de " + viaje.id;
	dibujar(completo, viaje.id);
	cImagenes++;
	return null;
}

function dibujar(blob, nombre) {
	var url = URL.createObjectURL(blob);
	urlsGaleria.push(url);
	var div = document.createElement("div");
	div.className = "MarcoImagen2";
	var img = document.createElement("img");
	img.src = url;
	img.className = "Imagen";
	img.loading = "lazy";
	var titulo = document.createElement("div");
	titulo.textContent = nombre;                    // textContent: el nombre es dato del usuario
	div.append(img, titulo);
	divGaleria.appendChild(div);
}
