FROM node:20-slim AS build
WORKDIR /app
COPY package.json ./
RUN npm install
COPY . .
RUN npm run build

# nginx, not `serve`: the static build has no dev-server proxy (vite.config.ts's
# proxy only exists under `vite`/`npm run dev`), so something has to forward
# /api/* to the backend container and handle SPA routing — see nginx.conf.
FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 5173
