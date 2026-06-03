FROM python:3.12-slim

WORKDIR /code

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt supervisor==4.2.5

COPY . .
COPY supervisord.conf /etc/supervisord.conf

RUN useradd --create-home appuser
USER appuser

CMD ["supervisord", "-c", "/etc/supervisord.conf"]
