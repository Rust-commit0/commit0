_DOCKERFILE_BASE = r"""
FROM --platform={platform} ubuntu:22.04

ARG DEBIAN_FRONTEND=noninteractive
ENV TZ=Etc/UTC

ARG http_proxy
ARG https_proxy
ARG HTTP_PROXY
ARG HTTPS_PROXY
ARG no_proxy="localhost,127.0.0.1,::1"
ARG NO_PROXY="localhost,127.0.0.1,::1"

RUN apt update && apt install -y \
wget \
build-essential \
libffi-dev \
libtiff-dev \
python3 \
python3-pip \
python-is-python3 \
jq \
curl \
locales \
locales-all \
tzdata \
ca-certificates \
&& rm -rf /var/lib/apt/lists/*

RUN apt-get update && apt-get install software-properties-common -y
RUN add-apt-repository ppa:git-core/ppa -y
RUN apt-get update && apt-get install git -y

RUN apt-get update && apt-get install -y --no-install-recommends python3-venv

RUN add-apt-repository ppa:deadsnakes/ppa -y && apt-get update && \
    apt-get install -y python3.10 python3.10-venv python3.10-dev python3.12 python3.12-venv python3.12-dev || true

RUN echo '#!/bin/bash' > /usr/local/bin/uv && \
    echo 'if [ "$1" = "venv" ]; then' >> /usr/local/bin/uv && \
    echo '  shift; pv=""; td=".venv"' >> /usr/local/bin/uv && \
    echo '  while [ $# -gt 0 ]; do' >> /usr/local/bin/uv && \
    echo '    case $1 in --python) pv="$2"; shift 2;; *) td="$1"; shift;; esac' >> /usr/local/bin/uv && \
    echo '  done' >> /usr/local/bin/uv && \
    echo '  if [ -n "$pv" ]; then "python$pv" -m venv "$td"; else python3 -m venv "$td"; fi' >> /usr/local/bin/uv && \
    echo 'elif [ "$1" = "pip" ]; then' >> /usr/local/bin/uv && \
    echo '  shift; pip "$@"' >> /usr/local/bin/uv && \
    echo 'else' >> /usr/local/bin/uv && \
    echo '  echo "uv shim: unsupported: $@" >&2; exit 1' >> /usr/local/bin/uv && \
    echo 'fi' >> /usr/local/bin/uv && \
    chmod +x /usr/local/bin/uv

RUN mkdir -p /etc/pki/tls/certs /etc/pki/tls /etc/pki/ca-trust/extracted/pem /etc/ssl/certs && \
    ln -sf /etc/ssl/certs/ca-certificates.crt /etc/pki/tls/certs/ca-bundle.crt && \
    ln -sf /etc/ssl/certs/ca-certificates.crt /etc/ssl/cert.pem && \
    ln -sf /etc/ssl/certs/ca-certificates.crt /etc/pki/tls/cert.pem && \
    ln -sf /etc/ssl/certs/ca-certificates.crt /etc/pki/ca-trust/extracted/pem/tls-ca-bundle.pem

ENV SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt \
    REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt \
    CURL_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt \
    NODE_EXTRA_CA_CERTS=/etc/ssl/certs/ca-certificates.crt

COPY mitm-ca.cr[t] /tmp/
RUN if [ -f /tmp/mitm-ca.crt ]; then \
        cp /tmp/mitm-ca.crt /usr/local/share/ca-certificates/mitm-ca.crt && \
        update-ca-certificates && \
        echo "MITM CA certificate installed successfully"; \
    else \
        echo "No MITM CA certificate found, skipping"; \
    fi && \
    rm -f /tmp/mitm-ca.crt
"""

_DOCKERFILE_REPO = r"""FROM --platform={platform} commit0.base:latest

ARG http_proxy
ARG https_proxy
ARG HTTP_PROXY
ARG HTTPS_PROXY
ARG no_proxy="localhost,127.0.0.1,::1"
ARG NO_PROXY="localhost,127.0.0.1,::1"

COPY ./setup.sh /root/
RUN chmod +x /root/setup.sh
RUN /bin/bash /root/setup.sh

WORKDIR /testbed/

RUN echo "source /testbed/.venv/bin/activate" > /root/.bashrc
"""


def get_dockerfile_base(platform: str) -> str:
    return _DOCKERFILE_BASE.format(platform=platform)


def get_dockerfile_repo(platform: str) -> str:
    return _DOCKERFILE_REPO.format(platform=platform)


__all__ = []
