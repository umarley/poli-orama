FROM node:22-alpine

ENV PNPM_HOME=/pnpm
ENV PATH=$PNPM_HOME:$PATH

WORKDIR /app

RUN corepack enable && corepack prepare pnpm@11.7.0 --activate

COPY package.json pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile

COPY . .

EXPOSE 5173

CMD ["pnpm", "dev", "--host", "0.0.0.0"]
