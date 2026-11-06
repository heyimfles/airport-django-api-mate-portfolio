FROM python:3.12.16-alpine3.24
LABEL maintainer="aleksacat13@gmail.com"

WORKDIR app/

COPY requirements.txt requirements.txt

RUN pip install --upgrade pip
RUN pip install -r requirements.txt

COPY . .