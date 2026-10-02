# Production image for scamdb.dollarscholars.org (same pattern as the quiz).
# Build and run: see docs/DEPLOY.md
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN python -m pip install --no-cache-dir -r requirements.txt

COPY . .

# Bake the static files into the image; WhiteNoise serves them at runtime.
# (Debug settings are only used for this build step, not at runtime.)
RUN DJANGO_DEBUG=True python manage.py collectstatic --noinput

# The translations, made on dollarscholars.org (docs/TRANSLATIONS.md). The container
# downloads them again when it starts (CMD); these are the fallback if that fails.
RUN DJANGO_DEBUG=True python manage.py fetch_translations --timeout 20

# Run the application as an unprivileged user
RUN addgroup --system appgroup \
    && adduser --system --ingroup appgroup appuser \
    && chown -R appuser:appgroup /app

USER appuser

EXPOSE 8000

# Fetch the latest translations (never stops the start: on failure the ones in the image
# stay), then serve. So `docker restart scamdb-app` also brings in new translations.
CMD ["sh", "-c", "python manage.py fetch_translations --timeout 15; exec gunicorn --bind 0.0.0.0:8000 --workers 2 --access-logfile - scam_project.wsgi:application"]
