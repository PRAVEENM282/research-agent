FROM node:22.14.0-alpine3.21 AS build
WORKDIR /web
COPY package.json ./
COPY package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY . .
RUN npm run build

FROM caddy:2.9.1-alpine AS runtime
COPY Caddyfile /etc/caddy/Caddyfile
COPY --from=build /web/dist /srv
RUN caddy validate --config /etc/caddy/Caddyfile
EXPOSE 80 443 443/udp
