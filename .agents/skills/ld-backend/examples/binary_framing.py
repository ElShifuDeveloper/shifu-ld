"""Codificador acotado de tramas LDP1 con manifiesto de texto y datos binarios."""

import json

MAX_MANIFEST_BYTES = 1024 * 1024
MAX_PAGE_BYTES = 16 * 1024 * 1024


def encode_ldp1_page(manifest, payloads, max_page_bytes=MAX_PAGE_BYTES):
    """Codifica una página limitada; para datos mayores usa descargas por separado y en flujo."""
    if not isinstance(manifest, dict) or not isinstance(manifest.get("payloads"), list):
        raise ValueError("El manifiesto debe incluir una lista payloads")
    if not isinstance(payloads, (list, tuple)):
        raise TypeError("payloads debe ser una lista o una tupla")
    if type(max_page_bytes) is not int or max_page_bytes < 8:
        raise ValueError("max_page_bytes debe ser un entero de al menos 8")
    if len(payloads) != len(manifest["payloads"]):
        raise ValueError("La cantidad de datos no coincide con el manifiesto")
    if any(not isinstance(metadata, dict) for metadata in manifest["payloads"]):
        raise ValueError("Cada elemento payload del manifiesto debe ser un objeto")
    payload_ids = [metadata.get("id") for metadata in manifest["payloads"]]
    if any(not isinstance(payload_id, str) or not payload_id for payload_id in payload_ids):
        raise ValueError("Cada elemento payload del manifiesto debe tener un id de texto no vacío")
    if len(set(payload_ids)) != len(payload_ids):
        raise ValueError("Los id de los payloads del manifiesto deben ser únicos")

    manifest_bytes = json.dumps(
        manifest, ensure_ascii=False, separators=(",", ":")
    ).encode("utf-8")
    if len(manifest_bytes) > MAX_MANIFEST_BYTES:
        raise ValueError("El manifiesto supera el tamaño máximo codificado")

    encoded_payloads = []
    total_size = 8 + len(manifest_bytes)
    if total_size > max_page_bytes:
        raise ValueError("La página completa supera el tamaño máximo codificado")
    for metadata, payload in zip(manifest["payloads"], payloads):
        if not isinstance(payload, (bytes, bytearray, memoryview)):
            raise TypeError("Cada payload debe ser de tipo bytes o compatible")
        payload_bytes = bytes(payload)
        if type(metadata.get("size")) is not int or metadata["size"] != len(payload_bytes):
            raise ValueError("El tamaño del payload no coincide con el manifiesto")
        total_size += 8 + len(payload_bytes)
        if total_size > max_page_bytes:
            raise ValueError("La página completa supera el tamaño máximo codificado")
        encoded_payloads.append(payload_bytes)

    if len(encoded_payloads) != len(manifest["payloads"]):
        raise ValueError("El manifiesto contiene un payload no compatible")
    frame = bytearray(b"LDP1")
    frame.extend(len(manifest_bytes).to_bytes(4, "big"))
    frame.extend(manifest_bytes)
    for payload in encoded_payloads:
        frame.extend(len(payload).to_bytes(8, "big"))
        frame.extend(payload)
    return bytes(frame)
