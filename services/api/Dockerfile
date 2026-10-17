# Base image pinned by multi-arch index digest: the tag alone can be re-pointed upstream.
# Dependabot (docker ecosystem) updates the tag and digest together.
# Stage 1: install dependencies into a virtualenv
FROM python:3.14-slim@sha256:a2b82f3c48559aa0a8446d9af49826b6e2b2016f4cd2afabfe6013ec53729170 AS build
RUN python -m venv /opt/venv
COPY requirements.txt .
RUN /opt/venv/bin/pip install --no-cache-dir -r requirements.txt \
    && /opt/venv/bin/pip uninstall -y pip

# Stage 2: runtime image with only the venv and the app code
FROM python:3.14-slim@sha256:a2b82f3c48559aa0a8446d9af49826b6e2b2016f4cd2afabfe6013ec53729170
ENV PATH=/opt/venv/bin:$PATH \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
# pip is only needed at build time; removing it drops its vendored libraries (and their CVEs)
RUN python -m pip uninstall -y pip \
    && rm -rf /usr/local/lib/python3.14/ensurepip \
    && useradd --uid 10001 --no-create-home --shell /usr/sbin/nologin app
WORKDIR /app
COPY --from=build /opt/venv /opt/venv
COPY app.py .
COPY static/ static/
# Numeric UID so Kubernetes can verify runAsNonRoot
USER 10001
EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=3s \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/healthz')"
# --no-access-log: the app writes its own JSON line per request (see log_request in app.py)
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
