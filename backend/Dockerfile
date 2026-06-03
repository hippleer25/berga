FROM python:3.12-slim

WORKDIR /code

COPY requirements.lock .
RUN pip install --no-cache-dir --extra-index-url https://download.pytorch.org/whl/cpu -r requirements.lock

COPY . .
COPY supervisord.conf /etc/supervisord.conf

RUN useradd --create-home appuser
USER appuser

CMD ["supervisord", "-c", "/etc/supervisord.conf"]
