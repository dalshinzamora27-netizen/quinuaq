# Quinuaq — Sistema de gestión para restaurantes

![Tests](https://github.com/dalshinzamora27-netizen/quinuaq/actions/workflows/tests.yml/badge.svg)
![Python](https://img.shields.io/badge/python-3.12%2B-blue)
![Flask](https://img.shields.io/badge/flask-3.1-black)

Aplicación web para gestionar la atención de un restaurante en tiempo real: el mozo toma el pedido en la mesa, los platos aparecen al instante en el monitor de cocina y las bebidas en el del bar, y caja emite el comprobante (nota de venta, boleta o factura con IGV) aceptando pagos mixtos.

Proyecto desarrollado con **Scrum** en 6 sprints; cada funcionalidad corresponde a una historia de usuario (US-001 … US-019) y está cubierta por tests automatizados.

## Funcionalidades

| Rol | Qué puede hacer |
|---|---|
| **Mozo** | Ver el estado de las mesas en tiempo real, abrir comandas, agregar platos con notas ("sin cebolla"), enviarlos a cocina/bar y solicitar la cuenta. |
| **Cocinero** | Monitor con los platos de comida en orden de llegada; los avanza de *recibido → en proceso → listo*. |
| **Bartender** | Igual que cocina, pero solo con bebidas. |
| **Cajero** | Emitir nota de venta, boleta (DNI) o factura (RUC + razón social), con pagos mixtos (efectivo, tarjeta, Yape/Plin) y cierre de turno con cálculo de sobrante/faltante. |
| **Admin** | Dashboard con métricas del día, gestión de carta y usuarios, y reporte con el ranking de los 10 platos más vendidos por unidades o ingresos. Tiene acceso a todas las áreas. |

## Tecnologías

- **Backend:** Python, Flask (blueprints + application factory), Flask-SQLAlchemy, Flask-Login, Flask-WTF (CSRF)
- **Tiempo real:** Flask-SocketIO (WebSockets)
- **Base de datos:** SQL Server (producción) o SQLite (desarrollo y tests)
- **Frontend:** Jinja2, HTML, CSS (modo oscuro) y JavaScript
- **Calidad:** pytest (75 tests, ~89 % de cobertura) y GitHub Actions

## Aspectos técnicos destacados

- **Control de acceso por rol:** el decorador `@rol_requerido(...)` ([app/permisos.py](app/permisos.py)) protege cada ruta; un mozo no puede entrar a caja ni al panel de admin.
- **Dinero con `Decimal`:** todos los cálculos de subtotal, IGV y pagos usan `Decimal` con redondeo `ROUND_HALF_UP`, sin errores de punto flotante ([app/services/facturacion.py](app/services/facturacion.py)).
- **Flujo de estados de cada plato:** `pendiente → recibido → en_proceso → listo`. Un plato solo llega a cocina cuando el mozo lo envía y ya no se puede borrar después.
- **Zona horaria:** las fechas se guardan en UTC y los reportes "del día" se calculan en hora de Perú ([app/services/tiempo.py](app/services/tiempo.py)).
- **Seguridad:** contraseñas con hash, protección CSRF en todos los formularios y peticiones AJAX, y WebSockets solo para usuarios con sesión iniciada.
- **Tests aislados:** cada test corre sobre una base SQLite nueva con datos de demostración, así no dependen de ninguna base de datos real.

## Instalación

Requisitos: Python 3.12 o superior.

```bash
git clone https://github.com/dalshinzamora27-netizen/quinuaq.git
cd quinuaq

python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Linux / macOS

pip install -r requirements.txt
copy .env.example .env         # en Linux/macOS: cp .env.example .env
```

Por defecto usa SQLite, así que no hace falta instalar nada más. Para usar SQL Server, cambia `DATABASE_URL` en `.env` (hay un ejemplo en el archivo).

Crea las tablas y carga los datos de demostración:

```bash
python -m flask --app run seed
```

Inicia la aplicación y abre http://127.0.0.1:5000:

```bash
python run.py
```

### Usuarios de demostración

Contraseña de todos: `admin123`

| Rol | DNI |
|---|---|
| Admin | `00000000` |
| Mozo | `11111111` |
| Cocinero | `22222222` |
| Bartender | `33333333` |
| Cajero | `44444444` |

> Para ver el tiempo real, abre el mozo en una ventana y la cocina en otra ventana privada: al enviar un pedido aparece al instante en el monitor.

## Tests

```bash
pytest
pytest --cov=app          # con reporte de cobertura
```

## Estructura del proyecto

```
app/
├── __init__.py          # application factory
├── config.py            # configuración (lee .env)
├── permisos.py          # decorador @rol_requerido
├── sockets.py           # eventos de Socket.IO
├── cli.py               # comandos init-db y seed
├── models/              # Usuario, Rol, Mesa, Producto, Comanda, Venta, Pago...
├── routes/              # un blueprint por rol: auth, admin, mozo, cocina, bar, cajero
├── services/            # lógica de negocio: facturación, estaciones, tiempo
├── templates/
└── static/
tests/                   # tests por sprint + tests de regresión
scripts/backup_db.ps1    # respaldo automático de SQL Server (US-017)
docs/spikes/             # prueba de concepto de WebSockets (SPIKE-001)
```

## Autor

**Dalshin Zamora** — [GitHub](https://github.com/dalshinzamora27-netizen)
