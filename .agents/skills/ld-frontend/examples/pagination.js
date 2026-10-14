// Ejemplo de paginación por cursor. Sustituye la ruta y la función que representa las filas.
let nextCursor = null;
let loading = false;

async function loadNextPage() {
  if (loading || nextCursor === undefined) return;
  loading = true;
  try {
    const url = new URL("/api/orders", location.origin);
    url.searchParams.set("limit", "200");
    if (nextCursor) url.searchParams.set("cursor", nextCursor);

    const response = await fetch(url);
    if (!response.ok) throw new Error(`Error HTTP ${response.status}`);
    const page = await response.json();
    renderRows(page.items);
    nextCursor = page.next_cursor ?? undefined;
  } finally {
    loading = false;
  }
}
