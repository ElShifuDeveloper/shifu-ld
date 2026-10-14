// Mantenimiento con popup en el estilo base LD (adaptado de appDemo11).
// Depende de General.js: Gui, Popup, Validacion. Los controles se usan por su id global.

function tokenCsrf() {
	return document.getElementsByName("csrfmiddlewaretoken")[0].value;
}

async function postForm(url, campos) {
	var frm = new URLSearchParams(campos);
	frm.append("csrfmiddlewaretoken", tokenCsrf());
	var rptaHttp = await fetch(url, { method: "POST", body: frm });
	if (!rptaHttp.ok) return null;
	return await rptaHttp.text();
}

// Grabar/Eliminar devuelven "grilla_id": la grilla (3 filas de metadatos + datos, con ¬ y |) y el id tras "_".
// ObtenerListas devuelve "grilla_proveedores_categorias"; los combos son "id|nombre" separados por ¬.
function pintarGrilla(lista) {
	Gui.Grilla(lista, divProducto, "|", null, null, 20, 10, "¬", "", true);
}

window.onload = async function () {
	Popup.Resize(divPopupWindow, 30, 40);
	Popup.ConfigurarArrastre(divPopupContainer, divPopupWindow, divBarra);
	Validacion.ValidarNumerosEnlinea("E");
	Validacion.ValidarDecimalesEnlinea("D");

	var rptaHttp = await fetch("ObtenerListas");
	if (rptaHttp.ok) {
		var rpta = await rptaHttp.text();
		if (rpta == "") { alert("Ocurrio un error al cargar las listas"); return; }
		var listas = rpta.split("_");
		pintarGrilla(listas[0].split("¬"));
		Gui.Combo(listas[1].split("¬"), cboProveedor, "|", "Seleccione");
		Gui.Combo(listas[2].split("¬"), cboCategoria, "|", "Seleccione");
	} else alert("No se pudo cargar la pantalla (HTTP " + rptaHttp.status + ")");

	btnCerrar.onclick = btnCancelar.onclick = function () {
		divPopupContainer.style.display = "none";
	};

	btnGrabar.onclick = async function () {
		if (!Gui.ValidarControles("R", "L")) {
			spnValida.innerText = "Datos Son Requeridos";
			return;
		}
		spnValida.innerText = "";
		var data = Gui.ObtenerValoresControles("M", "|");
		var rpta = await postForm("GrabarProducto", { Data: data });
		if (rpta === null || rpta == "") { alert("Ocurrio un error al Grabar el Producto"); return; }
		var partes = rpta.split("_");
		divPopupContainer.style.display = "none";
		pintarGrilla(partes[0].split("¬"));
		alert("Se grabo el producto con id: " + partes[1]);
	};
};

// Funciones que invoca la grilla mantenible: deben existir como globales.
function nuevoRegistro() {
	divPopupContainer.style.display = "inline";
	Gui.LimpiarControles("M");
}

async function editarRegistro(fila, id, btn) {
	divPopupContainer.style.display = "inline";
	Gui.LimpiarControles("M");
	var rptaHttp = await fetch("ObtenerProductoPorId?id=" + encodeURIComponent(id));
	if (!rptaHttp.ok) { alert("No se pudo obtener el producto"); return; }
	var rpta = await rptaHttp.text();
	if (rpta == "") { alert("Producto no encontrado"); return; }
	Gui.MostrarValoresControles("M", rpta.split("|"));
}

async function eliminarRegistro(id, btn) {
	if (!confirm("Seguro de eliminar al Producto: " + id)) return;
	var rpta = await postForm("EliminarProductoPorId", { id: id });
	if (rpta === null || rpta == "") { alert("Ocurrio un error al Eliminar el Producto"); return; }
	var partes = rpta.split("_");
	pintarGrilla(partes[0].split("¬"));
	alert("Se elimino el producto con id: " + partes[1]);
}

function cambiarPagina(indice) { }
function seleccionarFila(idDiv, fila, id) { }
