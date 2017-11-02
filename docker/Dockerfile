FROM debian:jessie
RUN apt-get update \
    && apt-get install -y apt-transport-https ca-certificates gcc \
    && apt-get clean \
    && rm -rf /var/cache/apt/*
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        python-pip python-dev libyaml-dev libxml2-dev \
        libxslt1-dev python-lxml zlib1g-dev \
    && apt-get clean && rm -rf /var/cache/apt/*

RUN pip install -U setuptools
COPY requirements.txt /requirements.txt
RUN pip install -r /requirements.txt

WORKDIR /app

ENTRYPOINT ["python", "/app/manage.py"]
CMD ["runserver", "0.0.0.0:8010"]
