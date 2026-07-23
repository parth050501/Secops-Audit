# CodeCore Collector Engine — runs inside the customer network (in your OVA).
# Minimal, non-root, small surface. Scanners (oscap etc.) are added in the OVA
# base or layered here as your production build requires.
FROM python:3.12-slim

# Create a non-root user to run the collector
RUN useradd --create-home --shell /usr/sbin/nologin collector \
    && mkdir -p /var/lib/codecore /etc/codecore \
    && chown -R collector:collector /var/lib/codecore /etc/codecore

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY codecore_collector ./codecore_collector

USER collector

# Config comes from env vars (APE_URL, COLLECTOR_TOKEN) or a mounted config file
# at /etc/codecore/collector.conf. Queue persists at /var/lib/codecore.
EXPOSE 8514
VOLUME ["/var/lib/codecore"]

ENTRYPOINT ["python", "-m", "codecore_collector.engine"]
