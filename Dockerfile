FROM python:3.12-slim AS builder

WORKDIR /app
COPY pyproject.toml README.md ./
COPY k8s_investigate/ k8s_investigate/

RUN pip install --no-cache-dir .

FROM python:3.12-slim

WORKDIR /app
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin/k8s-investigate /usr/local/bin/k8s-investigate

RUN groupadd -r investigate && useradd -r -g investigate -s /sbin/nologin investigate
USER investigate

ENTRYPOINT ["k8s-investigate"]
CMD ["scan", "all"]
