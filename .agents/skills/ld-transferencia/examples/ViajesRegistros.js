// Registros por viajes (appDemo26_2 y appDemo28): sin JSON, sin cursores; cadenas con ";" entre registros y "|"
// entre campos, un viaje por bloque de N registros, <progress> y contadores.
// Elementos: progreso, spnRegistros, spnBloques, spnProgresoRegistros, spnProgresoBloques, spnMensaje, divCubso.

// ---- A) CONSULTAR muchos registros por bloques (appDemo26_2: 907 440 filas en viajes de 10 000)
var registrosBloque = 10000;
var indiceBloque = 0;
var totalBloques = 0;
var totalRegistros = 0;
var cRegistros = 0;
var listaTabla = [];
var horaInicio = null;

async function consultarPorBloques() {
	horaInicio = new Date();
	var rptaHttp = await fetch("ContarRegistros");                        // escalar: total de filas
	if (!rptaHttp.ok) return;
	var rpta = await rptaHttp.text();
	if (rpta == "") return;
	totalRegistros = +rpta;
	totalBloques = Math.floor(totalRegistros / registrosBloque);
	if (totalRegistros % registrosBloque > 0) totalBloques++;
	progreso.max = totalBloques;
	spnRegistros.textContent = "Total de Registros: " + totalRegistros;
	spnBloques.textContent = "Total de Viajes: " + totalBloques;
	// Las tres filas de metadatos de Gui.Grilla: nombres, anchos y tipos
	listaTabla = ["Id|Codigo|Descripcion|Precio", "100|200|800|100", "int|str|str|int"];
	indiceBloque = 0;
	cRegistros = 0;
	await obtenerBloque();
}

async function obtenerBloque() {
	var url = "ObtenerBloqueRegistros?indice=" + (indiceBloque + 1) + "&registros=" + registrosBloque;
	var rptaHttp = await fetch(url);
	if (!rptaHttp.ok) return;
	var rpta = await rptaHttp.text();
	if (rpta == "") return;
	// uspCubsoPaginarCsvPy antepone ";" a cada registro: el primer elemento del split queda vacío y se descarta.
	var lista = rpta.split(";").filter(function (fila) { return fila != ""; });
	lista.forEach(function (fila) { listaTabla.push(fila); });
	cRegistros += lista.length;
	indiceBloque++;
	progreso.value = indiceBloque;
	spnProgresoRegistros.textContent = "Registros: " + cRegistros + "/" + totalRegistros;
	spnProgresoBloques.textContent = "Bloques: " + indiceBloque + "/" + totalBloques;
	if (indiceBloque < totalBloques) await obtenerBloque();
	else {
		// La grilla se pinta una sola vez al final: pintarla en cada viaje vuelve lento un volumen grande.
		Gui.Grilla(listaTabla, divCubso, "|", null, null, 20, 10, ";", "Cubso", false, true, "", false, true, false, null, false, null);
		spnMensaje.textContent = "Tiempo proceso en: " + (new Date() - horaInicio) + " milisegundos";
	}
}

// ---- B) GRABAR muchos registros por viajes (appDemo28: carga masiva de un CSV a una tabla)
// lista[0] = cabecera con los nombres de columna; datos desde la fila 1 (en appDemo28 hay 2 filas de metadatos
// insertadas para la grilla: aquí `lista` ya viene sin ellas).
var lista = [];
var tabla = "";
var totalViajes = 0;
var contadorViajes = 0;

async function grabarPorViajes(registrosPorViaje) {
	var frm = new FormData();
	frm.append("tabla", tabla);
	frm.append("campos", lista[0]);
	frm.append("csrfmiddlewaretoken", document.getElementsByName("csrfmiddlewaretoken")[0].value);
	var rptaHttp = await fetch("ValidarTablaCampos", { method: "POST", body: frm });   // "" si todo coincide
	if (!rptaHttp.ok) return;
	var rptaTexto = await rptaHttp.text();
	if (rptaTexto != "") { alert(rptaTexto); return; }                                  // "Error - No existen los campos: ..."
	totalViajes = Math.ceil((lista.length - 1) / registrosPorViaje);
	contadorViajes = 0;
	progreso.max = totalViajes;
	await grabarViaje(registrosPorViaje);
}

async function grabarViaje(registrosPorViaje) {
	var inicio = 1 + contadorViajes * registrosPorViaje;
	var bloque = [lista[0]].concat(lista.slice(inicio, inicio + registrosPorViaje));    // cabecera + N registros
	var frm = new FormData();
	frm.append("tabla", tabla);
	frm.append("data", bloque.join(";"));
	frm.append("csrfmiddlewaretoken", document.getElementsByName("csrfmiddlewaretoken")[0].value);
	var rptaHttp = await fetch("GrabarBloqueRegistros", { method: "POST", body: frm });
	if (!rptaHttp.ok) return;
	var rpta = await rptaHttp.text();
	if (rpta != "OK") { alert(rpta); return; }                                          // se detiene en el viaje que falló
	contadorViajes++;
	progreso.value = contadorViajes;
	spnProgresoBloques.textContent = "Viajes: " + contadorViajes + "/" + totalViajes;
	if (contadorViajes < totalViajes) await grabarViaje(registrosPorViaje);
	else spnMensaje.textContent = "La carga concluyó: " + (lista.length - 1) + " registros";
}
