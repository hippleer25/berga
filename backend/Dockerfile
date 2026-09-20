FROM python:3.12-slim

WORKDIR /code

COPY requirements.lock .
RUN pip install --no-cache-dir -r requirements.lock

COPY . .
COPY supervisord.conf /etc/supervisord.conf

RUN useradd --create-home appuser \
 && mkdir -p /home/appuser/.cache/huggingface/hub \
 && chown -R appuser:appuser /home/appuser/.cache
USER appuser

CMD ["supervisord", "-c", "/etc/supervisord.conf"]
