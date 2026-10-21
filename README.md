# Fundación Juventud que Transforma — Sitio Web

Sitio web institucional de la **Fundación Juventud que Transforma** (Chigorodó, Antioquia — Urabá), desplegado como sitio estático en `https://fundajutrans.org`.

## Stack

- HTML estático en `public/index.html` más una carpeta `public/assets/` con fuentes, imágenes y scripts. **No hay build step ni Node.js en producción.**
- El diseño se exportó desde Claude Design. La página se hidrata en el navegador con el runtime de Claude Design (`assets/js/dc-runtime.*.js`) sobre React 18, que también va en `assets/js/`. No se carga nada de CDNs externos ni de Google Fonts: todo se sirve desde el propio dominio.
- Servido en producción con **Nginx** (imagen `nginx:1.27-alpine`, ver `Dockerfile` y `nginx.conf`).

## Estructura

```
public/
  index.html            # página completa: plantilla + datos (script text/x-dc) + estilos
  robots.txt
  sitemap.xml
  favicon.ico           # provisional, generado del logo embebido; reemplazar con el logo en alta
  assets/
    js/                 # dc-runtime, react, react-dom (nombres con hash o versión)
    fonts/              # Inter y Poppins, solo subconjuntos latin / latin-ext y pesos usados
    img/                # fotos en WebP q75 y logos; el nombre lleva un hash del contenido
tools/
  unbundle_claude_design.py   # convierte un export "bundle" de Claude Design en public/ + assets/
Dockerfile              # imagen nginx:alpine lista para producción
nginx.conf              # cache, gzip, cabeceras de seguridad y reglas de rutas
_fuentes/               # (ignorada por git) fotos originales y el export original de Claude Design
```

Los nombres de los activos llevan un hash del contenido (`hero-5.d45da33b.webp`), así que nginx los sirve con caché de un año e inmutable. Si cambias una imagen, cambia también el nombre y la referencia en `index.html`.

## Desarrollo local

Cualquier servidor estático sirve:

```bash
npx serve public
# o
python -m http.server 8080 --directory public
```

Abrir `public/index.html` directamente con `file://` no funciona del todo: el runtime carga React con `<script src>` y los navegadores bloquean parte de esas cargas desde disco.

## Reglas de nginx

- `/assets/…`: `Cache-Control: public, max-age=31536000, immutable`.
- `/index.html`: `Cache-Control: no-cache, must-revalidate`.
- Cualquier ruta con extensión que no exista responde **404** (nunca devuelve `index.html`).
- Las rutas limpias sin extensión (`/`, `/proyectos`) caen a `index.html`; cualquier otra cosa, 404.
- Las cabeceras `X-Content-Type-Options` y `X-Frame-Options` salen en todas las respuestas. Como `add_header` no se hereda dentro de un bloque que declare el suyo, se repiten en cada `location`.

## Si llega un nuevo export de Claude Design

El export de Claude Design es un único HTML con todo embebido en base64. Para pasarlo a esta estructura:

```bash
python tools/unbundle_claude_design.py export.html salida/
```

Eso produce `salida/index.html` y `salida/assets/`, equivalentes al export original. Después hay que volver a aplicar a mano los ajustes que este repositorio ya tiene sobre ese punto de partida:

1. Formularios «Quiero donar» y «Quiero ser voluntario» abren WhatsApp con el mensaje prellenado (método `abrirWhatsApp` en el script `text/x-dc`), no `mailto:`.
2. `<img>` normales con `alt` en lugar de `<image-slot>` (así no hace falta `dc-components.js`), e iniciales en Junta directiva para quien aún no tiene foto.
3. Metadatos: `lang="es"`, título, descripción, Open Graph, canonical, favicon.
4. Fuentes solo `latin`/`latin-ext` y pesos usados; fotos en WebP q75 con nombres descriptivos.
5. `1.º y 2.º` en el nombre del torneo, clase `fjt-tap` en los enlaces del pie.

Lo más práctico suele ser tratar `public/` como fuente de verdad y trasladar al HTML solo lo que cambió en el nuevo export.

## Build de producción (Docker)

```bash
docker build -t fundacion-juventud-transforma-web .
docker run -p 8080:80 fundacion-juventud-transforma-web
```

Luego visita `http://localhost:8080`.

## Despliegue en Easypanel

Este repositorio incluye un `Dockerfile` en la raíz, por lo que Easypanel puede construir la imagen directamente desde GitHub sin configuración adicional (no requiere variables de entorno ni comandos de build manuales).

1. Crear un nuevo servicio tipo **App** en Easypanel.
2. Conectar este repositorio de GitHub y seleccionar la rama `main`.
3. Método de build: **Dockerfile** (detectado automáticamente en la raíz del repo).
4. Puerto interno del contenedor: `80`.
5. Activar **Auto Deploy** en push a `main` (o desplegar a mano).
6. Dominio: `fundajutrans.org` (el `canonical`, el `sitemap.xml` y las etiquetas Open Graph ya apuntan ahí).

## Contacto de la fundación

- Correo: fundajutrans@gmail.com
- WhatsApp: +57 312 578 5054
- Instagram: [@fundajutrans](https://www.instagram.com/fundajutrans)
- Facebook: [Juventud que Transforma](https://www.facebook.com/JuventudQueTransforma)
- TikTok: [@fundajutrans](https://www.tiktok.com/@fundajutrans)
- NIT 901218232-8 · Representante legal: Sandra Cecilia Abadía Cortes
