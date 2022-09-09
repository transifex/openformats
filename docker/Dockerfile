ARG PY_VERSION=3.6

FROM python:${PY_VERSION}-slim-buster as builder


ENV PKGS='\
    # Packages required by pip
    git openssh-client'

COPY ./setup.cfg ./app/setup.cfg
COPY ./setup.py ./app/setup.py
COPY ./versioneer.py ./app/versioneer.py

RUN apt-get update && apt-get install -y --no-install-recommends $PKGS && \
    python ./app/setup.py egg_info && \
    pip install --no-cache-dir -r openformats.egg-info/requires.txt  && \
    rm -rf /var/lib/apt/lists/*

ENV PYTHONDONTWRITEBYTECODE=1

COPY requirements.txt /requirements.txt
RUN pip install -r /requirements.txt

WORKDIR /app

ENTRYPOINT ["python", "/app/manage.py"]
CMD ["runserver", "0.0.0.0:8010"]
