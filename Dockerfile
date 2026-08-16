FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN addgroup --system app && adduser --system --ingroup app app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN DJANGO_SECRET_KEY=build-only DEBUG=0 ALLOWED_HOSTS=localhost \
    python manage.py collectstatic --noinput && \
    chown -R app:app /app

USER app
EXPOSE 8000

CMD ["./start.sh"]
