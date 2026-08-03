FROM node:22-alpine AS build
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm install
COPY . .
RUN npm run build
FROM node:22-alpine AS runtime
ENV NODE_ENV=production
RUN addgroup -S oracle && adduser -S oracle -G oracle
WORKDIR /app
COPY --from=build --chown=oracle:oracle /app/.next/standalone ./
COPY --from=build --chown=oracle:oracle /app/.next/static ./.next/static
USER oracle
EXPOSE 3000
CMD ["node", "server.js"]
