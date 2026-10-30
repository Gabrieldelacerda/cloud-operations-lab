FROM python:3.13.18-slim-bookworm

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

COPY app/main.py ./main.py

USER 10001:10001

EXPOSE 8000

CMD ["python", "main.py"]
