FROM python:3.12-slim AS builder

WORKDIR /app
COPY pyproject.toml README.md ./
COPY k8s_purify/ k8s_purify/

RUN pip install --no-cache-dir .

FROM python:3.12-slim

WORKDIR /app
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin/k8s-purify /usr/local/bin/k8s-purify

RUN groupadd -r purify && useradd -r -g purify -s /sbin/nologin purify
USER purify

ENTRYPOINT ["k8s-purify"]
CMD ["scan", "all"]
