# CAD toolchain for mechanical/: build123d (OpenCascade) and the check tools, headless. Notes: docs/dependencies.md
# Build: make cad-image    Use: make mech-test | mech-build | mech-check | mech-diff | mech-release
FROM ghcr.io/astral-sh/uv:0.13.10@sha256:a3ea1357342c1a4bf9a0c53a3deb1b55379aefa037338d8113d5771efa01774f AS uv

# python 3.13.18
FROM python:3.13-slim@sha256:7249d5587b78209a006dc4a3b5340678f84ea729239193aa559962cd8c1fce50
# OCP links libGL and X libraries also without a display
RUN apt-get update && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 libxrender1 libxext6 \
    && rm -rf /var/lib/apt/lists/*
COPY --from=uv /uv /usr/local/bin/uv
ENV UV_PROJECT_ENVIRONMENT=/opt/venv UV_PYTHON_DOWNLOADS=never UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy \
    PATH=/opt/venv/bin:$PATH MPLCONFIGDIR=/tmp
WORKDIR /opt/mech
COPY mechanical/pyproject.toml mechanical/uv.lock ./
RUN uv sync --frozen --no-install-project && /opt/venv/bin/python -c "import OCP.STEPControl, build123d, trimesh"
