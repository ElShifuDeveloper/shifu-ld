// Cliente WebSocket para chat/dibujo compartido (patrón de wsDemo02/03) con reconexión, JSON,
// token de sesión y sin insertar HTML. Complementa websocket-chat.js de ld-frontend.

// ws:// o wss:// según la página (desde https:// el navegador bloquea ws://) y host de la propia página:
// los demos fijan IPs (ws://172.20.10.2:9002, ws://190.43.83.241:9002) que fallan en otro equipo o red.
function urlWs(ruta = "/ws") {
  const proto = location.protocol === "https:" ? "wss:" : "ws:";
  return `${proto}//${location.host}${ruta}`;  // el proxy inverso reenvía /ws al servidor WebSocket
}

async function pedirToken(url = "ObtenerTokenWs") {
  const frm = new URLSearchParams();
  frm.append("csrfmiddlewaretoken", document.getElementsByName("csrfmiddlewaretoken")[0].value);
  const r = await fetch(url, { method: "POST", body: frm });
  if (!r.ok) throw new Error(r.status === 401 ? "sesion" : "token");
  return (await r.json()).token;
}

// alMensaje(objeto), alEstado("conectando" | "conectado" | "desconectado" | "sesion"|"error")
function crearCanal({ ruta = "/ws", alMensaje, alEstado = () => {}, maxReintentos = 8 }) {
  let socket = null;
  let intentos = 0;
  let cerradoPorUsuario = false;

  async function conectar() {
    alEstado("conectando");
    let token;
    try { token = await pedirToken(); }
    catch (e) { alEstado(e.message === "sesion" ? "sesion" : "error"); return; }  // sin sesión no se reintenta
    socket = new WebSocket(`${urlWs(ruta)}?token=${encodeURIComponent(token)}`);  // el token caduca: pide uno nuevo en cada intento
    socket.onopen = () => { intentos = 0; alEstado("conectado"); };
    socket.onmessage = (evento) => {
      let mensaje;
      try { mensaje = JSON.parse(evento.data); } catch { return; }  // ignora lo que no sea JSON
      if (mensaje && typeof mensaje === "object") alMensaje(mensaje);
    };
    socket.onclose = () => {
      alEstado("desconectado");
      if (cerradoPorUsuario || intentos >= maxReintentos) return;
      const espera = Math.min(30000, 500 * 2 ** intentos) * (0.5 + Math.random() / 2);  // retroceso exponencial con jitter
      intentos++;
      setTimeout(conectar, espera);
    };
  }

  conectar();
  return {
    // Devuelve false si no hay conexión: el llamador decide si avisa al usuario o descarta el mensaje.
    enviar(objeto) {
      if (!socket || socket.readyState !== WebSocket.OPEN) return false;
      socket.send(JSON.stringify(objeto));
      return true;
    },
    cerrar() { cerradoPorUsuario = true; if (socket) socket.close(); },
  };
}

// Limita la frecuencia de un evento continuo (mousemove del dibujo envía un mensaje por píxel en el demo).
function limitar(fn, ms) {
  let ultimo = 0;
  return (...args) => {
    const ahora = performance.now();
    if (ahora - ultimo >= ms) { ultimo = ahora; fn(...args); }
  };
}

// Pintar un mensaje de chat: textContent, nunca insertAdjacentHTML (el demo inserta el texto del
// otro usuario como HTML: cualquiera puede ejecutar código en todos los navegadores conectados).
function agregarMensajeChat(panel, { user, text, sent_at }) {
  const fila = document.createElement("div");
  const cab = document.createElement("strong");
  cab.textContent = `${user} · ${new Date(sent_at * 1000).toLocaleString()}`;
  const cuerpo = document.createElement("div");
  cuerpo.textContent = text;
  fila.append(cab, cuerpo, document.createElement("hr"));
  panel.prepend(fila);
}

// Uso (chat):
//   const canal = crearCanal({
//     alEstado: (e) => { spnEstado.textContent = e; },
//     alMensaje: (m) => { if (m.type === "chat.message") agregarMensajeChat(divPanel, m); },
//   });
//   btnEnviar.onclick = () => { if (!canal.enviar({ type: "chat.message", text: txtMensaje.value })) alert("Sin conexión"); };
// Uso (dibujo): canvas.onmousemove = limitar((e) => canal.enviar({ type: "paint.point", x: e.offsetX, y: e.offsetY, color: txtColor.value }), 40);
