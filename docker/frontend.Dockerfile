FROM node:20.9-bookworm-slim

WORKDIR /workspace

COPY package.json package-lock.json ./
COPY frontend/package.json frontend/package.json
RUN npm ci

CMD ["npm", "--workspace", "frontend", "run", "dev", "--", "--hostname", "0.0.0.0"]
