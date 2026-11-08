// ===== CSRF =====
// Agrega el token CSRF a toda peticion fetch que modifique datos (POST, PUT, DELETE)
(function() {
    const meta = document.querySelector('meta[name="csrf-token"]');
    if (!meta) return;
    const token = meta.content;
    const fetchOriginal = window.fetch;
    window.fetch = function(url, opciones = {}) {
        const metodo = (opciones.method || "GET").toUpperCase();
        if (!["GET", "HEAD", "OPTIONS"].includes(metodo)) {
            opciones.headers = Object.assign({}, opciones.headers, { "X-CSRFToken": token });
        }
        return fetchOriginal(url, opciones);
    };
})();

// ===== MODO OSCURO =====
(function() {
    const toggle = document.getElementById("themeToggle");
    const saved = localStorage.getItem("quinuaq-theme") || "light";

    if (saved === "dark") {
        document.documentElement.setAttribute("data-theme", "dark");
        if (toggle) toggle.textContent = "☀️";
    }

    if (toggle) {
        toggle.addEventListener("click", () => {
            const current = document.documentElement.getAttribute("data-theme");
            if (current === "dark") {
                document.documentElement.removeAttribute("data-theme");
                localStorage.setItem("quinuaq-theme", "light");
                toggle.textContent = "🌙";
            } else {
                document.documentElement.setAttribute("data-theme", "dark");
                localStorage.setItem("quinuaq-theme", "dark");
                toggle.textContent = "☀️";
            }
        });
    }
})();