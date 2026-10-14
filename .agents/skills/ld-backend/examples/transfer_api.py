"""API de referencia autenticada y basada en archivos para cargas por bloques.

Este ejemplo está pensado para un solo servidor. Un despliegue con varios
servidores necesita almacenamiento compartido y estado persistente de carga.
Configura MEDIA_ROOT y, para procesar texto, el ajuste
LD_UPLOAD_COMPLETION_HANDLER descrito en transfer-contract.md.
"""

import hashlib
import json
import logging
import os
import re
import tempfile
import uuid
from functools import wraps
from pathlib import Path

from django.conf import settings
from django.http import JsonResponse
from django.utils.module_loading import import_string
from django.views.decorators.http import require_POST

logger = logging.getLogger(__name__)

CHUNK_SIZE = 100 * 1024
MAX_ITEMS = 100
MAX_ITEM_BYTES = 2 * 1024 * 1024 * 1024
MAX_UPLOAD_BYTES = 5 * 1024 * 1024 * 1024
MAX_DISPLAY_NAME_LENGTH = 255


def _authenticated_json(view):
    """Exige un usuario autenticado y devuelve JSON en lugar de redirigir al inicio de sesión."""
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({"error": "se requiere autenticación"}, status=401)
        return view(request, *args, **kwargs)

    return wrapped


def _upload_root():
    media_root = getattr(settings, "MEDIA_ROOT", "")
    if not media_root:
        raise RuntimeError("Configura MEDIA_ROOT antes de habilitar las cargas")
    return (Path(media_root) / "ld-uploads").resolve()


def _safe_id(value):
    if isinstance(value, uuid.UUID):
        return str(value)
    try:
        parsed = uuid.UUID(value)
    except (ValueError, TypeError, AttributeError):
        return None
    return str(parsed) if str(parsed) == value.lower() else None


def _user_root(user):
    user_id = str(user.pk)
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", user_id):
        raise RuntimeError("La clave primaria del usuario no se puede usar como parte de la ruta")
    return _upload_root() / user_id


def _load_manifest(upload_dir, request):
    manifest_path = upload_dir / "manifest.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None, JsonResponse({"error": "carga no encontrada"}, status=404)
    if manifest.get("owner_id") != str(request.user.pk):
        return None, JsonResponse({"error": "carga no encontrada"}, status=404)
    return manifest, None


def _write_manifest(upload_dir, manifest):
    temporary = upload_dir / f".manifest-{uuid.uuid4().hex}.tmp"
    temporary.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
    os.replace(temporary, upload_dir / "manifest.json")


def _uploaded_chunk_sha256(uploaded_file):
    digest = hashlib.sha256()
    for block in uploaded_file.chunks():
        digest.update(block)
    return digest.digest()


def _file_sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while block := source.read(64 * 1024):
            digest.update(block)
    return digest.digest()


@require_POST
@_authenticated_json
def start_upload(request):
    """Crea metadatos aislados en el servidor para varios elementos de texto o archivo."""
    try:
        payload = json.loads(request.body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({"error": "el cuerpo de la solicitud debe ser JSON UTF-8"}, status=400)
    items = payload.get("items") if isinstance(payload, dict) else None
    if not isinstance(items, list) or not items or len(items) > MAX_ITEMS:
        return JsonResponse({"error": f"items debe contener entre 1 y {MAX_ITEMS} elementos"}, status=400)

    total_bytes = 0
    manifest_items = []
    for item in items:
        if not isinstance(item, dict):
            return JsonResponse({"error": "cada elemento debe ser un objeto"}, status=400)
        kind = item.get("kind")
        name = item.get("name")
        size = item.get("size")
        content_type = item.get("content_type", "application/octet-stream")
        if kind not in {"text", "file"}:
            return JsonResponse({"error": "kind debe ser text o file"}, status=400)
        if not isinstance(name, str) or not name.strip() or len(name) > MAX_DISPLAY_NAME_LENGTH:
            return JsonResponse({"error": "nombre de elemento no válido"}, status=400)
        if type(size) is not int or size < 0 or size > MAX_ITEM_BYTES:
            return JsonResponse({"error": "el tamaño del elemento está fuera del límite permitido"}, status=400)
        if not isinstance(content_type, str) or len(content_type) > 128:
            return JsonResponse({"error": "content_type no válido"}, status=400)

        total_bytes += size
        if total_bytes > MAX_UPLOAD_BYTES:
            return JsonResponse({"error": "la carga supera el límite total de tamaño"}, status=413)
        item_id = str(uuid.uuid4())
        manifest_items.append({
            "item_id": item_id,
            "kind": kind,
            "name": name,
            "content_type": content_type,
            "size": size,
            "chunk_size": CHUNK_SIZE,
            "chunk_count": (size + CHUNK_SIZE - 1) // CHUNK_SIZE,
        })

    upload_id = str(uuid.uuid4())
    upload_dir = _user_root(request.user) / upload_id
    try:
        upload_dir.mkdir(parents=True, exist_ok=False)
        (upload_dir / "items").mkdir()
        (upload_dir / "completed").mkdir()
        _write_manifest(upload_dir, {
            "upload_id": upload_id,
            "owner_id": str(request.user.pk),
            "status": "uploading",
            "items": manifest_items,
        })
    except OSError:
        logger.exception("No se pudo inicializar la carga")
        return JsonResponse({"error": "no se pudo inicializar la carga"}, status=500)

    return JsonResponse({
        "upload_id": upload_id,
        "chunk_size": CHUNK_SIZE,
        "items": [{"item_id": item["item_id"], "chunk_size": CHUNK_SIZE} for item in manifest_items],
    }, status=201)


@require_POST
@_authenticated_json
def receive_chunk(request, upload_id, item_id, index):
    """Valida y guarda atómicamente un fragmento del tamaño exacto para un elemento."""
    upload_id = _safe_id(upload_id)
    item_id = _safe_id(item_id)
    if upload_id is None or item_id is None:
        return JsonResponse({"error": "identificador de carga o elemento no válido"}, status=404)
    try:
        index = int(index)
    except (TypeError, ValueError):
        return JsonResponse({"error": "el índice del fragmento debe ser un entero"}, status=400)

    upload_dir = _user_root(request.user) / upload_id
    manifest, error = _load_manifest(upload_dir, request)
    if error:
        return error
    if manifest.get("status") != "uploading":
        return JsonResponse({"error": "la carga no está aceptando fragmentos"}, status=409)
    item = next((entry for entry in manifest["items"] if entry["item_id"] == item_id), None)
    if item is None or index < 0 or index >= item["chunk_count"]:
        return JsonResponse({"error": "elemento o índice de fragmento desconocido"}, status=400)

    expected_size = min(item["chunk_size"], item["size"] - index * item["chunk_size"])
    chunk = request.FILES.get("chunk")
    if chunk is None:
        return JsonResponse({"error": "falta el fragmento"}, status=400)
    if chunk.size != expected_size:
        return JsonResponse({"error": "el tamaño del fragmento no coincide con el rango esperado"}, status=400)

    chunk_dir = upload_dir / "items" / item_id / "chunks"
    target = chunk_dir / f"{index:08d}.part"
    lock = chunk_dir / f"{index:08d}.lock"
    lock_acquired = False
    try:
        chunk_dir.mkdir(parents=True, exist_ok=True)
        with lock.open("x", encoding="ascii"):
            lock_acquired = True
            if target.exists():
                if _file_sha256(target) == _uploaded_chunk_sha256(chunk):
                    return JsonResponse({
                        "received": True,
                        "index": index,
                        "duplicate": True,
                    })
                return JsonResponse(
                    {
                        "error": "el fragmento ya existe con contenido diferente",
                        "code": "chunk_conflict",
                    },
                    status=409,
                )
            with tempfile.NamedTemporaryFile(dir=chunk_dir, delete=False) as temporary:
                temporary_path = Path(temporary.name)
                for block in chunk.chunks():
                    temporary.write(block)
                temporary.flush()
                os.fsync(temporary.fileno())
            os.replace(temporary_path, target)
    except FileExistsError:
        return JsonResponse(
            {
                "error": "el fragmento todavía se está guardando",
                "code": "chunk_in_progress",
            },
            status=409,
        )
    except OSError:
        logger.exception("No se pudo guardar el fragmento de la carga")
        return JsonResponse({"error": "no se pudo guardar el fragmento"}, status=500)
    finally:
        if lock_acquired:
            lock.unlink(missing_ok=True)
        if "temporary_path" in locals():
            temporary_path.unlink(missing_ok=True)

    return JsonResponse({"received": True, "index": index})


@require_POST
@_authenticated_json
def complete_upload(request, upload_id):
    """Verifica todos los fragmentos, ensambla los elementos y ejecuta el manejador de datos configurado."""
    upload_id = _safe_id(upload_id)
    if upload_id is None:
        return JsonResponse({"error": "identificador de carga no válido"}, status=404)
    upload_dir = _user_root(request.user) / upload_id
    manifest, error = _load_manifest(upload_dir, request)
    if error:
        return error
    if manifest.get("status") == "completed":
        return JsonResponse({"status": "completed", "items": manifest["completed_items"]})
    if manifest.get("status") != "uploading":
        return JsonResponse({"error": "no se puede finalizar la carga"}, status=409)

    lock = upload_dir / "finalize.lock"
    lock_acquired = False
    try:
        with lock.open("x", encoding="ascii"):
            lock_acquired = True
            completed_items = []
            assembled = []
            for item in manifest["items"]:
                chunk_dir = upload_dir / "items" / item["item_id"] / "chunks"
                final_path = upload_dir / "completed" / f"{item['item_id']}.bin"
                temporary_path = final_path.with_suffix(".assembling")
                expected_paths = [
                    chunk_dir / f"{index:08d}.part"
                    for index in range(item["chunk_count"])
                ]
                if not all(path.is_file() for path in expected_paths):
                    return JsonResponse({"error": "faltan fragmentos de la carga"}, status=409)

                total_written = 0
                with temporary_path.open("wb") as destination:
                    for part_path in expected_paths:
                        with part_path.open("rb") as source:
                            while block := source.read(64 * 1024):
                                destination.write(block)
                                total_written += len(block)
                    destination.flush()
                    os.fsync(destination.fileno())
                if total_written != item["size"]:
                    temporary_path.unlink(missing_ok=True)
                    return JsonResponse({"error": "el tamaño ensamblado no coincide con el manifiesto"}, status=409)
                os.replace(temporary_path, final_path)
                assembled.append((item, final_path))
                completed_items.append({
                    "item_id": item["item_id"],
                    "kind": item["kind"],
                    "name": item["name"],
                    "size": total_written,
                })

            text_items = [item for item in manifest["items"] if item["kind"] == "text"]
            handler_path = getattr(settings, "LD_UPLOAD_COMPLETION_HANDLER", "")
            if text_items and not handler_path:
                return JsonResponse({"error": "no está configurado el manejador de procesamiento de texto"}, status=503)
            if handler_path:
                handler = import_string(handler_path)
                handler(upload_id, str(request.user.pk), assembled)

            manifest["status"] = "completed"
            manifest["completed_items"] = completed_items
            _write_manifest(upload_dir, manifest)
    except FileExistsError:
        return JsonResponse({"error": "la finalización de la carga ya está en curso"}, status=409)
    except Exception:
        logger.exception("No se pudo finalizar la carga")
        return JsonResponse({"error": "no se pudo finalizar la carga"}, status=500)
    finally:
        if lock_acquired:
            lock.unlink(missing_ok=True)

    return JsonResponse({"status": "completed", "items": completed_items})
