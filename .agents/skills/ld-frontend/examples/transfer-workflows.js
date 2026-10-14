// Ejemplos compartidos de consulta y envío para los casos 1 a 6. El contrato
// del servidor está documentado en ld-backend/references/transfer-contract.md.
const TRANSFER_CHUNK_BYTES = 100 * 1024;
const CHUNK_RETRY_ATTEMPTS = 3;

async function sendChunkWithRetry(url, form, csrfToken, index, signal) {
  let lastError;

  for (let attempt = 0; attempt < CHUNK_RETRY_ATTEMPTS; attempt++) {
    let response;
    try {
      response = await fetch(url, {
        method: "POST",
        headers: { "X-CSRFToken": csrfToken },
        body: form,
        signal
      });
    } catch (error) {
      if (signal?.aborted) throw error;
      lastError = error;
    }

    if (response) {
      if (response.status === 409) {
        let result;
        try {
          result = await response.json();
        } catch {
          result = null;
        }
        if (result?.code !== "chunk_in_progress") {
          throw new Error(`El servidor rechazó el fragmento ${index}: HTTP 409`);
        }
        lastError = new Error(`El fragmento ${index} todavía se está guardando`);
      } else if (!response.ok && response.status < 500) {
        throw new Error(`El servidor rechazó el fragmento ${index}: HTTP ${response.status}`);
      } else if (!response.ok) {
        lastError = new Error(`Falló el fragmento ${index}: HTTP ${response.status}`);
      } else {
        try {
          const result = await response.json();
          if (result.received === true && result.index === index) return result;
          lastError = new Error(`El servidor no confirmó el fragmento ${index}`);
        } catch (error) {
          lastError = error;
        }
      }
    }

    if (attempt + 1 < CHUNK_RETRY_ATTEMPTS) {
      await new Promise(resolve => setTimeout(resolve, 250 * (2 ** attempt)));
    }
  }

  throw new Error(
    `No se pudo confirmar el fragmento ${index} tras ${CHUNK_RETRY_ATTEMPTS} intentos. ` +
    "La carga quedó incompleta; vuelve a iniciar uploadItems para comenzar una carga nueva.",
    { cause: lastError }
  );
}

async function fetchRecordPage(limit = 200, cursor = null, signal) {
  const url = new URL("/api/records", location.origin);
  url.searchParams.set("limit", String(limit));
  if (cursor) url.searchParams.set("cursor", cursor);

  const response = await fetch(url, {
    headers: { Accept: "application/json" },
    signal
  });
  if (!response.ok) throw new Error(`Falló la consulta de registros: HTTP ${response.status}`);
  return response.json();
}

async function fetchFilePage(limit = 100, cursor = null, signal) {
  const url = new URL("/api/files", location.origin);
  url.searchParams.set("limit", String(limit));
  if (cursor) url.searchParams.set("cursor", cursor);

  const response = await fetch(url, {
    headers: { Accept: "application/json" },
    signal
  });
  if (!response.ok) throw new Error(`Falló la consulta de archivos: HTTP ${response.status}`);
  return response.json();
}

async function fetchFileRange(fileId, start, end, signal) {
  if (!Number.isSafeInteger(start) || !Number.isSafeInteger(end) || start < 0 || end < start) {
    throw new RangeError("El rango de bytes no es válido");
  }
  const response = await fetch(
    `/api/files/${encodeURIComponent(fileId)}/content`,
    { headers: { Range: `bytes=${start}-${end}` }, signal }
  );
  if (response.status !== 206) {
    throw new Error(`Se esperaba HTTP 206 para el rango de bytes; se recibió ${response.status}`);
  }
  const contentRange = /^bytes (\d+)-(\d+)\/(\d+)$/.exec(
    response.headers.get("Content-Range") || ""
  );
  if (!contentRange) {
    throw new Error("El servidor no devolvió un encabezado Content-Range válido");
  }
  const [, responseStartText, responseEndText, totalSizeText] = contentRange;
  const responseStart = Number(responseStartText);
  const responseEnd = Number(responseEndText);
  const totalSize = Number(totalSizeText);
  if (
    !Number.isSafeInteger(responseStart) ||
    !Number.isSafeInteger(responseEnd) ||
    !Number.isSafeInteger(totalSize) ||
    responseStart !== start ||
    totalSize <= responseStart ||
    responseEnd !== Math.min(end, totalSize - 1)
  ) {
    throw new Error("El servidor devolvió un Content-Range distinto al solicitado");
  }
  const expectedLength = responseEnd - responseStart + 1;
  const bytes = await response.arrayBuffer();
  if (bytes.byteLength !== expectedLength) {
    throw new Error(`Se esperaban ${expectedLength} bytes; se recibieron ${bytes.byteLength}`);
  }
  return bytes;
}

async function fetchMixedPage(limit = 100, cursor = null, signal) {
  const url = new URL("/api/mixed", location.origin);
  url.searchParams.set("limit", String(limit));
  if (cursor) url.searchParams.set("cursor", cursor);

  const response = await fetch(url, {
    headers: { Accept: "application/vnd.ld-page-v1" },
    signal
  });
  if (!response.ok) throw new Error(`Falló la consulta de la página mixta: HTTP ${response.status}`);
  if (!response.headers.get("Content-Type")?.startsWith("application/vnd.ld-page-v1")) {
    throw new Error("El servidor devolvió un formato de página mixta inesperado");
  }
  return parseLdp1(await response.arrayBuffer());
}

async function parseLdp1(buffer, maxManifestBytes = 1024 * 1024) {
  const bytes = buffer instanceof ArrayBuffer
    ? new Uint8Array(buffer)
    : ArrayBuffer.isView(buffer)
      ? new Uint8Array(buffer.buffer, buffer.byteOffset, buffer.byteLength)
      : null;
  if (!bytes) throw new TypeError("La entrada LDP1 debe ser un ArrayBuffer o una vista");
  const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
  if (bytes.byteLength < 8 || String.fromCharCode(...bytes.subarray(0, 4)) !== "LDP1") {
    throw new Error("La trama LDP1 no es válida");
  }

  const manifestLength = view.getUint32(4, false);
  if (manifestLength > maxManifestBytes || 8 + manifestLength > bytes.byteLength) {
    throw new Error("La longitud del manifiesto no es válida");
  }
  const decoder = new TextDecoder("utf-8", { fatal: true });
  const manifest = JSON.parse(decoder.decode(bytes.subarray(8, 8 + manifestLength)));
  if (!manifest || typeof manifest !== "object" || !Array.isArray(manifest.payloads)) {
    throw new Error("payloads del manifiesto debe ser una lista");
  }

  let offset = 8 + manifestLength;
  const payloads = new Map();
  for (const item of manifest.payloads) {
    if (
      !item ||
      typeof item.id !== "string" ||
      item.id.length === 0 ||
      !Number.isSafeInteger(item.size) ||
      item.size < 0 ||
      payloads.has(item.id)
    ) {
      throw new Error("Los metadatos payload del manifiesto no son válidos o están duplicados");
    }
    if (offset + 8 > bytes.byteLength) throw new Error("La longitud del payload está truncada");
    const length = view.getBigUint64(offset, false);
    offset += 8;
    if (length > BigInt(Number.MAX_SAFE_INTEGER)) throw new Error("El payload supera la longitud máxima admitida");
    if (length > BigInt(bytes.byteLength - offset)) throw new Error("Los bytes del payload están incompletos");
    if (item.size !== Number(length)) {
      throw new Error(`La longitud del payload ${item.id} no coincide con lo declarado`);
    }
    payloads.set(item.id, bytes.slice(offset, offset + Number(length)));
    offset += Number(length);
  }
  if (offset !== bytes.byteLength) throw new Error("Hay bytes sobrantes inesperados");
  return { manifest, payloads };
}

function prepareUploadItem(item) {
  if (item.kind === "text") {
    const bytes = new TextEncoder().encode(item.text);
    return {
      kind: "text",
      name: item.name,
      content_type: item.content_type || "text/plain; charset=utf-8",
      blob: new Blob([bytes], { type: "application/octet-stream" })
    };
  }
  if (item.kind === "file" && item.file instanceof Blob) {
    return {
      kind: "file",
      name: item.name || item.file.name,
      content_type: item.content_type || item.file.type || "application/octet-stream",
      blob: item.file
    };
  }
  throw new TypeError("Cada elemento debe ser de tipo texto o archivo e incluir un Blob");
}

async function uploadItems(items, csrfToken, onProgress, signal) {
  if (!Array.isArray(items) || items.length === 0) {
    throw new TypeError("Selecciona al menos un elemento");
  }
  const prepared = items.map(prepareUploadItem);

  const startResponse = await fetch("/api/uploads", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": csrfToken
    },
    body: JSON.stringify({
      items: prepared.map(item => ({
        kind: item.kind,
        name: item.name,
        size: item.blob.size,
        content_type: item.content_type
      }))
    }),
    signal
  });
  if (!startResponse.ok) throw new Error(`No se pudo iniciar la carga: HTTP ${startResponse.status}`);
  const started = await startResponse.json();
  if (!started.upload_id || !Array.isArray(started.items) || started.items.length !== prepared.length) {
    throw new Error("La respuesta de inicialización de la carga no es válida");
  }

  const chunkSize = started.chunk_size;
  if (!Number.isSafeInteger(chunkSize) || chunkSize <= 0 || chunkSize > TRANSFER_CHUNK_BYTES) {
    throw new Error("El servidor devolvió un tamaño de fragmento no válido");
  }
  let confirmedBytes = 0;
  const totalBytes = prepared.reduce((sum, item) => sum + item.blob.size, 0);

  for (let itemIndex = 0; itemIndex < prepared.length; itemIndex++) {
    const item = prepared[itemIndex];
    const itemId = started.items[itemIndex].item_id;
    if (!itemId) throw new Error(`Falta el identificador del elemento en la posición ${itemIndex}`);
    const totalChunks = Math.ceil(item.blob.size / chunkSize);

    for (let index = 0; index < totalChunks; index++) {
      const start = index * chunkSize;
      const end = Math.min(start + chunkSize, item.blob.size);
      const form = new FormData();
      form.append("chunk", item.blob.slice(start, end), item.name);

      await sendChunkWithRetry(
        `/api/uploads/${encodeURIComponent(started.upload_id)}/items/${encodeURIComponent(itemId)}/chunks/${index}`,
        form,
        csrfToken,
        index,
        signal
      );
      confirmedBytes += end - start;
      onProgress?.(confirmedBytes, totalBytes);
    }
  }

  const completeResponse = await fetch(
    `/api/uploads/${encodeURIComponent(started.upload_id)}/complete`,
    { method: "POST", headers: { "X-CSRFToken": csrfToken }, signal }
  );
  if (!completeResponse.ok) {
    throw new Error(`No se pudo finalizar la carga: HTTP ${completeResponse.status}`);
  }
  return completeResponse.json();
}
