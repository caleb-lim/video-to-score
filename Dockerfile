# GPU image (default):  docker compose build vts
# CPU image:            docker compose build vts-cpu
#   or by hand:         docker build --build-arg TORCH_VARIANT=cpu -t video-to-score:cpu .
#
# TORCH_VARIANT is a PyTorch wheel index: cpu, cu118, cu124, cu126 ... (see pytorch.org).
# cu124 works with any NVIDIA driver new enough for CUDA 12.

FROM python:3.11-slim

ARG TORCH_VARIANT=cu124
ARG TORCH_VERSION=2.6.0

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    # Model weights (Demucs, beat_this, ...) and yt-dlp cache land here; mount a volume to keep them.
    XDG_CACHE_HOME=/cache \
    TORCH_HOME=/cache/torch \
    HF_HOME=/cache/huggingface \
    HOME=/cache/home

RUN apt-get update \
 && apt-get install -y --no-install-recommends ffmpeg libsndfile1 build-essential \
 && rm -rf /var/lib/apt/lists/*

# Basic Pitch lives in its own venv so its numpy/TF pins can't fight torch.
# It's exposed on PATH as `basic-pitch`, which is what config.yaml calls by default.
RUN python -m venv /opt/basicpitch \
 && /opt/basicpitch/bin/pip install basic-pitch \
 && ln -s /opt/basicpitch/bin/basic-pitch /usr/local/bin/basic-pitch

# PyTorch from the chosen wheel index, then pinned so later installs can't swap it.
RUN pip install "torch==${TORCH_VERSION}" "torchaudio==${TORCH_VERSION}" \
        --index-url "https://download.pytorch.org/whl/${TORCH_VARIANT}" \
 && printf "torch==%s\ntorchaudio==%s\n" "${TORCH_VERSION}" "${TORCH_VERSION}" > /opt/torch-constraints.txt

WORKDIR /app

# Dependencies first (cached layer): install from pyproject with a stub package,
# so editing source code doesn't re-download the ML stack.
COPY pyproject.toml README.md ./
RUN mkdir -p src/video_to_score && touch src/video_to_score/__init__.py \
 && pip install -c /opt/torch-constraints.txt ".[ml,dev]"

# The real source.
COPY src ./src
RUN pip install --no-deps --force-reinstall .
COPY tests ./tests
COPY bench ./bench

# Runtime layout: /work is the working dir, /work/songs is meant to be a bind mount.
WORKDIR /work
COPY config.yaml /work/config.yaml
RUN mkdir -p /work/songs /cache/home \
 && chmod -R a+rwX /work /cache

ENTRYPOINT ["video-to-score"]
CMD ["--help"]
