# Frontend React/Vite — SSQM: build reprodutível + servir estático via nginx.
# Substitui o Firebase Hosting por um container portável (VPS/K8s/Cloud Run).
FROM node:20-alpine AS build

WORKDIR /app

# A base da API é injetada no build (consumo SOMENTE via API — sem RTDB direto).
ARG VITE_API_URL=/api
ENV VITE_API_URL=$VITE_API_URL

COPY package*.json ./
RUN npm ci || npm install
COPY . .
RUN npm run build

# --- estágio de runtime ---
FROM nginx:1.27-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
