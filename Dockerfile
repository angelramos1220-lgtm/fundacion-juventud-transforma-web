# Sitio estático de la Fundación Juventud que Transforma
# El export de Claude Design es un único HTML autocontenido
# (CSS, JS y assets embebidos), por lo que no requiere build step ni Node.js.

FROM nginx:1.27-alpine

RUN rm -rf /usr/share/nginx/html/*

COPY public/ /usr/share/nginx/html/
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
