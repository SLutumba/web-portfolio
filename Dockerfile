FROM python:3.13-slim
WORKDIR /portfolio
COPY requirements.txt ./
COPY vendor/task_api/requirements.txt vendor/task_api/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY server.py ./
COPY static/ static/
COPY vendor/ vendor/
RUN useradd --create-home portfolio && mkdir -p data && chown -R portfolio:portfolio /portfolio
USER portfolio
EXPOSE 8080
CMD ["waitress-serve", "--listen=0.0.0.0:8080", "server:app"]

