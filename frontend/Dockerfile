FROM node:20-alpine AS builder

WORKDIR /app

COPY frontend/package.json frontend/package-lock.json* ./

RUN npm install

COPY frontend ./

ARG NEXT_PUBLIC_API_BASE_URL=http://localhost:8888
ENV NEXT_PUBLIC_API_BASE_URL=$NEXT_PUBLIC_API_BASE_URL

RUN npm run build

FROM node:20-alpine AS runner

WORKDIR /app

ENV NODE_ENV=production
ENV PORT=3333

COPY --from=builder /app ./

EXPOSE 3333

CMD ["npm", "run", "start"]
