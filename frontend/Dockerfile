# syntax=docker/dockerfile:1

# ---- Base ----
FROM node:18-alpine AS base
WORKDIR /app
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ .

# ---- Dev ----
FROM base AS dev
EXPOSE 5173
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:5173/ || exit 1
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]

# ---- Build ----
FROM base AS build
RUN npm run build

# ---- Production ----
FROM nginx:alpine AS production
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx/nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost/ || exit 1
