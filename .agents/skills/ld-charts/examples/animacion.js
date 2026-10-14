// Bucle de animación con requestAnimationFrame (patrón de appDemo17/18/20/22) y comandos de voz.

// El movimiento se calcula por tiempo, no por fotograma: `posX += 10` va el doble de rápido en un
// monitor de 120 Hz. dibujar(dt, t) recibe segundos transcurridos desde el fotograma anterior.
function crearAnimacion(dibujar) {
  let id = null;
  let anterior = null;
  const reducir = window.matchMedia("(prefers-reduced-motion: reduce)");
  function fotograma(t) {
    const dt = anterior === null ? 0 : (t - anterior) / 1000;
    anterior = t;
    dibujar(dt, t);
    id = requestAnimationFrame(fotograma);
  }
  return {
    get activa() { return id !== null; },
    iniciar() {
      if (id !== null) return;
      if (reducir.matches) { dibujar(0, 0); return; }  // respeta "reducir movimiento": un solo fotograma
      anterior = null;
      id = requestAnimationFrame(fotograma);
    },
    detener() {
      if (id !== null) cancelAnimationFrame(id);
      id = null;
    },
  };
}
// Ejemplo (texto desplazándose a 600 px/s):
//   let x = -400;
//   const anim = crearAnimacion((dt) => {
//     ctx.fillStyle = "black"; ctx.fillRect(0, 0, ancho, alto);
//     ctx.fillStyle = "white"; ctx.font = "100px Arial"; ctx.fillText(mensaje, x, 300);
//     x = x < ancho ? x + 600 * dt : -400;
//   });
//   btnAnimar.onclick = () => { anim.activa ? anim.detener() : anim.iniciar(); btnAnimar.value = anim.activa ? "Detener" : "Animar"; };

// Comandos de voz con la API del navegador. Solo Chromium/Safari (webkitSpeechRecognition), requiere
// HTTPS o localhost y permiso del usuario; inícialo desde un clic. comandos = { "siri activar": fn, ... }
function crearComandosVoz(comandos, { idioma = "es-PE", alError = (e) => console.warn("Voz:", e) } = {}) {
  const Reconocedor = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!Reconocedor) return null;  // navegador sin soporte: la pantalla debe seguir funcionando con botones
  const r = new Reconocedor();
  r.lang = idioma;
  r.continuous = true;
  r.interimResults = false;
  r.onresult = (evento) => {
    const frase = evento.results[evento.results.length - 1][0].transcript.trim().toLowerCase();
    const accion = comandos[frase];
    if (accion) accion(frase);
  };
  r.onerror = (e) => alError(e.error);  // el demo usa alert() en cada error, también en "no-speech"
  return { iniciar: () => r.start(), detener: () => r.stop() };
}
