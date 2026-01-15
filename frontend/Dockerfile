# Frontend Dockerfile (Multi-stage build for Bun)
FROM oven/bun:1 AS base
WORKDIR /app

# Install dependencies
FROM base AS install
RUN mkdir -p /temp/deps
COPY package.json bun.lock* /temp/deps/
RUN cd /temp/deps && bun install --frozen-lockfile
RUN mkdir /temp/node_modules && mv /temp/deps/node_modules/* /temp/node_modules/
RUN mv /temp/node_modules /app/node_modules

# Build application
FROM base AS build
COPY --from=install /app/node_modules /app/node_modules
COPY . .
RUN bun run build

# Production image
FROM base AS prod
COPY --from=build /app/.output ./
COPY --from=build /app/node_modules ./node_modules

ENV NODE_ENV=production
ENV PORT=3000

EXPOSE 3000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:3000/ || exit 1

CMD ["bun", "run", "start"]
