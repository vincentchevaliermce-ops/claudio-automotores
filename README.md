# Claudio Automotores Junín · sitio web

Sitio de una página para Claudio Automotores (Av. Libertad 481, Junín). El stock se actualiza solo cada hora desde las publicaciones activas de Mercado Libre de la agencia: un auto vendido en Mercado Libre desaparece del sitio, un auto publicado aparece.

## Cómo funciona
- `index.html` lee `stock.json` y muestra los autos (filtros, búsqueda, ficha con fotos, botón de WhatsApp con el mensaje armado).
- `.github/workflows/sync-ml.yml` corre cada hora, llama a `scripts/sync_ml.py` y publica el `stock.json` nuevo si cambió.
- Si Mercado Libre no responde, el sitio conserva el stock anterior (nunca queda vacío).
- Los precios no se muestran: cada auto dice «Consultar» y lleva a WhatsApp.

## Secretos del repositorio (Settings → Secrets and variables → Actions)
| Nombre | Qué es |
|---|---|
| `ML_CLIENT_ID` | App ID de la aplicación creada en developers.mercadolibre.com.ar |
| `ML_CLIENT_SECRET` | Clave secreta de esa aplicación |
| `ML_REFRESH_TOKEN` | Lo carga solo el workflow «Conectar Mercado Libre» |
| `GH_PAT` | Token de GitHub con permiso para escribir secretos de este repositorio |

## Actualizar a mano
Actions → «Stock desde Mercado Libre» → Run workflow.
