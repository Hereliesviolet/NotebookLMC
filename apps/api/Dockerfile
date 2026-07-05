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
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
