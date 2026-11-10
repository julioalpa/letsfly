# buscador-vuelos

Buscador personal de vuelos baratos con historial de precios y alertas.
Django + PostgreSQL, fuente de datos: Ignav.

## Cómo funciona

1. Cargás **rutas** en el admin (origen, destino, ventana de fechas, filtros y reglas de alerta).
2. Un comando (`poll_routes`) corre todos los días. Por cada fecha de la ventana pide tarifas a Ignav.
3. Se guarda el precio más bajo de cada fecha (`PriceObservation`). Ese historial es lo que permite calcular promedios.
4. Se evalúan las reglas: precio por debajo de X, o X% debajo del promedio histórico.
5. Si hay un mínimo nuevo, se manda aviso por Telegram (o por consola). Cada aviso queda registrado (`Notification`) para no repetirlo.

## Puesta en marcha (local, con SQLite)

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # completar IGNAV_API_KEY
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver    # admin en http://localhost:8000/admin/
```

Variables de entorno: el proyecto lee `.env` sólo si lo exportás (`set -a; source .env; set +a`) o usás docker compose.

## Con Docker + Postgres

```bash
cp .env.example .env
docker compose up --build
docker compose exec web python manage.py createsuperuser
```

## Consultar precios (a mano o programado)

```bash
python manage.py poll_routes                # todas las rutas activas
python manage.py poll_routes --route 1      # una sola
```

Ejemplo de cron (todos los días a las 7:00, con docker compose):

```cron
0 7 * * * cd /ruta/al/proyecto && docker compose run --rm web python manage.py poll_routes
```

## Tests

```bash
python manage.py test flights
```

## Consumo de requests: hacer la cuenta antes

Cada fecha de la ventana es una request. Requests por corrida = rutas activas × fechas de la ventana.
Ejemplo: 5 rutas × 14 fechas × 1 corrida diaria = 70 requests por día. Revisá el pricing de Ignav antes de subir la frecuencia.

## Pendientes conocidos

- **Formato de `airlines_include`**: no quedó claro en la doc si Ignav espera lista o string. Está marcado con TODO en `flights/providers/ignav.py`. Probarlo contra la API real con una aerolínea.
- **Links de reserva**: el cliente todavía no llama al endpoint de booking links. Se puede agregar cuando haya un aviso que mandar con enlace directo.
- **Monedas**: se comparan precios sólo dentro de la misma moneda. Ignav no documenta un parámetro de moneda, así que conviene ver qué devuelve en la práctica.
- **Cobertura**: confirmar que las aerolíneas low cost que te interesan aparezcan en las respuestas.
- **Despliegue**: falta definir dónde corre (AWS, por ejemplo) y cómo se programa la corrida diaria allí.
- **Postgres**: la configuración está pensada para docker compose; los tests corren en SQLite.
