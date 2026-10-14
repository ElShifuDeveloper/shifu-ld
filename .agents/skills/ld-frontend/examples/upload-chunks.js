// Carga transfer-workflows.js antes de este adaptador.
// La función para un archivo reutiliza el contrato de cargas mixtas.
async function uploadFile(file, csrfToken, onProgress, signal) {
  return uploadItems(
    [{ kind: "file", name: file.name, file }],
    csrfToken,
    onProgress,
    signal
  );
}
