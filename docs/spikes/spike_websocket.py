from flask import Flask, render_template_string
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.config["SECRET_KEY"] = "spike_test"
socketio = SocketIO(app)

HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>SPIKE-001 — WebSockets Quinuaq</title>
    <script src="https://cdn.socket.io/4.7.2/socket.io.min.js"></script>
    <style>
        body { font-family: 'Segoe UI', sans-serif; background: #f0f0f0;
               display: flex; align-items: center; justify-content: center;
               min-height: 100vh; margin: 0; }
        .card { background: #fff; border-radius: 16px; padding: 32px;
                width: 420px; border: 1px solid #e0e0e0; }
        h2 { font-size: 16px; margin-bottom: 4px; }
        p  { font-size: 12px; color: #888; margin-bottom: 20px; }
        .log { background: #1e1e1e; border-radius: 8px; padding: 16px;
               min-height: 160px; margin-bottom: 16px; }
        .log-line { font-family: monospace; font-size: 12px;
                    margin-bottom: 6px; }
        .log-line.server { color: #4ec9b0; }
        .log-line.client { color: #ce9178; }
        .log-line.info   { color: #888; }
        button { padding: 10px 20px; background: #D85A30; color: #fff;
                 border: none; border-radius: 8px; font-size: 13px;
                 cursor: pointer; margin-right: 8px; }
        button:hover { background: #993C1D; }
        .status { display: inline-block; width: 8px; height: 8px;
                  border-radius: 50%; background: #ccc; margin-right: 6px; }
        .status.conectado { background: #1D9E75; }
        #estado { font-size: 12px; color: #888; margin-bottom: 16px;
                  display: flex; align-items: center; }
    </style>
</head>
<body>
<div class="card">
    <h2>SPIKE-001 — WebSockets</h2>
    <p>Prototipo de comunicación en tiempo real para Quinuaq</p>
    <div id="estado"><span class="status" id="dot"></span><span id="txt">Desconectado</span></div>
    <div class="log" id="log">
        <div class="log-line info">// esperando conexión...</div>
    </div>
    <button onclick="simularPedido()">Simular pedido a cocina</button>
    <button onclick="simularBebida()">Simular pedido al bar</button>
</div>

<script>
const socket = io();
const log    = document.getElementById("log");
const dot    = document.getElementById("dot");
const txt    = document.getElementById("txt");

function addLog(msg, tipo) {
    const d = document.createElement("div");
    d.className = "log-line " + tipo;
    d.textContent = "[" + new Date().toLocaleTimeString() + "] " + msg;
    log.appendChild(d);
    log.scrollTop = log.scrollHeight;
}

socket.on("connect", () => {
    dot.classList.add("conectado");
    txt.textContent = "Conectado — Socket ID: " + socket.id;
    addLog("Conexión WebSocket establecida con el servidor.", "info");
});

socket.on("disconnect", () => {
    dot.classList.remove("conectado");
    txt.textContent = "Desconectado";
    addLog("Conexión cerrada.", "info");
});

socket.on("nuevo_pedido_cocina", (data) => {
    addLog("COCINA recibió → Mesa " + data.mesa + ": " + data.items.join(", "), "server");
});

socket.on("nuevo_pedido_bar", (data) => {
    addLog("BAR recibió → Mesa " + data.mesa + ": " + data.items.join(", "), "server");
});

function simularPedido() {
    const payload = { mesa: 3, items: ["Lomo saltado", "Ceviche"] };
    addLog("Mozo envía a cocina → Mesa " + payload.mesa, "client");
    socket.emit("pedido_cocina", payload);
}

function simularBebida() {
    const payload = { mesa: 3, items: ["Pisco sour", "Chicha morada"] };
    addLog("Mozo envía al bar → Mesa " + payload.mesa, "client");
    socket.emit("pedido_bar", payload);
}
</script>
</body>
</html>
"""

@app.route("/spike")
def spike():
    return render_template_string(HTML)

@socketio.on("pedido_cocina")
def handle_cocina(data):
    print(f"[COCINA] Mesa {data['mesa']}: {data['items']}")
    emit("nuevo_pedido_cocina", data, broadcast=True)

@socketio.on("pedido_bar")
def handle_bar(data):
    print(f"[BAR] Mesa {data['mesa']}: {data['items']}")
    emit("nuevo_pedido_bar", data, broadcast=True)

if __name__ == "__main__":
    print("SPIKE-001 corriendo en http://127.0.0.1:5001/spike")
    socketio.run(app, debug=True, port=5001)