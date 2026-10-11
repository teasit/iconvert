FROM python:3.12-alpine

RUN apk add --no-cache vips vips-heif libheif-aom librsvg

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py .

RUN mkdir -p /cache && chown nobody:nobody /cache && chmod 777 /cache
VOLUME /cache
EXPOSE 8000
USER nobody

HEALTHCHECK --interval=60s --timeout=5s CMD wget -qO- http://127.0.0.1:8000/health || exit 1
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
