FROM python:3.13-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py foods.csv ./
COPY static ./static
ENV DB_PATH=/data/app.db
EXPOSE 8000
# one process + threads: SQLite handles a single writer best
CMD ["gunicorn", "--workers", "1", "--threads", "4", "--bind", "0.0.0.0:8000", "app:app"]
