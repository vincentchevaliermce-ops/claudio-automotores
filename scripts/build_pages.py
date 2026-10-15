"""Genera una página por auto (autos/<slug>.html), el sitemap y robots.txt a partir de stock.json.

Corre después de sync_ml.py en GitHub Actions. También agrega el campo "slug" a cada auto de stock.json,
que la página principal usa para el botón "Compartir".
La dirección pública del sitio se lee de site.config.json (site_url). Sin ella, las imágenes de vista previa
de WhatsApp no aparecen, así que conviene completarla apenas el sitio esté publicado.
"""
import html, json, os, re, shutil, unicodedata
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STOCK = os.path.join(ROOT, "stock.json")
OUT = os.path.join(ROOT, "autos")
WA = "5492364416575"


def cfg():
    try:
        return json.load(open(os.path.join(ROOT, "site.config.json"))).get("site_url", "").rstrip("/")
    except Exception:
        return ""


def slugify(s):
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")


def slug_for(a, used):
    base = slugify(" ".join(str(x) for x in [a.get("marca"), a.get("modelo"), a.get("version"), a.get("anio")] if x))[:70].strip("-")
    if re.match(r"^MLA\d+", str(a.get("id", "")), re.I):
        base = f"{base}-{str(a['id']).lower()}"
    s, n = base or slugify(a.get("id", "auto")), 2
    while s in used:
        s, n = f"{base}-{n}", n + 1
    used.add(s)
    return s


def e(x):
    return html.escape(str(x if x is not None else ""), quote=True)


def foto(f, base):
    """Ruta de una foto vista desde autos/. Las de Mercado Libre ya son absolutas."""
    if re.match(r"^https?://", f):
        return f, f
    rel = "../" + f.lstrip("./")
    return rel, (f"{base}/{f.lstrip('./')}" if base else rel)


def km_txt(a):
    if a.get("km") == 0:
        return "0 km"
    if a.get("km") is None:
        return None
    return f"{a['km']:,}".replace(",", ".") + " km reales"


def nombre(a):
    return f"{a.get('marca', '')} {a.get('modelo', '')}".strip()


def full(a):
    return " ".join(str(x) for x in [nombre(a), a.get("version"), a.get("anio")] if x)


def odo(a):
    km = a.get("km")
    if km == 0:
        return '<span class="odo zero"><span class="d"><em>0</em><em>K</em><em>M</em></span><small>sin uso</small></span>'
    if km is None:
        return ""
    s, lead, h = str(km).zfill(6), True, ""
    for i, c in enumerate(s):
        if c != "0" or i == len(s) - 1:
            lead = False
        h += f'<em{" class=z" if lead else ""}>{c}</em>'
    return f'<span class="odo"><span class="d">{h}</span><small>km reales</small></span>'


TEMPLATE = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "auto_template.html"), encoding="utf-8").read()


def page(a, otros, base):
    rel0, abs0 = foto(a["fotos"][0], base)
    url = f"{base}/autos/{a['slug']}.html" if base else ""
    rows = [("Año", a.get("anio")), ("Kilómetros", km_txt(a) or "Consultar"),
            ("Motor", a.get("motor") and f"{a['motor']} {a.get('combustible') or ''}".strip()),
            ("Caja", a.get("caja")), ("Tipo", a.get("carroceria")),
            ("Condición", "0 km" if a.get("condicion") == "0km" else "Usado seleccionado"),
            ("Precio", "Consultar por WhatsApp")]
    tbl = "".join(f"<dt>{e(k)}</dt><dd>{e(v)}</dd>" for k, v in rows if v)
    fotos = [foto(f, base)[0] for f in a["fotos"]]
    thumbs = "" if len(fotos) < 2 else "".join(
        f'<button type="button" data-src="{e(f)}" aria-label="Foto {i + 1}"{" aria-current=true" if i == 0 else ""}><img src="{e(f)}" alt="" loading="lazy"></button>'
        for i, f in enumerate(fotos))
    wa_txt = f"Hola Claudio, vi en la web el {full(a)}. ¿Sigue disponible?"
    cards = ""
    for o in otros:
        r, _ = foto(o["fotos"][0], base)
        cards += (f'<a class="mini" href="{e(o["slug"])}.html"><img src="{e(r)}" alt="{e(full(o))}" loading="lazy">'
                  f'<b>{e(nombre(o))}</b><small>{e(" · ".join(str(x) for x in [o.get("version"), o.get("anio")] if x))}</small></a>')
    desc = f"{full(a)}" + (f", {km_txt(a)}" if km_txt(a) else "") + ". En Claudio Automotores, Av. Libertad 481, Junín. Consultá por WhatsApp."
    ld = {"@context": "https://schema.org", "@type": "Car", "name": full(a),
          "brand": {"@type": "Brand", "name": a.get("marca")}, "model": a.get("modelo"),
          "vehicleModelDate": str(a.get("anio") or ""), "image": abs0, "description": desc,
          "itemCondition": "https://schema.org/NewCondition" if a.get("condicion") == "0km" else "https://schema.org/UsedCondition",
          "seller": {"@type": "AutoDealer", "name": "Claudio Automotores Junín", "telephone": "+54 236 442-4307",
                     "address": {"@type": "PostalAddress", "streetAddress": "Av. Libertad 481", "addressLocality": "Junín", "addressRegion": "Buenos Aires", "addressCountry": "AR"}}}
    if a.get("km") is not None:
        ld["mileageFromOdometer"] = {"@type": "QuantitativeValue", "value": a["km"], "unitCode": "KMT"}
    if a.get("caja"):
        ld["vehicleTransmission"] = a["caja"]
    if a.get("combustible"):
        ld["fuelType"] = a["combustible"]
    rep = {
        "{{TITLE}}": e(f"{full(a)} · Claudio Automotores Junín"),
        "{{DESC}}": e(desc), "{{OG_IMAGE}}": e(abs0), "{{URL}}": e(url),
        "{{CANONICAL}}": f'<link rel="canonical" href="{e(url)}">' if url else "",
        "{{LD}}": json.dumps(ld, ensure_ascii=False).replace("</", "<\\/"),
        "{{NOMBRE}}": e(nombre(a)), "{{VERSION}}": e(" · ".join(str(x) for x in [a.get("version"), a.get("anio")] if x)),
        "{{FULL}}": e(full(a)), "{{IMG0}}": e(rel0), "{{THUMBS}}": thumbs, "{{TBL}}": tbl,
        "{{ODO}}": odo(a), "{{PLATE}}": f'<span class="plate"><i>ARGENTINA</i><b>{e(a["anio"])}</b></span>' if a.get("anio") else "",
        "{{FLAG}}": '<span class="flag">0 km</span>' if a.get("condicion") == "0km" else "",
        "{{NOTA}}": f'<p class="nota">{e(a["nota"])}</p>' if a.get("nota") else "",
        "{{WA}}": e(f"https://wa.me/{WA}?text=" + urllib_quote(wa_txt)),
        "{{ML}}": f'<a class="btn btn-line" href="{e(a["ml_url"])}" target="_blank" rel="noopener">Ver la publicación en Mercado Libre</a>' if a.get("ml_url") else "",
        "{{SHARE_TXT}}": e(f"Mirá este {full(a)} en Claudio Automotores"),
        "{{OTROS}}": cards,
    }
    out = TEMPLATE
    for k, v in rep.items():
        out = out.replace(k, v)
    return out


def urllib_quote(s):
    from urllib.parse import quote
    return quote(s, safe="")


def main():
    data = json.load(open(STOCK, encoding="utf-8"))
    autos = [a for a in data.get("autos", []) if a.get("fotos") and a.get("marca")]
    used = set()
    for a in autos:
        a["slug"] = slug_for(a, used)
    base = cfg()
    if os.path.isdir(OUT):
        shutil.rmtree(OUT)
    os.makedirs(OUT)
    for a in autos:
        otros = sorted([o for o in autos if o is not a],
                       key=lambda o: (o.get("carroceria") != a.get("carroceria"), abs((o.get("anio") or 0) - (a.get("anio") or 0))))[:3]
        with open(os.path.join(OUT, a["slug"] + ".html"), "w", encoding="utf-8") as f:
            f.write(page(a, otros, base))
    with open(STOCK, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    if base:
        hoy = date.today().isoformat()
        urls = [f"{base}/"] + [f"{base}/autos/{a['slug']}.html" for a in autos]
        sm = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + \
             "".join(f"  <url><loc>{e(u)}</loc><lastmod>{hoy}</lastmod></url>\n" for u in urls) + "</urlset>\n"
        open(os.path.join(ROOT, "sitemap.xml"), "w").write(sm)
        open(os.path.join(ROOT, "robots.txt"), "w").write(f"User-agent: *\nAllow: /\nDisallow: /auth.html\nSitemap: {base}/sitemap.xml\n")
    print(f"{len(autos)} páginas de autos generadas" + ("" if base else " (falta site_url en site.config.json)"))


if __name__ == "__main__":
    main()
