# Fundación Juventud que Transforma — Sitio Web

Sitio web institucional de la **Fundación Juventud que Transforma** (Chigorodó, Antioquia — Urabá), desplegado como sitio estático.

## Stack

- HTML + CSS + JS autocontenidos, exportados desde Claude Design.
- **No requiere build step ni Node.js en producción**: fuentes, imágenes y scripts (incluyendo React/ReactDOM) van embebidos como datos codificados dentro de `public/index.html` y se desempaquetan en el navegador del visitante.
- Servido en producción con **Nginx** (imagen `nginx:alpine`, ver `Dockerfile`).

## Estructura

```
public/
  index.html     # sitio completo: HTML + CSS + JS + assets embebidos
Dockerfile       # imagen nginx:alpine lista para producción
nginx.conf       # configuración de nginx (gzip, cache, headers de seguridad)
.dockerignore
.gitignore
```

## Desarrollo local

Basta con abrir `public/index.html` en un navegador moderno y actualizado (Chrome, Edge o Firefox recientes; requiere soporte de `DecompressionStream`), o servirlo con cualquier servidor estático:

```bash
npx serve public
```

## Build de producción (Docker)

```bash
docker build -t fundacion-juventud-transforma-web .
docker run -p 8080:80 fundacion-juventud-transforma-web
```

Luego visita `http://localhost:8080`.

## Despliegue en Easypanel

Este repositorio incluye un `Dockerfile` en la raíz, por lo que Easypanel puede construir la imagen directamente desde GitHub sin configuración adicional (no requiere variables de entorno ni comandos de build manuales).

Pasos generales (ver detalle completo en la conversación de despliegue del proyecto):

1. Crear un nuevo servicio tipo **App** en Easypanel.
2. Conectar este repositorio de GitHub y seleccionar la rama `main`.
3. Método de build: **Dockerfile** (detectado automáticamente en la raíz del repo).
4. Puerto interno del contenedor: `80`.
5. Activar **Auto Deploy** en push a `main`.
6. Desplegar y usar el dominio temporal `*.easypanel.host` generado por el servicio.

No se ha configurado ningún dominio personalizado todavía; el sitio se sirve inicialmente bajo la URL temporal de Easypanel.

## Contacto de la fundación

- Correo: fundajutrans@gmail.com
- WhatsApp: +57 312 578 5054
- Instagram: [@fundajutrans](https://www.instagram.com/fundajutrans)
- Facebook: [Juventud que Transforma](https://www.facebook.com/JuventudQueTransforma)
- TikTok: [@fundajutrans](https://www.tiktok.com/@fundajutrans)
