FROM --platform=x86_64 python:3.8 as development

RUN curl -sSL https://raw.githubusercontent.com/python-poetry/poetry/master/get-poetry.py | POETRY_HOME=/opt/poetry python && \
    cd /usr/local/bin && \
    ln -s /opt/poetry/bin/poetry && \
    poetry config virtualenvs.create false

# ================= Install JSignPDF ===========================
RUN apt update && apt -y install default-jre    
COPY ./jsignpdf.tar.gz .
RUN tar -zxf jsignpdf.tar.gz --directory /
RUN rm jsignpdf.tar.gz
# ==============================================================


COPY ./pyproject.toml ./poetry.lock* /tmp/
WORKDIR /tmp
RUN poetry install --no-root

RUN mkdir -p /app
RUN mkdir -p /data
WORKDIR /app

FROM --platform=x86_64 tiangolo/uvicorn-gunicorn-fastapi:python3.8 as production

RUN curl -sSL https://raw.githubusercontent.com/python-poetry/poetry/master/get-poetry.py | POETRY_HOME=/opt/poetry python && \
    cd /usr/local/bin && \
    ln -s /opt/poetry/bin/poetry && \
    poetry config virtualenvs.create false

# ================= Install JSignPDF ===========================
RUN apt update && apt -y install default-jre    
COPY ./jsignpdf.tar.gz .
RUN tar -zxf jsignpdf.tar.gz --directory /
RUN rm jsignpdf.tar.gz
# ==============================================================

COPY ./pyproject.toml ./poetry.lock* /tmp/
WORKDIR /tmp
RUN poetry install --no-root --no-dev

COPY ./ /app
RUN mkdir -p /data
WORKDIR /app
EXPOSE 80