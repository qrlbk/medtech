FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# System deps for psycopg, lxml, pdfplumber, playwright
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev libxml2-dev libxslt1-dev curl \
    && rm -rf /var/lib/apt/lists/*

# Set to "true" to additionally install the optional ML stack (torch +
# sentence-transformers) and enable semantic matching/search.
ARG INSTALL_ML=false

COPY requirements.txt requirements-ml.txt ./
# Resilient install: retry on flaky network/SSL and use a longer timeout.
RUN pip install --upgrade pip \
    && pip install --retries 8 --timeout 180 -r requirements.txt \
    && if [ "$INSTALL_ML" = "true" ]; then \
         pip install --retries 8 --timeout 180 -r requirements-ml.txt; fi

# Default to lexical+fuzzy normalization; flip to true when ML extras are built in.
ENV EMBEDDINGS_ENABLED=${INSTALL_ML}

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
