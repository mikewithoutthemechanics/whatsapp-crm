# WhatsApp CRM SA - User-Friendly Docker Image
# Run: docker run -p 8000:8000 mikewithoutthemechanics/wavi-crm
# Then open http://localhost:8000/setup in browser

FROM python:3.12-slim

WORKDIR /app

# Install runtime
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app
COPY app/ ./app/
COPY api/ ./api/
COPY scripts/ ./scripts/

# Create entrypoint
COPY scripts/start_all.py /usr/local/bin/start_all.py
RUN chmod +x /usr/local/bin/start_all.py

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8000/health').raise_for_status()" || exit 1

EXPOSE 8000

# Default: show setup page
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]