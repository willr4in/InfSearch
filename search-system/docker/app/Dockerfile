FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    g++-12 \
    cmake \
    make \
    ca-certificates \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY src/ /app/src/

# Создаём папку для сборки — пользователь может добавить CMakeLists.txt в src/
RUN mkdir -p /app/build || true

CMD ["bash"]
