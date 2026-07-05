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

# Echte Prozess-Parallelitaet statt eines einzelnen Uvicorn-Prozesses: eine
# einzelne lang laufende Langdock-Anfrage (Studio-Generierung, Chat) blockiert
# sonst dessen kompletten Event-Loop fuer alle Nutzer, selbst nachdem die
# einzelnen Langdock-/Qdrant-Aufrufe async/asyncio.to_thread-faehig gemacht
# wurden (CPU-seitige Arbeit - z.B. JSON/Pydantic-Verarbeitung, Studio-Export-
# Rendering - blockiert weiterhin den jeweiligen Worker-Prozess).
#
# Gunicorn (statt Uvicorn's eingebautem --workers, seit 0.30 verfuegbar) als
# Prozess-Supervisor: robusteres Worker-Handling in Production (automatischer
# Neustart abgestuerzter Worker inkl. --timeout fuer haengende Worker,
# --max-requests gegen Memory-Leaks) - Uvicorn selbst bleibt der eigentliche
# ASGI-Server je Worker-Prozess ueber den UvicornWorker-Worker-Typ.
# API_WORKERS ist ueberschreibbar (.env / docker-compose.yml environment),
# Default 4 passend zu i.d.R. 2-4 CPU-Kernen auf einem Single-VM-Deployment
# wie hier (kein Kubernetes o.ae. mit Pod-Autoscaling).
ENV API_WORKERS=4

CMD gunicorn app.main:app \
    --workers ${API_WORKERS} \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:8000 \
    --timeout 300 \
    --graceful-timeout 30 \
    --max-requests 2000 \
    --max-requests-jitter 200
