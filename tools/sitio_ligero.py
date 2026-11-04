#!/usr/bin/env python3
"""Aligera index.html de cazaofertas.vip.

Las fotos de los productos llegan incrustadas (data:image/...;base64) dentro del
JSON <script type="application/json" id="ofertas-data">. Eso hace que la página
pese varios MB y tarde mucho en abrir en celular.

Este script:
  1. Guarda cada foto incrustada como archivo en fotos/<hash>.jpg (el nombre es
     un hash del contenido, así una foto nueva nunca choca con una vieja en caché).
  2. Cambia el campo "img" de cada producto por la ruta "fotos/<hash>.jpg".
  3. Borra de fotos/ los archivos que ya ningún producto usa.

Es seguro correrlo varias veces: si una foto ya es una ruta, la deja igual.
Uso: python3 tools/sitio_ligero.py [ruta/a/index.html]
"""
import base64
import hashlib
import json
import os
import re
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDEX = sys.argv[1] if len(sys.argv) > 1 else os.path.join(RAIZ, "index.html")
CARPETA = os.path.join(os.path.dirname(os.path.abspath(INDEX)), "fotos")

ETIQUETA = re.compile(
    r'(<script type="application/json" id="ofertas-data">)(.*?)(</script>)', re.S
)
DATA_URI = re.compile(r"^data:image/(jpeg|jpg|png|webp);base64,(.+)$", re.S)
EXT = {"jpeg": "jpg", "jpg": "jpg", "png": "png", "webp": "webp"}


def main():
    with open(INDEX, encoding="utf-8") as f:
        html = f.read()

    m = ETIQUETA.search(html)
    if not m:
        sys.exit("No encontré el bloque ofertas-data en " + INDEX)

    datos = json.loads(m.group(2))
    os.makedirs(CARPETA, exist_ok=True)

    usados, nuevos = set(), 0
    for p in datos.get("productos", []):
        img = p.get("img") or ""
        d = DATA_URI.match(img)
        if d:
            binario = base64.b64decode(d.group(2))
            nombre = hashlib.sha1(binario).hexdigest()[:16] + "." + EXT[d.group(1)]
            ruta = os.path.join(CARPETA, nombre)
            if not os.path.exists(ruta):
                with open(ruta, "wb") as f:
                    f.write(binario)
                nuevos += 1
            p["img"] = "fotos/" + nombre
        if p.get("img", "").startswith("fotos/"):
            usados.add(os.path.basename(p["img"]))

    borrados = 0
    for archivo in os.listdir(CARPETA):
        if archivo not in usados:
            os.remove(os.path.join(CARPETA, archivo))
            borrados += 1

    # Mismo formato que usa la actualización diaria: "<" escapado como <.
    texto = json.dumps(datos, ensure_ascii=False).replace("<", "\\u003c")
    html = html[: m.start(2)] + texto + html[m.end(2):]

    with open(INDEX, "w", encoding="utf-8") as f:
        f.write(html)

    print(
        f"Listo: {len(usados)} fotos en uso, {nuevos} nuevas, {borrados} borradas. "
        f"index.html ahora pesa {len(html.encode('utf-8')) // 1024} KB."
    )


if __name__ == "__main__":
    main()
