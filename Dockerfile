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

# Run the application as an unprivileged user
RUN addgroup --system appgroup \
    && adduser --system --ingroup appgroup appuser \
    && chown -R appuser:appgroup /app

USER appuser

EXPOSE 8000

CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "2", "--access-logfile", "-", "scam_project.wsgi:application"]
