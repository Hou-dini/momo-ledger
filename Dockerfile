# Stage 1: Build the Next.js frontend
FROM node:20-alpine AS frontend-builder

WORKDIR /frontend

# Copy frontend dependency configurations
COPY ./frontend/package*.json ./
RUN npm ci

# Copy frontend source and compile static build files
COPY ./frontend/ ./
RUN npm run build

# Stage 2: Create python runtime
FROM python:3.12-slim

RUN pip install --no-cache-dir uv==0.8.13

WORKDIR /code

COPY ./pyproject.toml ./README.md ./uv.lock* ./
COPY ./app ./app

RUN uv sync --frozen

# Copy the statically compiled Next.js build output from the builder stage
COPY --from=frontend-builder /frontend/out ./static

ARG COMMIT_SHA=""
ENV COMMIT_SHA=${COMMIT_SHA}

ARG AGENT_VERSION=0.0.0
ENV AGENT_VERSION=${AGENT_VERSION}

EXPOSE 8080

CMD ["uv", "run", "uvicorn", "app.routes:app", "--host", "0.0.0.0", "--port", "8080"]