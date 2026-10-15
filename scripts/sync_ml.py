"""Sincroniza stock.json con las publicaciones activas de Mercado Libre de Claudio Automotores.

Corre cada hora en GitHub Actions. Necesita estos secretos del repositorio:
  ML_CLIENT_ID, ML_CLIENT_SECRET, ML_REFRESH_TOKEN
Mercado Libre entrega un refresh token nuevo en cada renovación (el anterior deja de servir),
así que el script lo escribe en new_refresh_token.txt y el workflow lo guarda de vuelta en el secreto.
"""
import json, os, re, sys, urllib.parse, urllib.request
from datetime import datetime, timezone

API = "https://api.mercadolibre.com"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "stock.json")


def call(path, data=None, token=None):
    req = urllib.request.Request(API + path if path.startswith("/") else path)
    req.add_header("Accept", "application/json")
    if token:
        req.add_header("Authorization", "Bearer " + token)
    if data is not None:
        req.data = urllib.parse.urlencode(data).encode()
        req.add_header("Content-Type", "application/x-www-form-urlencoded")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def renovar_token():
    r = call("/oauth/token", {
        "grant_type": "refresh_token",
        "client_id": os.environ["ML_CLIENT_ID"],
        "client_secret": os.environ["ML_CLIENT_SECRET"],
        "refresh_token": os.environ["ML_REFRESH_TOKEN"],
    })
    with open(os.path.join(ROOT, "new_refresh_token.txt"), "w") as f:
        f.write(r["refresh_token"])
    return r["access_token"]


def attr(item, *ids):
    for a in item.get("attributes", []):
        if a.get("id") in ids and a.get("value_name"):
            return a["value_name"]
    return None


CARROCERIAS = {"sedan": "Sedán", "sedán": "Sedán", "hatchback": "Hatchback", "suv": "SUV",
               "pick-up": "Pick-up", "pickup": "Pick-up", "monovolumen": "Monovolumen",
               "rural": "Rural", "coupé": "Coupé", "coupe": "Coupé", "furgón": "Utilitario",
               "utilitario": "Utilitario", "convertible": "Convertible"}


def a_auto(it):
    km_txt = attr(it, "KILOMETERS") or ""
    km = int(re.sub(r"\D", "", km_txt)) if re.search(r"\d", km_txt) else None
    anio_txt = attr(it, "VEHICLE_YEAR") or ""
    anio = int(anio_txt) if anio_txt.isdigit() else None
    cond = "0km" if (it.get("condition") == "new" or km == 0) else "usado"
    carro = (attr(it, "VEHICLE_BODY_TYPE") or "").strip()
    carro = CARROCERIAS.get(carro.lower(), carro or None)
    fotos = [p.get("secure_url") or p.get("url") for p in it.get("pictures", [])][:12]
    marca = attr(it, "BRAND") or ""
    modelo = attr(it, "MODEL") or ""
    return {
        "id": it["id"],
        "marca": marca,
        "modelo": modelo,
        "version": attr(it, "TRIM", "VERSION") or "",
        "titulo": it.get("title"),
        "anio": anio,
        "km": km,
        "motor": attr(it, "ENGINE", "ENGINE_DISPLACEMENT"),
        "combustible": attr(it, "FUEL_TYPE"),
        "caja": attr(it, "TRANSMISSION"),
        "carroceria": carro,
        "condicion": cond,
        "fotos": [f for f in fotos if f],
        "destacado": cond == "0km",
        "nota": None,
        "ml_url": it.get("permalink"),
        "precio": it.get("price"),
        "moneda": it.get("currency_id"),
    }


def main():
    token = renovar_token()
    me = call("/users/me", token=token)
    ids, offset = [], 0
    while True:
        r = call(f"/users/{me['id']}/items/search?status=active&limit=50&offset={offset}", token=token)
        ids += r.get("results", [])
        offset += 50
        if offset >= r.get("paging", {}).get("total", 0):
            break
    autos = []
    for i in range(0, len(ids), 20):
        lote = call("/items?ids=" + ",".join(ids[i:i + 20]), token=token)
        for x in lote:
            it = x.get("body", {})
            if x.get("code") == 200 and it.get("status") == "active":
                a = a_auto(it)
                if a["fotos"] and a["marca"]:
                    autos.append(a)
    if not autos:
        # Nunca vaciar el sitio por un error: si ML no devuelve nada, se deja el stock anterior.
        print("Mercado Libre no devolvió autos activos; stock.json sin cambios.")
        return
    nuevo = {"fuente": "Mercado Libre", "actualizado": datetime.now(timezone.utc).strftime("%Y-%m-%d"), "autos": autos}
    try:
        viejo = json.load(open(OUT))
    except Exception:
        viejo = {}
    sin_slug = lambda l: [{k: v for k, v in x.items() if k != "slug"} for x in (l or [])]
    if sin_slug(viejo.get("autos")) == autos:
        print(f"{len(autos)} autos, sin cambios.")
        return
    with open(OUT, "w") as f:
        json.dump(nuevo, f, ensure_ascii=False, indent=1)
    print(f"stock.json actualizado: {len(autos)} autos.")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("Error:", e)
        sys.exit(1)
