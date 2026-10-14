var Gui = (function () {
    function Gui() {
    }
	
	Gui.Combo = function (lista, cbo, sepCampo, primerItem) {
        sepCampo = (sepCampo == null ? "|" : sepCampo);
        primerItem = (primerItem == null ? "" : primerItem);
        var html = "";        
        if (primerItem != "") {
            html += "<option value=''>";
            html += primerItem;
            html += "</option>";
        }
        var nRegistros = lista.length;
        var campos = [];
        for (var i = 0; i < nRegistros; i++) {
            campos = lista[i].split(sepCampo);
            html += "<option value='";
            html += campos[0];
            html += "'>";
            html += campos[1];
            html += "</option>";
        }
        cbo.innerHTML = html;
    }
	
    Gui.Grilla = function (lista, div, sepCampo, colOcultar, listasCombos,
        registrosPagina, paginasBloque, sepRegistro, nombreReporte,
        esMantenible, esImprimible, controlador, tieneBotones, tieneFiltro,
        tieneNuevo, subtotales, mover, botones) {
        sepCampo = (sepCampo == null ? "|" : sepCampo);
        colOcultar = (colOcultar == null ? -1 : colOcultar);
        listasCombos = (listasCombos == null ? [] : listasCombos);
        registrosPagina = (registrosPagina == null ? 20 : registrosPagina);
        paginasBloque = (paginasBloque == null ? 10 : paginasBloque);
        sepRegistro = (sepRegistro == null ? "¬" : sepRegistro);
        nombreReporte = (nombreReporte == null ? "" : nombreReporte);
        esMantenible = (esMantenible == null ? false : esMantenible);
        esImprimible = (esImprimible == null ? false : esImprimible);
		tieneBotones = (tieneBotones == null ? true : tieneBotones);
        tieneFiltro = (tieneFiltro == null ? true : tieneFiltro);
        tieneNuevo = (tieneNuevo == null ? true : tieneNuevo);
        subtotales = (subtotales == null ? [] : subtotales);
        mover = (mover == null ? true : mover);
		botones = (botones == null ? [] : botones);
		var nBotones = botones.length;
		
        var totales = [];
        var id = div.id;
        var nRegistros = lista.length;
        //Variables para Paginar
        var indicePagina = 0;
        var indiceBloque = 0;
        //Variables para Ordenar
        var tipoOrden = 0; //Ascendente por defecto;
        var colOrden = 0; //Primera Columna;

        //Variables para convertir Matriz en Texto
        var cabeceras = [];
        var anchos = [];
        var tipos = [];
        var archivoExportar = "";

        if (nRegistros > 0) {
            var matriz = [];
            var indicesCombos = [];
            cabeceras = lista[0].split(sepCampo);
            anchos = lista[1].split(sepCampo);
            tipos = lista[2].split(sepCampo);
            var nCampos = cabeceras.length;
            var filaSel = null;
            
            obtenerIndicesCombos();
            crearTabla();
            crearMatriz();
            mostrarRegistros();
            configurarEventos();
            configurarMover();

            function obtenerIndicesCombos() {
                for (var j = 0; j < nCampos; j++) {
                    if (anchos[j].startsWith("C")) {
                        indicesCombos.push(j);
                        anchos[j] = anchos[j].substring(1, anchos[j].length);
                    }
                }
            }

            function crearTabla() {
                var html = "";
                html += "<div style='font-weight:bold;float:left'>Total de Registros: ";
                html += "<span id='spnTotal";
                html += div.id;
                html += "'></span>";
				html += "</div><br/>";
				if(tieneBotones)
				{
					html += "<img id='imgNuevoFiltro";
					html += div.id;
					html += "' src='";
					html += hdfRaiz.value;
					html += "Images/Icons/NuevoFiltro.png' class='Icono NoImprimir' title='Nuevo Filtro'>";                
					html += "<img id='imgQuitarOrden";
					html += div.id;
					html += "' src='";
					html += hdfRaiz.value;
					html += "Images/Icons/QuitarOrden.png' class='Icono NoImprimir' title='Quitar Filtros'>";
					html += "<img id='imgExportarTexto";
					html += div.id;
					html += "' src='";
					html += hdfRaiz.value;
					html += "Images/Icons/ExportarTxt.png' class='Icono NoImprimir' title='Exportar a Texto'>";
					html += "<img id='imgExportarExcel";
					html += div.id;
					html += "' src='";
					html += hdfRaiz.value;
					html += "Images/Icons/ExportarExcel.png' class='Icono NoImprimir' title='Exportar a Excel'>";
					html += "<img id='imgExportarWord";
					html += div.id;
					html += "' src='";
					html += hdfRaiz.value;
					html += "Images/Icons/ExportarWord.png' class='Icono NoImprimir' title='Exportar a Word'>";
					html += "<img id='imgExportarPdf";
					html += div.id;
					html += "' src='";
					html += hdfRaiz.value;
					html += "Images/Icons/ExportarPdf.png' class='Icono NoImprimir' title='Exportar a Pdf'>";					
				}
                if (esImprimible) {
                    html += "<img id='imgImprimir";
                    html += div.id;
                    html += "' src='";
                    html += hdfRaiz.value;
                    html += "Images/Icons/Imprimir.png' class='Icono NoImprimir' title='Imprimir Tabla'>";
                }
                html += "</div>";
                html += "<table>";
                html += "<thead>";
                html += "<tr class='FilaCabecera'>";
                for (var j = 0; j < nCampos; j++) {
                    if (colOcultar == -1 || (colOcultar > -1 && j != colOcultar)){
                        html += "<th style='width:";
                        html += anchos[j];
                        html += "px'>";
                        html += "<span class='Orden "
                        html += div.id;
                        html += "' data-col='";
                        html += j;
                        html += "'>";
                        html += cabeceras[j];
                        html += "</span>";
                        html += "<span class='SimbOrden ";
                        html += div.id;
                        html += "'></span>";
                        if (tieneFiltro) {
                            html += "<br/>";
                            if (indicesCombos.indexOf(j) > -1) {
                                html += "<select style='width:90%' class='";
                                html += div.id;
                                html += "Cab Cbo'></select>";
                            }
                            else {
                                html += "<input type='text' style='width:90%' class='";
                                html += div.id;
                                html += "Cab Txt'>";
                            }
                        }
                        html += "</th>";
                    }
                }
				if (nBotones > 0) {
					for (var j = 0; j < nBotones; j++) {
						html += "<th style='width:80px'>";
						html += botones[j].cabecera;
						html += "</th>";
					}
				}
                if (esMantenible) {
                    html += "<th style='width:70px' class='Centro'>";
                    if (tieneNuevo) {
                        html += "<img id='imgNuevo";
                        html += div.id;
                        html += "' src='";
                        html += hdfRaiz.value;
                        html += "Images/Icons/NuevoRegistro.png' class='Icono NoImprimir' title = 'Nuevo Registro' > ";
                    }
                    html += "</th>";
                }
                html += "</tr>";
                html += "</thead>";
                html += "<tbody id='tb";
                html += div.id;
                html += "'>";
                html += "</tbody>";
                html += "<tfoot>";

                if (subtotales.length > 0) {
                    var tieneCheck = false;
                    var nCols = (tieneCheck ? nCampos + 1 : nCampos);
                    var n = (tieneCheck ? 1 : 0);
                    html += "<tr class='FilaCabecera'>";
                    var ccs = 0;
                    for (var j = 0; j < nCols; j++) {
                        html += "<th class='Derecha'";
                        if (subtotales.indexOf(j - n) > -1) {
                            html += " id='total";
                            html += id;
                            html += subtotales[ccs];
                            html += "'";
                            ccs++;
                        }
                        html + ">";
                        if (subtotales.indexOf(j - n) > -1) {
                            html += "0";
                        }
                        html += "</th>";
                    }
                    if (esMantenible) html += "<th></th>";
                    html += "</tr>";
                }

                html += "<tr>";
                html += "<td id='tdPagina";
                html += div.id;
                html += "' colspan='";
                html += (colOcultar == -1 ? nCampos: nCampos-1);
                html += "' class='Centro'>";
                html += "</td>";
                html += "</tr>";
                
                html += "</tfoot>";
                html += "</table>";
                div.innerHTML = html;
                if (listasCombos.length > 0) llenarCombos();
                configurarOrdenacion();
            }

            function llenarCombos() {
                var combos = document.getElementsByClassName(div.id + "Cab Cbo");
                var nCombos = combos.length;
                for (var j = 0; j < nCombos; j++) {
                    Gui.Combo(listasCombos[j], combos[j], sepCampo, "Todos");
                }
            }

            function crearMatriz() {
                matriz = [];
                var campos = [];
                var fila = [];
                var tipo = "";
                var valoresTxt = [];
                var valoresCbo = [];

                if (subtotales.length > 0) {
                    totales = [];
                    var nSubtotales = subtotales.length;
                    for (var j = 0; j < nSubtotales; j++) {
                        totales.push(0);
                    }
                }

                var controlesCab = document.getElementsByClassName(div.id + "Cab");
                var nControlesCab = controlesCab.length;
                for (var j = 0; j < nControlesCab; j++) {
                    if (controlesCab[j].className.indexOf("Txt") > -1) valoresTxt.push(controlesCab[j].value.toLowerCase());
                    else {
                        if (controlesCab[j].className.indexOf("Cbo") > -1) {
                            valoresCbo.push(controlesCab[j].options[controlesCab[j].selectedIndex].text);
                        }
                    }
                }
                var exito = false;
                var cTxt = 0;
                var cCbo = 0;
                var ccs = 0;
                var valor = "";
                var nRegistros = lista.length;
                if (nRegistros > 3 && lista[3] != "") {
                    for (var i = 3; i < nRegistros; i++) {
                        campos = lista[i].split(sepCampo);
                        cTxt = 0;
                        cCbo = 0;
                        if (tieneFiltro) {
                            for (var j = 0; j < nCampos; j++) {
                                if (controlesCab[j].className.indexOf("Txt") > -1) {
                                    exito = (valoresTxt[cTxt] == "" || (valoresTxt[cTxt] != "") && campos[j].toLowerCase().indexOf(valoresTxt[cTxt]) > -1);
                                    cTxt++;
                                }
                                else {
                                    if (controlesCab[j].className.indexOf("Cbo") > -1) {
                                        exito = (valoresCbo[cCbo] == "Todos" || (valoresCbo[cCbo] != "") && campos[j] == valoresCbo[cCbo]);
                                        cCbo++;
                                    }
                                }
                                if (!exito) break;
                            }
                        }
                        else exito = true;
                        ccs = 0;
                        if (exito) {
                            fila = [];
                            for (var j = 0; j < nCampos; j++) {
                                tipo = tipos[j];
                                if (tipo == "str") fila.push(campos[j]);
                                else {
                                    if (tipo.startsWith("int") || tipo.startsWith("float")) {
                                        fila.push(+campos[j]);
                                    }
                                }
                                if (subtotales.length > 0 && subtotales.indexOf(j) > -1) {
                                    valor = fila[j];
                                    totales[ccs] += valor;
                                    ccs++;
                                }
                            }
                            matriz.push(fila);
                        }
                    }
                }
            }

            function mostrarRegistros() {
                var html = "";
                var nRegMatriz = matriz.length;
                if (nRegMatriz > 0) {
                    var inicio = indicePagina * registrosPagina;
                    var fin = inicio + registrosPagina;
                    for (var i = inicio; i < fin; i++) {
                        if (i < nRegMatriz) {
                            html += "<tr class='FilaDatos ";
                            html += div.id;
                            html += "'>";
                            for (var j = 0; j < nCampos; j++) {
                                if (colOcultar == -1 || (colOcultar > -1 && j != colOcultar)) {
                                    html += "<td class='";
                                    esNumero = (tipos[j].indexOf("int") > -1 || tipos[j].indexOf("float") > -1);
                                    esFecha = (tipos[j].indexOf("datetime") > -1);
                                    esDecimal = (tipos[j].indexOf("float") > -1);
                                    if (esNumero) {
                                        html += "Derecha";
                                    }
                                    else if (esFecha) {
                                        html += "Centro";
                                    }
                                    else {
                                        html += "Izquierda";
                                    }
                                    html += "'>";
                                    if (esDecimal) html += matriz[i][j].toFixed(2);
                                    else if (esFecha) html += mostrarFechaDMY(matriz[i][j]);
                                    else html += matriz[i][j];
                                    html += "</td>";
                                }
                            }
							if (nBotones > 0) {
								for (var j = 0; j < nBotones; j++) {
									html += "<td>";
									html += "<input type='button' class='BotonGrid Centro NoImprimir ";
									html += id;
									html += "' value='";
									html += botones[j].titulo;
									html += "' data-id='";
									html += botones[j].id;
									html += "'/>";
									html += "</td>";
								}
							}
                            if (esMantenible) {
                                html += "<td class='Centro'>";
                                html += "<img src='";
                                html += hdfRaiz.value;
                                html += "Images/Icons/Editar.png' class='Icono NoImprimir Edit ";
                                html += div.id;
                                html += "' title='Editar Registro'>";
                                html += "<img src='";
                                html += hdfRaiz.value;
                                html += "Images/Icons/Eliminar.png' class='Icono NoImprimir Elim ";
                                html += div.id;
                                html += "' title='Eliminar Registro'>";
                                html += "</td>";
                            }
                            html += "</tr>";
                        }
                        else break;
                    }
                    var tbCuerpo = document.getElementById("tb" + div.id);
                    if (tbCuerpo != null) tbCuerpo.innerHTML = html;
                    var spTotal = document.getElementById("spnTotal" + div.id);
                    if (spTotal != null) spTotal.innerHTML = nRegMatriz;
					if (nBotones > 0) configurarBotones();
                }
                if (subtotales.length > 0) {
                    var nSubtotales = subtotales.length;
                    var tipo;
                    var esDecimal;
                    for (var j = 0; j < nSubtotales; j++) {
                        var celdaSubtotal = document.getElementById("total" + id + subtotales[j]);
                        if (celdaSubtotal != null) {
                            tipo = tipos[subtotales[j]];
                            esDecimal = (tipo.indexOf("float") > -1);
                            if (esDecimal) celdaSubtotal.innerText = totales[j].toFixed(2);
                            else celdaSubtotal.innerText = totales[j];
                        }
                    }
                }
                crearPaginas();
                configurarFilas();
            }
			
			function configurarBotones() {
				var divs = document.getElementsByClassName("BotonGrid Centro NoImprimir " + id);
				var nDivs = divs.length;
				for (var j = 0; j < nDivs; j++) {
					var btn = divs[j];
					btn.onclick = function () {
						var fila = this.parentNode.parentNode;
						var idRegistro = fila.childNodes[0].innerText;
						var idBoton = this.getAttribute("data-id");
						seleccionarBoton(id, idRegistro, idBoton, fila);
					}
				}
			}

            function configurarFilas() {
                var filas = document.getElementsByClassName("FilaDatos " + div.id);
                var nFilas = filas.length;
                for (var i = 0; i < nFilas; i++) {
                    filas[i].onclick = function () {
                        if (filaSel != null) filaSel.removeAttribute("style");
                        this.style.color = "blue";
                        this.style.backgroundColor = "yellow";
                        filaSel = this;
                        var id = this.childNodes[0].innerText;
                        seleccionarFila(div.id, this, id);
                    }                    
                }
                var imgsEditar = document.getElementsByClassName("Icono NoImprimir Edit " + div.id)
                var nImgsEditar = imgsEditar.length;
                for (var j = 0; j < nImgsEditar; j++) {
                    imgsEditar[j].onclick = function () {
                        var fila = this.parentNode.parentNode;
                        var id = fila.childNodes[0].innerText;
                        editarRegistro(fila, id, this);
                    }
                }
                var imgsEliminar = document.getElementsByClassName("Icono NoImprimir Elim " + div.id)
                var nImgsEliminar = imgsEliminar.length;
                for (var j = 0; j < nImgsEliminar; j++) {
                    imgsEliminar[j].onclick = function () {
                        var fila = this.parentNode.parentNode;
                        var id = fila.childNodes[0].innerText;
                        eliminarRegistro(id, this);
                    }
                }
            }

            function crearPaginas() {
                var tdPagina = document.getElementById("tdPagina" + div.id);
                if (tdPagina != null) {
                    var html = "";
                    var nRegMatriz = matriz.length;
                    var totalPaginas = Math.floor(nRegMatriz / registrosPagina);
                    if (nRegMatriz % registrosPagina > 0) totalPaginas++;
                    var registrosBloque = registrosPagina * paginasBloque;
                    var totalBloques = Math.floor(nRegMatriz / registrosBloque);
                    if (nRegMatriz % registrosBloque > 0) totalBloques++;
                    if (totalPaginas > 1) {
                        if (indiceBloque > 0) {
                            html += "<input type='button' value='<<' class='Pagina ";
                            html += div.id;
                            html += "'/>";
                            html += "<input type='button' value='<' class='Pagina ";
                            html += div.id;
                            html += "'/>";
                        }
                        var inicio = indiceBloque * paginasBloque;
                        var fin = inicio + paginasBloque;
                        for (var j = inicio; j < fin; j++) {
                            if (j < totalPaginas) {
                                html += "<input type='button' value='";
                                html += (j + 1);
                                html += "' class='";
                                html += (j == indicePagina ? "PaginaSel" : "Pagina");
                                html += " ";
                                html += div.id;
                                html += "'/>";
                            }
                            else break;
                        }
                        if (indiceBloque < totalBloques - 1) {
                            html += "<input type='button' value='>' class='Pagina ";
                            html += div.id;
                            html += "'/>";
                            html += "<input type='button' value='>>' class='Pagina ";
                            html += div.id;
                            html += "'/>";
                        }
                    }
                    tdPagina.innerHTML = html;
                    configurarPaginacion();
                }
            }

            function configurarPaginacion() {
                var botones = document.getElementsByClassName("Pagina " + div.id);
                var nBotones = botones.length;
                for (var j = 0; j < nBotones; j++) {
                    botones[j].onclick = function () {
                        paginar(this.value);
                        cambiarPagina(this.value);
                    }
                }
            }

            function configurarOrdenacion() {
                var spansOrden = document.getElementsByClassName("Orden " + div.id);
                var nSpansOrden = spansOrden.length;
                for (var j = 0; j < nSpansOrden; j++) {
                    spansOrden[j].onclick = function () {
                        ordenar(this);
                    }                    
                }
            }

            function configurarMover() {
                if (mover) {
                    var celdas = document.getElementsByTagName("th");
                    var nCeldas = celdas.length;
                    for (var j = 0; j < nCeldas; j++) {                    
                        celdas[j].draggable = true;
                        celdas[j].ondragstart = function (event) {
                            var posInicio = cabeceras.indexOf(this.firstChild.innerText);
                            event.dataTransfer.setData("text", posInicio);  
                        }
                        celdas[j].ondragover = function (event) {
                            event.preventDefault();
                        }
                        celdas[j].ondrop = function (event) {
                            event.preventDefault = true;
                            var posInicio = +event.dataTransfer.getData("text");
                            var posFin = +cabeceras.indexOf(this.firstChild.innerText);
                            var campo = cabeceras[posInicio];
                            var cabs = Array.from(cabeceras);
                            if (posInicio < posFin) {
                                for (var j = posInicio; j < posFin; j++) {
                                    cabs[j] = cabs[j + 1];
                                }
                                cabs[posFin] = campo;
                            }
                            else {
                                if (posInicio > posFin) {
                                    for (var j = posInicio; j > posFin; j--) {
                                        cabs[j] = cabs[j - 1];
                                    }
                                    cabs[posFin] = campo;
                                }
                            }
                            moverColumnas(cabs);
                        }
                    }
                }
            }

            function ordenar(spanOrden) {                
                colOrden = +spanOrden.getAttribute("data-col");
                var spanSimb = spanOrden.nextSibling;
                var simbolo = "▲";
                tipoOrden = 0;
                if (spanSimb.textContent == "▲") {
                    simbolo = "▼";
                    tipoOrden = 1;
                }                
                matriz.sort(ordenarMatriz);
                iniciarSimboloOrdenacion();
                spanSimb.innerText = simbolo;
                spanSimb.style.color = "red";
                mostrarRegistros();
            }

            function iniciarSimboloOrdenacion() {
                var spanSimbolos = document.getElementsByClassName("SimbOrden " + div.id);
                var nSpanSimbolos = spanSimbolos.length;
                for (var j = 0; j < nSpanSimbolos; j++) {
                    spanSimbolos[j].style.color = "white";
                }
            }

            function ordenarMatriz(x, y) {
                valx = x[colOrden];
                valy = y[colOrden];
                if (tipoOrden == 0) return (valx > valy ? 1 : -1);
                else return (valx < valy ? 1 : -1);
            }

            function paginar(valor) {
                if (isNaN(valor)) {
                    switch (valor) {
                        case "<<":
                            indiceBloque = 0;
                            indicePagina = 0;                            
                            break;
                        case "<":
                            indiceBloque--;
                            indicePagina = indiceBloque * paginasBloque;                            
                            break;
                        case ">":
                            indiceBloque++;
                            indicePagina = indiceBloque * paginasBloque;
                            break;
                        case ">>":
                            var nRegMatriz = matriz.length;
                            var registrosBloque = registrosPagina * paginasBloque;
                            var totalBloques = Math.floor(nRegMatriz / registrosBloque);
                            if (nRegMatriz % registrosBloque > 0) totalBloques++;
                            indiceBloque = totalBloques-1;
                            indicePagina = indiceBloque * paginasBloque;
                            break;
                    }
                }
                else {
                    indicePagina = (+valor -1);
                }
                mostrarRegistros();
            }

            function configurarEventos() {
                //Eventos de los Controles de la Cabecera
                var controlesCab = document.getElementsByClassName(div.id + "Cab");
                var nControlesCab = controlesCab.length;
                for (var j = 0; j < nControlesCab; j++) {
                    if (controlesCab[j].className.indexOf("Txt")>-1) {
                        controlesCab[j].onkeyup = function () {
                            crearMatriz();
                            mostrarRegistros();
                        }
                    }
                    else {
                        if (controlesCab[j].className.indexOf("Cbo") > -1) {
                            controlesCab[j].onchange = function () {
                                crearMatriz();
                                mostrarRegistros();
                            }
                        }
                    }
                }
                //Eventos de Botones arriba de la Grilla
                var imgNuevoFiltro = document.getElementById("imgNuevoFiltro" + div.id);
                if (imgNuevoFiltro != null) {
                    imgNuevoFiltro.onclick = function () {
                        var controlesCab = document.getElementsByClassName(div.id + "Cab");
                        var nControlesCab = controlesCab.length;
                        for (var j = 0; j < nControlesCab; j++) {
                            controlesCab[j].value = "";
                        }
                        crearMatriz();
                        mostrarRegistros();
                    }
                }
                var imgQuitarOrden = document.getElementById("imgQuitarOrden" + div.id);
                if (imgQuitarOrden != null) {
                    imgQuitarOrden.onclick = function () {
                        var spanSimbolos = document.getElementsByClassName("SimbOrden " + div.id);
                        var nSpanSimbolos = spanSimbolos.length;
                        for (var j = 0; j < nSpanSimbolos; j++) {
                            spanSimbolos[j].innerHTML = "";
                        }
                        tipoOrden = 0;
                        colOrden = 0;
                        matriz.sort(ordenarMatriz);
                        mostrarRegistros();
                    }                    
                }
                var imgExportarTexto = document.getElementById("imgExportarTexto" + div.id);
                if (imgExportarTexto != null) {
                    imgExportarTexto.onclick = function () {
                        var txt = crearTextoDesdeMatriz(",","\r\n");
                        if (txt != "") {
                            FileSystem.download(txt, nombreReporte + ".txt");
                        }
                    }
                }
                var imgExportarExcel = document.getElementById("imgExportarExcel" + div.id);
                if (imgExportarExcel != null) {
                    imgExportarExcel.onclick = function () {
                        var txt = crearTextoDesdeMatriz("|", "¬", true);
                        if (txt != "") {
                            var frm = new FormData();
                            frm.append("Data", txt);
                            archivoExportar = nombreReporte + ".xlsx";
                            Http.post(controlador + "/Exportar?archivo=" + archivoExportar, mostrarRptaExportar, "arraybuffer", frm);
                        }
                    }
                }
                var imgExportarWord = document.getElementById("imgExportarWord" + div.id);
                if (imgExportarWord != null) {
                    imgExportarWord.onclick = function () {
                        var txt = crearTextoDesdeMatriz("|", "¬", true);
                        if (txt != "") {
                            var frm = new FormData();
                            frm.append("Data", txt);
                            archivoExportar = nombreReporte + ".docx";
                            Http.post(controlador + "/Exportar?archivo=" + archivoExportar, mostrarRptaExportar, "arraybuffer", frm);
                        }
                    }
                }
                var imgExportarPdf = document.getElementById("imgExportarPdf" + div.id);
                if (imgExportarPdf != null) {
                    imgExportarPdf.onclick = function () {
                        var txt = crearTextoDesdeMatriz("|", "¬", true);
                        if (txt != "") {
                            var frm = new FormData();
                            frm.append("Data", txt);
                            archivoExportar = nombreReporte + ".pdf";
                            Http.post(controlador + "/Exportar?archivo=" + archivoExportar, mostrarRptaExportar, "arraybuffer", frm);
                        }
                    }
                }
                var imgNuevo = document.getElementById("imgNuevo" + div.id);
                if (imgNuevo != null) {
                    imgNuevo.onclick = function () {
                        nuevoRegistro();
                    }
                }
                var imgImprimir = document.getElementById("imgImprimir" + div.id);
                if (imgImprimir != null) {
                    imgImprimir.onclick = function () {
                        var tabla = crearHTMLDesdeMatriz("|", "¬", true);
                        if (tabla != "") {
                            Impresion.ImprimirTabla(tabla);
                        }
                    }
                }
            }

            function mostrarRptaExportar(rpta) {
                if (rpta.byteLength > 0) {
                    FileSystem.download(rpta, archivoExportar);
                }
            }

            function crearTextoDesdeMatriz(sCampo, sRegistro, tieneMetadata) {
                var txt = "";
                tieneMetadata = (tieneMetadata == null ? false : tieneMetadata);
                var nRegMatriz = matriz.length;
                if (nRegMatriz > 0) {
                    txt = cabeceras.join(sCampo);
                    txt += sRegistro;
                    if (tieneMetadata) {
                        txt += anchos.join(sCampo);
                        txt += sRegistro;
                        txt += tipos.join(sCampo);
                        txt += sRegistro;
                    }
                    for (var i = 0; i < nRegMatriz; i++) {
                        txt += matriz[i].join(sCampo);
                        if (i < nRegMatriz - 1) txt += sRegistro;
                    }
                }
                return txt;
            }

            function crearHTMLDesdeMatriz(sCampo, sRegistro) {
                var html = "";
                var nRegMatriz = matriz.length;
                var nCampos = cabeceras.length;
                if (nRegMatriz > 0) {
                    html += "<table>";
                    html += "<thead>";
                    html += "<tr style='background-color:blue;color:white'>";
                    for (var j = 0; j < nCampos; j++) {
                        html += "<th style='width:";
                        html += anchos[j];
                        html += "px'>";
                        html += cabeceras[j];
                        html += "</th>";
                    }
                    html += "</tr>";
                    html += "</thead>";
                    html += "<tbody>";
                    for (var i = 0; i < nRegMatriz; i++) {
                        html += "<tr style='background-color:white;color:blue'>";
                        for (var j = 0; j < nCampos; j++) {
                            html += "<td>";
                            html += matriz[i][j];
                            html += "</td>";
                        }
                        html += "</tr>";
                    }
                    html += "</tbody>";
                    html += "</table>";
                }
                return html;
            }

            Gui.Grilla.prototype.DesmarcarFilaSeleccionada = function () {
                if (filaSel != null) {
                    filaSel.removeAttribute("style");
                    filaSel = null;
                }
            }

            Gui.Grilla.prototype.ObtenerFilaSeleccionada = function() {
                return filaSel;
            }

            Gui.Grilla.prototype.IrUltimaPagina = function () {
                var nRegMatriz = matriz.length;
                var registrosBloque = registrosPagina * paginasBloque;
                var totalPaginas = Math.floor(nRegMatriz / registrosPagina);
                if (nRegMatriz % registrosPagina > 0) totalPaginas++;
                var totalBloques = Math.floor(nRegMatriz / registrosBloque);
                if (nRegMatriz % registrosBloque > 0) totalBloques++;
                indiceBloque = totalBloques - 1;
                indicePagina = totalPaginas -1;
                mostrarRegistros();
            }
        }
    }
    
	Gui.LimpiarControles = function (clase) {
        var controles = document.getElementsByClassName(clase);
        var nControles = controles.length;
        for (var j = 0; j < nControles; j++) {
            if (controles[j].tagName == "IMG") controles[j].src = "";
            else {
                controles[j].value = "";
                controles[j].setAttribute("data-val", "");
                controles[j].style.borderColor="";
            }
        }
    }

    Gui.MostrarValoresControles = function (clase, campos, textoCombo, listaCombos) {
        textoCombo = (textoCombo == null ? false : textoCombo);
        var controles = document.getElementsByClassName(clase);
        var nControles = controles.length;
        var c = 0;
        for (var j = 0; j < nControles; j++) {
            if (controles[j].tagName == "SELECT") {
                if (textoCombo) {
                    controles[j].value = Gui.BuscarTextoCombo(campos[j], listaCombos[c]);
                    c++;
                }
                else controles[j].value = campos[j];
            }
            else {
                if (controles[j].tagName == "IMG") {
                    controles[j].src = "data:image/png;base64," + campos[j];
                }
                else {
                    controles[j].value = campos[j];
                    controles[j].setAttribute("data-val",campos[j]);
                }
            }
        }
    }    

    Gui.ObtenerValoresControles = function (clase, sepCampo, textoCombo) {
        var rpta = "";
        textoCombo = (textoCombo == null ? false : textoCombo);
        var controles = document.getElementsByClassName(clase);
        var nControles = controles.length;
        for (var j = 0; j < nControles; j++) {
            if (controles[j].tagName == "SELECT") {
                if (textoCombo) rpta += controles[j].options[controles[j].selectedIndex].text;
                else rpta += controles[j].value;
            }
            else {
                if (controles[j].tagName == "SPAN") rpta += controles[j].textContent;
                else rpta += controles[j].value;
            }
            if (j < nControles-1) rpta += sepCampo;
        }
        return rpta;
    }

    Gui.ValidarControles = function (claseReq, claseLec) {
        var controles = document.getElementsByClassName(claseReq);
        var nControles = controles.length;
        var esSoloLectura;
        var ce = 0;
        for (var j = 0; j < nControles; j++) {
            esSoloLectura = (controles[j].className.indexOf(claseLec) > -1);
            if (!esSoloLectura && controles[j].value == "") {
                controles[j].style.borderColor = "red";
                ce++;
            }
            else controles[j].style.borderColor = "";
        }
        return (ce == 0);
    }
	return Gui;
})();

var Validacion = (function () {
    function Validacion() {
    }
	
	Validacion.ValidarDatos = function(claseReq, claseNum, spnValida) {
        var valido = false;
        if (Validacion.ValidarRequeridos(claseReq)) {
            if (Validacion.ValidarNumeros(claseNum)) {
                spnValida.innerHTML = "";
                valido = true;
            }
            else {
                spnValida.style.color = "blue";
                spnValida.innerHTML = "Los campos en color azul son numeros mayor a cero";
            }
        }
        else {
            spnValida.style.color = "red";
            spnValida.innerHTML = "Los campos en color rojo son obligatorios";
        }
        return valido;
    }
	
	Validacion.ValidarRequeridos = function (clase) {
        var ce = 0;
        var controles = document.getElementsByClassName(clase);
        var ncontroles = controles.length;
        for (var j = 0; j < ncontroles; j++) {
            if (controles[j].value == "") {
                controles[j].style.borderColor = "red";
                ce++;
            }
            else controles[j].style.borderColor = "";
        }
        return (ce == 0);
    }

    Validacion.ValidarNumeros = function (clase) {
        var ce = 0;
        var controles = document.getElementsByClassName(clase);
        var ncontroles = controles.length;
        for (var j = 0; j < ncontroles; j++) {
            if (controles[j].value != "") {
                if (isNaN(controles[j].value)) {
                    controles[j].style.borderColor = "blue";
                    ce++;
                }
                else {
                    var valor = (controles[j].value * 1);
                    if (valor <= 0) {
                        controles[j].style.borderColor = "blue";
                        ce++;
                    }
                    else controles[j].style.borderColor = "";
                }
            }
        }
        return (ce == 0);
    }
	
	Validacion.ValidarNumerosEnlinea = function(clase) {
        if (clase == null) clase = "N";
        var controles = document.getElementsByClassName(clase);
        var ncontroles = controles.length;
        for (var j = 0; j < ncontroles; j++) {
            controles[j].onkeyup = controles[j].onkeydown = function (event) {
                var keycode = ('which' in event ? event.which : event.keycode);
                var esValido = ((keycode > 47 && keycode < 58) || (keycode > 95 && keycode < 106) || keycode == 8 || keycode == 37 || keycode == 39 || keycode == 110 || keycode == 188);
                if (!esValido) this.value = this.value.removeCharAt(this.selectionStart);
            }
            controles[j].onpaste = function (event) {
                event.preventDefault();
            }
        }
    }

    Validacion.ValidarDecimalesEnlinea = function(clase) {
        if (clase == null) clase = "D";
        var controles = document.getElementsByClassName(clase);
        var ncontroles = controles.length;
        for (var j = 0; j < ncontroles; j++) {
            controles[j].onkeyup = controles[j].onkeydown = function (event) {
                var keycode = ('which' in event ? event.which : event.keycode);
                var esValido = ((keycode > 47 && keycode < 58) || (keycode > 95 && keycode < 106) || keycode == 8 || keycode == 37 || keycode == 39 || keycode == 110 || keycode == 188 || (keycode == 190 && this.value.split(".").length < 3));
                if (!esValido) this.value = this.value.removeCharAt(this.selectionStart);
            }
            controles[j].onpaste = function (event) {
                event.preventDefault();
            }
        }
    }

    String.prototype.removeCharAt = function (i) {
        var tmp = this.split('');
        tmp.splice(i - 1, 1);
        return tmp.join('');
    }

    return Validacion;
})();

var Popup = (function () {
    function Popup() {
    }
	Popup.Resize = function(popup, ancho, alto) {
        popup.style.width = ancho + "%";
        popup.style.height = alto + "%";
        popup.style.left = ((100 - ancho) / 2) + "%";
        popup.style.top = ((100 - alto) / 2) + "%";
    }

    Popup.ConfigurarArrastre = function(divPopupContainer, divPopupWindow, divBarra) {
        divBarra.draggable = true;
        divBarra.ondragstart = function (event) {
            var ancho = getComputedStyle(divPopupWindow, null).getPropertyValue("left");
            var alto = getComputedStyle(divPopupWindow, null).getPropertyValue("top");
            var a = Math.floor(ancho.replace("px", ""));
            var b = Math.floor(alto.replace("px", ""));
            var x = (event.clientX > a ? event.clientX - a : a - event.clientX);
            var y = (event.clientY > b ? event.clientY - b : b - event.clientY);
            var punto = x + "," + y;
            event.dataTransfer.setData("text", punto);
        }
        divBarra.ondragover = function (event) {
            event.preventDefault();
        }
        divPopupContainer.ondragover = function (event) {
            event.preventDefault();
        }
        divPopupContainer.ondrop = function (event) {
            event.preventDefault();
            var x1 = event.clientX;
            var y1 = event.clientY;
            var puntoInicial = event.dataTransfer.getData("text");
            var punto = puntoInicial.split(",");
            var x2 = punto[0] * 1;
            var y2 = punto[1] * 1;
            divPopupWindow.style.left = (x1 - x2) + "px";
            divPopupWindow.style.top = (y1 - y2) + "px";
        }
    }

    return Popup;
})();

var Impresion = (function () {
    function Impresion() {
    }

    Impresion.ImprimirTabla = function(tabla) {
        var ventana = window.frames["print_frame"];
        if (ventana != null) {
            var pagina = document.body;
            ventana.document.body.innerHTML = "";
            ventana.document.body.innerHTML = tabla;
            ventana.focus();
            ventana.print();
            ventana.close();
            document.body = pagina;
        }
    }

    Impresion.Imprimir = function(div) {
        var ventana = window.frames["print_frame"];
        if (ventana != null) {
            var pagina = document.body;
            Impresion.MostrarControles(false);
            ventana.document.body.innerHTML = "";
            Impresion.GuardarValores(div);
            ventana.document.body.innerHTML = div.outerHTML;
            divVentana = ventana.document.getElementById(div.id);
            if (divVentana != null) Impresion.RecuperarValores(divVentana);
            ventana.focus();
            ventana.print();
            ventana.close();
            Impresion.MostrarControles(true);
            document.body = pagina;
        }
    }

    Impresion.GuardarValores = function(div) {
        if (div.hasChildNodes()) {
            var controles = div.childNodes;
            var ncontroles = controles.length;
            var control;
            for (var i = 0; i < ncontroles; i++) {
                control = controles[i];
                if (control.tagName == "INPUT" && control.type == "text") {
                    control.setAttribute("value", control.value);
                }
                Impresion.GuardarValores(control);
            }
        }
    }

    Impresion.RecuperarValores = function(div) {
        if (div.hasChildNodes()) {
            var controles = div.childNodes;
            var ncontroles = controles.length;
            var control;
            for (var i = 0; i < ncontroles; i++) {
                control = controles[i];
                if (control.tagName == "INPUT" && control.type == "text") {
                    control.value = control.getAttribute("value");
                }
                Impresion.RecuperarValores(control);
            }
        }
    }

    Impresion.MostrarControles = function(visible) {
        var controles = document.getElementsByClassName("NoImprimir");
        var ncontroles = controles.length;
        var estilo = (visible ? "inline" : "none");
        for (var j = 0; j < ncontroles; j++) {
            controles[j].style.display = estilo;
        }
    }

    return Impresion;
})();

var SVG = (function () {
    function SVG() {
    }

    SVG.crearTexto = function (x, y, color, fuente, tamanio, texto, vertical) {
        var contenido = "";
        contenido += "<text x='";
        contenido += x;
        contenido += "' y='";
        contenido += y;
        contenido += "' fill='";
        contenido += color;
        contenido += "' alignment-baseline='bottom' font-family='";
        contenido += fuente;
        contenido += "' font-size='";
        contenido += tamanio;
        contenido += "' data-texto='";
        contenido += texto;
        contenido += "'";
        if (vertical != null) {
            contenido += " transform='rotate(270,";
            contenido += x;
            contenido += ",";
            contenido += y;
            contenido += ")'";
        }
        contenido += ">";
        contenido += texto;
        contenido += "</text>";
        return contenido;
    }

    SVG.crearRectangulo = function (id, nombre, clase, x, y, ancho, alto, colorRelleno, colorBorde, anchoBorde, profundidad, animado) {
        var contenido = "<g id='g";
        contenido += id;
        contenido += "'>";
        contenido += "<rect id='";
        contenido += id;
        contenido += "' data-id='";
        contenido += id;
        contenido += "' data-nombre='";
        contenido += nombre;
        contenido += "' class='";
        contenido += clase;
        contenido += "' x='";
        contenido += x;
        contenido += "' y='";
        contenido += y;
        contenido += "' fill='";
        contenido += colorRelleno;
        contenido += "' width='";
        contenido += ancho;
        contenido += "' height='";
        contenido += alto;
        contenido += "' stroke='";
        contenido += colorBorde;
        contenido += "' stroke-width='";
        contenido += anchoBorde;
        contenido += "' style='cursor:pointer'>";
        contenido += "</rect>";
        if (profundidad != null) {
            contenido += "<polygon points='";
            contenido += x;
            contenido += ",";
            contenido += y;
            contenido += " ";
            contenido += x + profundidad;
            contenido += ",";
            contenido += y - profundidad;
            contenido += " ";
            contenido += x + ancho + profundidad;
            contenido += ",";
            contenido += y - profundidad;
            contenido += " ";
            contenido += x + ancho + profundidad;
            contenido += ",";
            contenido += y + alto - profundidad;
            contenido += " ";
            contenido += x + ancho;
            contenido += ",";
            contenido += y + alto;
            contenido += " ";
            contenido += x + ancho;
            contenido += ",";
            contenido += y;
            contenido += "' style='fill:";
            contenido += colorRelleno;
            contenido += "; stroke:";
            contenido += colorBorde;
            contenido += "; stroke-width:";
            contenido += anchoBorde;
            contenido += "'/>";
            contenido += SVG.crearLinea(x + ancho, y, x + ancho + profundidad, y - profundidad, anchoBorde, colorBorde);
        }
        if (animado != null) {
            contenido += "<animate xlink:href='#";
            contenido += id;
            contenido += "' attributeName='width' from='0' to='";
            contenido += ancho;
            contenido += "' dur='1s' begin='0s' repeatCount='indefinite'>";
        }
        contenido += "</g>";
        return contenido;
    }

    SVG.crearLinea = function (x1, y1, x2, y2, ancho, color) {
        var contenido = "";
        contenido += "<line x1='";
        contenido += x1;
        contenido += "' y1='";
        contenido += y1;
        contenido += "' x2='";
        contenido += x2;
        contenido += "' y2='";
        contenido += y2;
        contenido += "' style='stroke:";
        contenido += color;
        contenido += ";stroke-width:";
        contenido += ancho;
        contenido += "'/>";
        return contenido;
    }

    SVG.crearCirculo = function (id, nombre, clase, x, y, radio, color) {
        var contenido = "";
        contenido += "<circle id='";
        contenido += id;
        contenido += "' cx = '";
        contenido += x;
        contenido += "' cy='";
        contenido += y;
        contenido += "' fill='";
        contenido += color;
        contenido += "' r='";
        contenido += radio;
        contenido += "' data-id='";
        contenido += id;
        contenido += "' data-nombre='";
        contenido += nombre;
        contenido += "' class='";
        contenido += clase;
        contenido += "' style='cursor:pointer'/>";
        return contenido;
    }

    SVG.crearElipse = function (x, y, radioX, radioY, color) {
        var contenido = "";
        contenido += "<ellipse cx='";
        contenido += x;
        contenido += "' cy='";
        contenido += y;
        contenido += "' fill='";
        contenido += color;
        contenido += "' rx='";
        contenido += radioX;
        contenido += "' ry='";
        contenido += radioY;
        contenido += "'/>";
        return contenido;
    }

    SVG.descargarGrafico = function (svg) {
        var contenido = svg.outerHTML;
        var blob = new Blob([contenido], { type: "image/svg+xml" });
        var img = new Image();
        img.src = URL.createObjectURL(blob);
        img.onload = function () {
            var canvas = document.createElement("canvas");
            canvas.width = svg.scrollWidth;
            canvas.height = svg.scrollHeight;
            var contexto = canvas.getContext("2d");
            contexto.drawImage(this, 0, 0, canvas.width, canvas.height);
            var enlace = document.createElement("a");
            enlace.download = "Grafico.jpg";
            enlace.href = canvas.toDataURL("");
            enlace.click();
        }
    }

    return SVG;
})();
window.SVG = SVG;