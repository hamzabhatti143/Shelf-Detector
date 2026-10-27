FROM python:3.12-slim
WORKDIR /srv

ARG WITH_YOLO=false
COPY requirements.txt requirements-yolo.txt ./
RUN pip install --no-cache-dir -r requirements.txt \
    && if [ "$WITH_YOLO" = "true" ]; then pip install --no-cache-dir -r requirements-yolo.txt; fi

COPY app ./app
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]