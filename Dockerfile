# syntax=docker/dockerfile:1.7

# ---------- stage 1: install ilspycmd into a portable folder ----------
# NOTE: ilspycmd 10.0.* on NuGet ships a broken package (missing
# DotnetToolSettings.xml). Pin to the known-good 9.0.* line, which targets net8.0.
FROM mcr.microsoft.com/dotnet/sdk:8.0 AS tool-builder
RUN dotnet tool install ilspycmd \
        --tool-path /opt/dotnet-tools \
        --version 9.0.*

# ---------- stage 2: runtime image (Python + .NET runtime + tool) ----------
# Match the .NET 8 runtime that ilspycmd 9.0.* targets.
FROM mcr.microsoft.com/dotnet/runtime:8.0

RUN apt-get update && apt-get install -y --no-install-recommends \
        python3 python3-pip python3-venv \
        util-linux \
    && rm -rf /var/lib/apt/lists/*

COPY --from=tool-builder /opt/dotnet-tools /opt/dotnet-tools
ENV PATH="/opt/dotnet-tools:${PATH}"

WORKDIR /app
COPY pyproject.toml README.md ./
COPY src/ ./src/
# Install our MCP server plus mcpo (the OpenAPI front-end). One image, two
# possible entrypoints: the default runs the MCP server; docker-compose's
# `mcpo` service overrides ENTRYPOINT to run mcpo against it.
RUN python3 -m pip install --no-cache-dir --break-system-packages . mcpo

RUN mkdir -p /workspace

# Entrypoint detects the bind-mounted workspace's UID/GID at runtime, then
# drops privileges via setpriv so files written into the workspace come back
# owned by the host user — no HOST_UID env var, no chown gymnastics.
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

ENV ILSPY_WORKSPACE=/workspace \
    MCP_HOST=0.0.0.0 \
    MCP_PORT=8000

EXPOSE 8000
ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
