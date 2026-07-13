# 프론트엔드: Vite 로 정적 빌드 → vite preview 로 서빙(+ /api 프록시).
# nginx 없이 vite preview 하나가 정적 파일 서빙과 /api → backend 프록시를 처리한다.

# ── build stage ─────────────────────────────────────────────────────────────
FROM node:20-alpine AS build
WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .

# 빌드타임 주입: 실서버(/api) 사용 + BASE 는 상대경로(=vite preview 프록시로 감).
ENV VITE_USE_MOCK=false \
    VITE_API_BASE=
RUN npm run build

# ── runtime stage ───────────────────────────────────────────────────────────
FROM node:20-alpine AS run
WORKDIR /app

# vite preview 실행에 필요한 것: dist(정적 산출물) + vite(node_modules) + 설정.
COPY --from=build /app/node_modules ./node_modules
COPY --from=build /app/dist ./dist
COPY --from=build /app/package.json ./package.json
COPY --from=build /app/vite.config.ts ./vite.config.ts

EXPOSE 4173

# VITE_PROXY_TARGET 은 런타임 env(compose)로 주입 → vite.config 가 읽어 프록시.
CMD ["npx", "vite", "preview", "--host", "0.0.0.0", "--port", "4173"]
