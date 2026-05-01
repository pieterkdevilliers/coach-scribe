# ---- base ----
FROM node:20-alpine AS base
WORKDIR /app
COPY package.json package-lock.json ./

# ---- dev ----
FROM base AS dev
RUN npm install
COPY . .
CMD ["npm", "run", "dev"]

# ---- build ----
FROM base AS build
RUN npm install
COPY . .
RUN npm run build

# ---- production ----
FROM node:20-alpine AS production
WORKDIR /app
COPY --from=build /app/.output ./output
CMD ["node", "./output/server/index.mjs"]
