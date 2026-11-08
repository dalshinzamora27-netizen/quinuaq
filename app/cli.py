"""Comandos de consola:  flask --app run init-db   |   flask --app run seed"""
import click
from app import db
from app.models import Rol, Usuario, Categoria, Producto, Mesa

PASSWORD_DEMO = "admin123"

ROLES = ["admin", "mozo", "cocinero", "bartender", "cajero"]

USUARIOS = [
    # dni,        nombre,    apellido,    rol
    ("00000000", "Admin",    "Principal", "admin"),
    ("11111111", "Carlos",   "Quispe",    "mozo"),
    ("22222222", "Rosa",     "Huamán",    "cocinero"),
    ("33333333", "Miguel",   "Mendoza",   "bartender"),
    ("44444444", "Lucía",    "Torres",    "cajero"),
]

CARTA = {
    ("Entradas", "comida"): [
        ("Papa a la huancaína", "Papa sancochada con crema de ají amarillo", "14.00"),
        ("Causa limeña",        "Causa rellena de pollo",                   "16.00"),
        ("Ocopa arequipeña",    "Papa con salsa de huacatay y maní",        "14.00"),
    ],
    ("Platos de fondo", "comida"): [
        ("Lomo saltado",   "Lomo fino salteado con papas fritas y arroz", "32.00"),
        ("Ají de gallina", "Gallina deshilachada en crema de ají",        "24.00"),
        ("Arroz con pollo","Arroz verde al culantro con presa de pollo",  "22.00"),
    ],
    ("Especiales", "comida"): [
        ("Puca picante", "Guiso ayacuchano de papa y beterraga con chicharrón", "26.00"),
        ("Cuy chactado", "Cuy frito con papas doradas y ensalada",               "45.00"),
    ],
    ("Postres", "comida"): [
        ("Mazamorra morada", "Postre de maíz morado y frutas", "8.00"),
        ("Arroz con leche",  "Con canela y clavo de olor",     "8.00"),
    ],
    ("Bebidas", "bebida"): [
        ("Chicha morada (jarra)", "Jarra de 1 litro",        "15.00"),
        ("Limonada frozen",       "Vaso de 500 ml",          "10.00"),
        ("Pisco sour",            "Clásico con pisco quebranta", "22.00"),
        ("Gaseosa personal",      "500 ml",                  "5.00"),
    ],
}

NUM_MESAS = 10


def cargar_datos_demo():
    """Inserta roles, usuarios, carta y mesas de demostracion. No duplica si ya existen."""
    if Rol.query.first():
        return False

    roles = {nombre: Rol(nombre=nombre) for nombre in ROLES}
    db.session.add_all(roles.values())

    for dni, nombre, apellido, rol in USUARIOS:
        u = Usuario(dni=dni, nombre=nombre, apellido=apellido, rol=roles[rol])
        u.set_password(PASSWORD_DEMO)
        db.session.add(u)

    for (cat_nombre, tipo), productos in CARTA.items():
        cat = Categoria(nombre=cat_nombre, tipo=tipo)
        db.session.add(cat)
        for nombre, desc, precio in productos:
            db.session.add(Producto(nombre=nombre, descripcion=desc, precio=precio, categoria=cat))

    for n in range(1, NUM_MESAS + 1):
        db.session.add(Mesa(numero=n, capacidad=2 if n <= 3 else (6 if n >= 9 else 4)))

    db.session.commit()
    return True


def registrar_comandos(app):
    @app.cli.command("init-db")
    def init_db():
        """Crea las tablas que no existan."""
        db.create_all()
        click.echo("Tablas creadas.")

    @app.cli.command("seed")
    def seed():
        """Crea las tablas y carga datos de demostracion."""
        db.create_all()
        if cargar_datos_demo():
            click.echo(f"Datos de demostración cargados. Contraseña de todos los usuarios: {PASSWORD_DEMO}")
        else:
            click.echo("La base de datos ya tenía datos; no se cargó nada.")
