// Paquetes de bytes y lotes del estilo LD (extraídos de appDemo06-10 y 14, donde este código se repite copiado).
// Formato: [2 bytes: longitud del texto][texto UTF-8][bytes del archivo 1][bytes del archivo 2]...
// El texto lleva un registro por archivo (campos con "|", registros con ";") y el ÚLTIMO campo es el tamaño
// en bytes. Mismo formato que Paquete de Modulos/modPaquetes.py (base 256, longitud en bytes UTF-8).
// Estilo: objeto con métodos PascalCase, como Gui, Popup y Validacion de General.js.

var Paquete = (function () {
    function Paquete() {
    }

    function validarMaxArchivosLote(maxArchivosLote) {
        if (!Number.isSafeInteger(maxArchivosLote) || maxArchivosLote <= 0) {
            throw new RangeError("maxArchivosLote debe ser un entero positivo entregado por el servidor");
        }
    }

    // Lee un Blob recibido del servidor. Devuelve { registros: [[campos], ...], blobs: [Blob, ...] }.
    // Lanza Error si el paquete está truncado: así no se muestran archivos incompletos.
    Paquete.Leer = async function (blob, sepReg, sepCampo) {
        sepReg = (sepReg == null ? ";" : sepReg);
        sepCampo = (sepCampo == null ? "|" : sepCampo);
        if (blob.size < 2) throw new Error("Paquete sin cabecera");
        // Los demos leen cada byte con slice(0,1).arrayBuffer(); una sola lectura de 2 bytes es equivalente.
        var cabecera = new Uint8Array(await blob.slice(0, 2).arrayBuffer());
        var nTexto = cabecera[0] * 256 + cabecera[1];
        if (blob.size < 2 + nTexto) throw new Error("Paquete truncado: falta parte del texto");
        var bytesTexto = new Uint8Array(await blob.slice(2, 2 + nTexto).arrayBuffer());
        // TextDecoder reemplaza al bucle String.fromCharCode de los demos, que rompe las tildes (UTF-8).
        var texto = new TextDecoder("utf-8").decode(bytesTexto);
        var registros = [];
        var blobs = [];
        var x = 2 + nTexto;
        if (texto != "") {
            var lista = texto.split(sepReg);
            for (var i = 0; i < lista.length; i++) {
                var campos = lista[i].split(sepCampo);
                var size = +campos[campos.length - 1];
                if (!Number.isInteger(size) || size < 0 || x + size > blob.size) {
                    throw new Error("Paquete truncado o con tamaños no válidos en: " + campos[0]);
                }
                registros.push(campos);
                blobs.push(blob.slice(x, x + size));
                x += size;
            }
        }
        if (x != blob.size) throw new Error("Paquete con bytes sobrantes");
        return { registros: registros, blobs: blobs };
    }

    // Lee un paquete del formato ANTERIOR de los demos (appDemo06-10, 14); inverso de Paquete.Leer.
    // Existe solo como puente para leer un paquete que genera un demo existente durante una migración;
    // el formato de trabajo es Paquete.Leer. Los demos usan base 255 en la cabecera, cuentan el texto en
    // caracteres y leen cada byte con String.fromCharCode (Latin-1, no UTF-8): solo son correctos con
    // texto ASCII. Reproduce ese comportamiento tal cual, así que hereda sus límites (texto ASCII, n <= 65279).
    Paquete.LeerLegacy = async function (blob, sepReg, sepCampo) {
        sepReg = (sepReg == null ? ";" : sepReg);
        sepCampo = (sepCampo == null ? "|" : sepCampo);
        if (blob.size < 2) throw new Error("Paquete sin cabecera");
        var cabecera = new Uint8Array(await blob.slice(0, 2).arrayBuffer());
        var nTexto = cabecera[0] * 255 + cabecera[1];
        if (blob.size < 2 + nTexto) throw new Error("Paquete truncado: falta parte del texto");
        var bytesTexto = new Uint8Array(await blob.slice(2, 2 + nTexto).arrayBuffer());
        // String.fromCharCode byte a byte: es exactamente lo que hace el cliente de los demos (Latin-1).
        var texto = "";
        for (var j = 0; j < bytesTexto.length; j++) texto += String.fromCharCode(bytesTexto[j]);
        var registros = [];
        var blobs = [];
        var x = 2 + nTexto;
        if (texto != "") {
            var lista = texto.split(sepReg);
            for (var i = 0; i < lista.length; i++) {
                var campos = lista[i].split(sepCampo);
                var size = +campos[campos.length - 1];
                if (!Number.isInteger(size) || size < 0 || x + size > blob.size) {
                    throw new Error("Paquete truncado o con tamaños no válidos en: " + campos[0]);
                }
                registros.push(campos);
                blobs.push(blob.slice(x, x + size));
                x += size;
            }
        }
        if (x != blob.size) throw new Error("Paquete con bytes sobrantes");
        return { registros: registros, blobs: blobs };
    }

    // Arma el paquete para subirlo: texto = "nombre|size;nombre|size", blobs = [Blob/File, ...] en el mismo orden.
    // Devuelve un Blob listo para FormData.append("Blob", paquete). Inverso de Paquete.Leer.
    Paquete.Crear = function (texto, blobs) {
        var bytesTexto = new TextEncoder().encode(texto);
        var n = bytesTexto.length;
        if (n > 65535) throw new Error("El texto del paquete supera 65535 bytes");
        return new Blob([new Uint8Array([Math.floor(n / 256), n % 256]), bytesTexto].concat(blobs));
    }

    // Agrupa [{id, size}, ...] en lotes cuya suma no supera `limite` (appDemo10: grupos de ~100 KB).
    // Un elemento mayor que el límite forma su propio lote: en la subida, ese va por bloques I/P.
    // Devuelve una lista de listas de id, en el orden recibido.
    Paquete.AgruparPorTamano = function (items, limite, maxArchivosLote) {
        validarMaxArchivosLote(maxArchivosLote);
        var grupos = [];
        var actual = [];
        var total = 0;
        for (var i = 0; i < items.length; i++) {
            if (actual.length > 0 && (actual.length >= maxArchivosLote || total + items[i].size > limite)) {
                grupos.push(actual);
                actual = [];
                total = 0;
            }
            actual.push(items[i].id);
            total += items[i].size;
        }
        if (actual.length > 0) grupos.push(actual);
        return grupos;
    }

    // Planifica los viajes de una tanda en UN solo recorrido y EN ORDEN (items = [{id, size}, ...]). El plan no depende
    // de la dirección: sirve igual para SUBIR (lote -> GrabarLote, bloque -> GrabarBloque I/P) y para DESCARGAR
    // (lote -> ObtenerPaquete, bloque -> ObtenerBloque por índice; el cliente une las partes). Regla de decisión:
    //  - un archivo con size <= sizeLote entra al lote abierto si la suma sigue <= sizeLote; si no cabe, se cierra el
    //    lote y ese archivo abre el siguiente;
    //  - un archivo con size > sizeLote cierra el lote abierto, se corta en bloques de sizeBloque (I = primero, P = resto)
    //    y, al terminar su último bloque, el recorrido continúa con los siguientes en un lote nuevo.
    // Devuelve viajes: { tipo: "lote", ids: [id...] } o { tipo: "bloque", id, bloque, nBloques, inicio } (inicio = índice
    // del viaje de su bloque I, para reiniciar el archivo si falla un bloque P). Nunca reordena los archivos.
    Paquete.PlanificarViajes = function (items, sizeLote, sizeBloque, maxArchivosLote) {
        validarMaxArchivosLote(maxArchivosLote);
        sizeLote = (sizeLote == null ? 100 * 1024 : sizeLote);
        sizeBloque = (sizeBloque == null ? 100 * 1024 : sizeBloque);
        var viajes = [];
        var actual = [];
        var total = 0;
        function cerrarLote() {
            if (actual.length > 0) viajes.push({ tipo: "lote", ids: actual });
            actual = [];
            total = 0;
        }
        for (var i = 0; i < items.length; i++) {
            var it = items[i];
            if (it.size > sizeLote) {
                cerrarLote();
                var n = Paquete.CantidadBloques(it.size, sizeBloque);
                var inicio = viajes.length;
                for (var b = 0; b < n; b++) viajes.push({ tipo: "bloque", id: it.id, bloque: b, nBloques: n, inicio: inicio });
            } else {
                if (actual.length > 0 && (actual.length >= maxArchivosLote || total + it.size > sizeLote)) cerrarLote();
                actual.push(it.id);
                total += it.size;
            }
        }
        cerrarLote();
        return viajes;
    }

    // Entero positivo leído de un campo oculto (texto) o `defecto` si falta o no es válido. Sirve para los tamaños que entrega settings.
    Paquete.ParametroEntero = function (valor, defecto) {
        var n = Number(valor);
        return (valor != null && String(valor).trim() !== "" && Number.isInteger(n) && n > 0) ? n : defecto;
    }

    // Cantidad de bloques de `size` bytes que necesita un archivo (appDemo13: leerArchivo/enviarBloqueArchivo).
    Paquete.CantidadBloques = function (size, sizeBloque) {
        sizeBloque = (sizeBloque == null ? 100 * 1024 : sizeBloque);
        var n = Math.floor(size / sizeBloque);
        if (size % sizeBloque > 0) n++;
        return n;
    }

    return Paquete;
}());

if (typeof module !== "undefined") module.exports = { Paquete: Paquete };
