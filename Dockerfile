# Build stage
# node:22 matches the toolchain the lockfile was resolved with. On node:20 the
# build died outright: `corepack enable` with no pinned version fetches the
# latest pnpm, which now requires a newer Node than the base image ships
# (F-31). package.json pins `packageManager` so corepack resolves the exact
# pnpm the lockfile was written by, rather than whatever shipped that morning.
FROM node:22-alpine AS builder

WORKDIR /app

# Install dependencies with the lockfile, so the image resolves exactly the
# tree that was tested. Previously this copied only package.json and ran
# `npm install`, ignoring both lockfiles entirely (F-26).
RUN corepack enable
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
RUN pnpm install --frozen-lockfile

# Copy source and build
COPY . .
RUN pnpm run build

# Production serve stage
FROM nginx:alpine

COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
