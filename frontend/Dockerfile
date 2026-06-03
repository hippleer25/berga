# Stage 1: Build
FROM node:20-slim AS frontend-builder
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm ci
COPY . .
RUN npm run build

# Stage 2: Serve
FROM nginx:alpine
COPY --from=frontend-builder /app/build /usr/share/nginx/html
RUN printf 'server {\n\
    listen 80;\n\
    root /usr/share/nginx/html;\n\
    index index.html;\n\
    location /sw.js {\n\
        add_header Cache-Control "no-cache, no-store, must-revalidate";\n\
        add_header Content-Type "application/javascript";\n\
    }\n\
    location /manifest.webmanifest {\n\
        add_header Content-Type "application/manifest+json";\n\
    }\n\
    location /api/ {\n\
        proxy_pass http://backend:5746;\n\
        proxy_set_header Host $host;\n\
        proxy_set_header X-Real-IP $remote_addr;\n\
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;\n\
        proxy_set_header X-Forwarded-Proto $scheme;\n\
    }\n\
    location / {\n\
        try_files $uri $uri/ /index.html;\n\
    }\n\
}\n' > /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]