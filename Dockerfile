# Multi-stage Dockerfile Template
# Optimisé pour la production avec une image minimale

# Arguments de build
ARG NODE_VERSION=22
ARG BUILD_DATE
ARG VCS_REF
ARG VERSION

# =====================================
# Stage 1: Dependencies
# =====================================
FROM node:${NODE_VERSION}-alpine AS dependencies

WORKDIR /app

# Installer les dépendances système si nécessaire
RUN apk add --no-cache \
    python3 \
    make \
    g++ \
    && rm -rf /var/cache/apk/*

# Copier les fichiers de dépendances
COPY package*.json ./

# Installer toutes les dépendances (dev + prod)
RUN npm ci --include=dev

# =====================================
# Stage 2: Builder
# =====================================
FROM node:${NODE_VERSION}-alpine AS builder

WORKDIR /app

# Copier les dépendances depuis le stage précédent
COPY --from=dependencies /app/node_modules ./node_modules
COPY . .

# Build de l'application (si nécessaire)
# Pas de build nécessaire pour ce projet Node.js simple

# =====================================
# Stage 3: Production
# =====================================
FROM node:${NODE_VERSION}-alpine AS production

# Métadonnées
LABEL maintainer="your-email@example.com"
LABEL org.opencontainers.image.created="${BUILD_DATE}"
LABEL org.opencontainers.image.revision="${VCS_REF}"
LABEL org.opencontainers.image.version="${VERSION}"
LABEL org.opencontainers.image.title="Your App Name"
LABEL org.opencontainers.image.description="Your app description"

WORKDIR /app

# Créer un utilisateur non-root pour la sécurité
RUN addgroup -g 1001 -S nodejs && \
    adduser -S nodejs -u 1001

# Copier uniquement les dépendances de production
COPY package*.json ./
RUN npm ci --omit=dev && \
    npm cache clean --force

# Copier le code source (projet sans build)
COPY --from=builder --chown=nodejs:nodejs /app/src ./src

# Changer l'utilisateur
USER nodejs

# Exposer le port (adapter selon votre application)
EXPOSE 3000

# Variables d'environnement
ENV NODE_ENV=production \
    PORT=3000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD node -e "require('http').get('http://localhost:3000/health', (r) => {process.exit(r.statusCode === 200 ? 0 : 1)})" || exit 1

# Démarrage de l'application
CMD ["node", "src/index.js"]
