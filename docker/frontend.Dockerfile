# SGW Resilience Platform — frontend image (Next.js production build).
#
# Build context is the repository root. The browser talks only to this origin; the
# server-side rewrite forwards /api to the backend service named by API_ORIGIN at
# START time — same-origin in the browser, no CORS, cookie stays SameSite=Strict.

FROM node:22-alpine AS build
WORKDIR /app
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend ./
# Next evaluates rewrites() at BUILD time and bakes the destination into the routes
# manifest — `next start` does not re-read it. So the backend's service name is fixed
# here, not at runtime; override the ARG if the service is ever renamed.
ARG API_ORIGIN=http://backend:8000
ENV API_ORIGIN=$API_ORIGIN
RUN npm run build

FROM node:22-alpine
WORKDIR /app
ENV NODE_ENV=production
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --omit=dev && npm cache clean --force
COPY --from=build /app/.next ./.next
COPY frontend/next.config.mjs ./

EXPOSE 3000

CMD ["npm", "run", "start"]
