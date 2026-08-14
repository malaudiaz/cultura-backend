# FastAPI + PostgreSQL con Docker

## Inicio rápido

1. Crea la configuración local:

   ```bash
   cp .env.example .env
   ```

2. Cambia `POSTGRES_PASSWORD` en `.env` y levanta los servicios:

   ```bash
   docker-compose up --build
   ```

3. Abre:

   - API: http://localhost:8000
   - Documentación Swagger: http://localhost:8000/docs
   - Estado de API y base de datos: http://localhost:8000/health

Si tu instalación incluye el plugin oficial de Compose, también puedes usar
`docker compose` en lugar de `docker-compose`.

Para detener los servicios usa `docker-compose down`. Para eliminar también los
datos persistentes de PostgreSQL usa `docker-compose down -v`.

La API accede a PostgreSQL dentro de la red de Compose mediante `db:5432`.
Desde el host, PostgreSQL se publica en el puerto definido por `POSTGRES_PORT`
(por defecto `5233`), por ejemplo `localhost:5233`.

## Migraciones y semilla

Aplica el esquema con `alembic upgrade head`. Después, ejecuta
`python -m app.seed` para crear datos de desarrollo idempotentes (usuarios,
categoría, etiquetas y una noticia). Configura `SEED_ADMIN_PASSWORD` para
cambiar la contraseña predeterminada `change-me`.

## Autenticación

Configura en `.env` una clave `JWT_SECRET` larga y aleatoria. Para el acceso
social añade también las credenciales de tus aplicaciones de Google y Meta:

```env
GOOGLE_CLIENT_ID=tu_cliente_web.apps.googleusercontent.com
FACEBOOK_APP_ID=tu_app_id
FACEBOOK_APP_SECRET=tu_app_secret
CORS_ORIGINS=http://localhost:3000,http://localhost:5173
```

Endpoints disponibles:

- `POST /auth/register`: registro local con `email`, `name` y `password`.
- `POST /auth/login`: acceso local con `email` y `password`.
- `POST /auth/google`: registro o acceso con `{ "token": "ID_TOKEN" }`.
- `POST /auth/facebook`: registro o acceso con `{ "token": "ACCESS_TOKEN" }`.

Los cuatro endpoints devuelven un JWT en `access_token`. El frontend debe
obtener el ID token de Google o el access token de Facebook mediante los SDK
oficiales y enviarlo al endpoint correspondiente. Prueba los cuerpos y revisa
las respuestas interactivamente en http://localhost:8000/docs.

## Roles

Todo usuario nuevo recibe el rol `usuario`. Los roles disponibles son
`administrador`, `editor`, `redactor` y `usuario`.

Rutas protegidas:

- `GET /users/me`: devuelve el usuario autenticado y su rol.
- `GET /users`: lista usuarios; requiere el rol `administrador`.
- `PATCH /users/{user_id}/role`: cambia un rol; requiere el rol
  `administrador`. Cuerpo: `{ "role": "editor" }`.

Envía el JWT en las rutas protegidas mediante la cabecera
`Authorization: Bearer <access_token>`.

## Galería de imágenes

Las imágenes se guardan en el volumen Docker `gallery_media`, se convierten a
WebP comprimido y se publican bajo `/media/<archivo>.webp`. La variable
`IMAGE_STORAGE_PATH` permite cambiar la ruta de almacenamiento (en Docker usa
por defecto `/app/media`).

Rutas públicas:

- `GET /gallery/categories`: lista categorías.
- `GET /gallery/images?page=1&category_id=<uuid>`: lista imágenes, con filtro
  de categoría opcional y 10 resultados por página.

Los roles `administrador` y `editor` pueden crear, renombrar y borrar
categorías, además de borrar imágenes. Los roles `administrador`, `editor` y
`redactor` pueden cargar imágenes o videos con `POST /gallery/images`
(formulario con `category_id` y uno o más campos `files`). Una categoría con
imágenes no se puede eliminar.

Cada imagen registra el usuario autenticado que la cargó. Las respuestas de
`POST /gallery/images` y `GET /gallery/images` incluyen `uploaded_by_id` y
`uploaded_by_name`.

También se admiten videos promocionales MP4 en la misma carga. Deben durar de
15 a 30 segundos y pesar de 3 a 8 MB; se validan con `ffprobe` y se conservan
en su formato original bajo `/media/<archivo>.mp4`. Cada elemento devuelve
`media_type` (`image` o `video`) y, para videos, `duration_seconds`.

## Noticias

Las noticias publicadas se consultan mediante `GET /news` y
`GET /news/slug/{slug}`. Los roles `administrador`, `editor` y `redactor`
pueden crear y editar noticias; el autor puede enviarlas a revisión con
`POST /news/{news_id}/submit`. Los roles `administrador` y `editor` pueden
aprobar o rechazar (`POST /news/{news_id}/review`) y publicar
(`POST /news/{news_id}/publish`).

Las secciones se gestionan con `POST`, `PATCH` y `DELETE` bajo
`/news/{news_id}/sections`. Las etiquetas se listan en `GET /news/tags` y las
gestionan administradores y editores mediante `POST`, `PATCH` y `DELETE`.
