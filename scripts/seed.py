"""Datos de prueba para recorrer secciones, consultar ítems y combinar filtros."""

from db.models import Block, Entry, Item, Machine, Tag
from db.session import Session, init_db


def add_block(entry, title, items, *, parent=None):
    siblings = [block for block in entry.blocks if block.parent is parent]
    block = Block(title=title, parent=parent, position=len(siblings) + 1)
    entry.blocks.append(block)
    for position, item in enumerate(items, start=1):
        item.position = position
        block.items.append(item)
    return block


def seed(session):
    csv = Tag(name="CSV")
    sqlite = Tag(name="SQLite")
    inventario = Tag(name="inventario")
    taller = Machine(name="Taller", os="linux")
    escritorio = Machine(name="Escritorio", os="windows")

    ventas = Entry(
        title="Inspección de un CSV",
        description="Comprobaciones al recibir una exportación de ventas.",
        phase="enumeration", os="linux", tags=[csv, inventario], machines=[taller],
    )
    inspeccion = add_block(ventas, "Inspección inicial", [
        Item(kind="text", content="Revisa la cabecera y el tamaño del archivo recibido."),
    ])
    add_block(ventas, "Cabecera", [
        Item(kind="text", content="**Columnas esperadas**"),
        Item(kind="command", language="bash", content="head -n 1 ventas.csv"),
        Item(kind="text", content="Salida esperada\n\n```text\nfecha,total\n```"),
    ], parent=inspeccion)
    add_block(ventas, "Tamaño", [
        Item(kind="command", language="bash", content="wc -l ventas.csv"),
        Item(kind="note", content="El recuento incluye la cabecera."),
    ], parent=inspeccion)
    add_block(ventas, "Referencia visual", [
        Item(kind="image", content="imagenes/vista-previa-ventas.png"),
    ])

    catalogo = Entry(
        title="Consultar el catálogo de SQLite",
        description="Listado de tablas y columnas de una base de datos local.",
        phase="enumeration", os="multiplatform", tags=[sqlite, inventario],
        machines=[taller, escritorio],
    )
    add_block(catalogo, "Tablas", [
        Item(kind="command", language="sql",
             content="SELECT name\nFROM sqlite_schema\nWHERE type = 'table'\nORDER BY name"),
        Item(kind="note", content="La consulta devuelve una fila por tabla."),
    ])
    add_block(catalogo, "Columnas", [
        Item(kind="text", content="Desde la consola interactiva de SQLite"),
        Item(kind="command", content=".schema ventas"),
    ])

    glosario = Entry(
        title="Glosario de exportaciones",
        description="Términos que aparecen en los ficheros de intercambio.",
        phase="other", tags=[csv],
    )
    add_block(glosario, "Delimitador", [
        Item(kind="text", content="Carácter que separa los campos de un registro."),
    ])

    session.add_all([ventas, catalogo, glosario])


def main():
    init_db()
    with Session.begin() as session:
        seed(session)


if __name__ == "__main__":
    main()
