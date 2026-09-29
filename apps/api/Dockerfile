FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    # WeasyPrint (apps/api/app/studio/export.py) runtime libs - installed via
    # pip wheels, so only the shared libraries it dlopen()s at runtime are
    # needed (no -dev/compile packages). Versions >=53 dropped the old
    # cairo-based rendering backend for a Pango/HarfBuzz one, see
    # https://doc.courtbouillon.org/weasyprint/stable/first_steps.html
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libharfbuzz-subset0 \
    fontconfig \
    fonts-liberation \
    # fonts-liberation alone lacks glyphs for the Briefing-export icons
    # (U+26A0 warning sign, U+2713 check mark) - Pango/HarfBuzz silently
    # falls back to DejaVu for just those glyphs while keeping Liberation
    # Sans for regular text (verified in-container before adding this).
    fonts-dejavu-core \
    # cairosvg (apps/api/app/studio/export.py, Mindmap-PNG-Export) needs
    # libcairo directly via cairocffi - WeasyPrint >=53 no longer pulls this
    # in (see comment above), so it must be installed explicitly.
    libcairo2 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# Real process parallelism instead of a single Uvicorn process: one long
# Langdock request (studio generation, chat) would otherwise block the event
# loop for all users, and CPU-bound work (JSON/Pydantic handling, studio
# export rendering) still blocks its own worker process.
#
# Gunicorn supervises the workers: crashed or hanging workers are restarted
# (--timeout) and --max-requests recycles them against memory growth. Uvicorn
# stays the ASGI server inside each worker through the UvicornWorker class.
# API_WORKERS can be overridden (.env / docker-compose.yml environment). The
# default of 4 fits a single VM with 2-4 CPU cores.
ENV API_WORKERS=4

CMD gunicorn app.main:app \
    --workers ${API_WORKERS} \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:8000 \
    --timeout 300 \
    --graceful-timeout 30 \
    --max-requests 2000 \
    --max-requests-jitter 200
