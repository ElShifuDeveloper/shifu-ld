// Ejemplo sencillo de chat de texto. Autentica y valida también los eventos en el servidor.
const socket = new WebSocket("ws://localhost:9002");

socket.addEventListener("open", () => setConnectionState("connected"));
socket.addEventListener("close", () => setConnectionState("disconnected"));
socket.addEventListener("error", () => setConnectionState("error"));
socket.addEventListener("message", ({ data }) => {
  const message = JSON.parse(data);
  if (message.type !== "chat.message") return;
  appendMessageAsText(message.user, message.text);
});

function sendChatMessage(user, text) {
  if (socket.readyState !== WebSocket.OPEN) {
    throw new Error("WebSocket no está conectado");
  }
  socket.send(JSON.stringify({
    type: "chat.message",
    sent_at: new Date().toISOString(),
    user,
    text
  }));
}
