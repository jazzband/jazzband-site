FROM node as npm

COPY package.json package-lock.json /tmp/

WORKDIR /tmp

RUN npm install

# -----------------------------------------------------------------------------

FROM python:3.6

ENV PYTHONUNBUFFERED 1 \
    PYTHONPATH /app/

# add a non-privileged user for installing and running the application
# don't use --create-home option to prevent populating with skeleton files
RUN mkdir /app && \
    chown 10001:10001 /app && \
    groupadd --gid 10001 app && \
    useradd --no-create-home --uid 10001 --gid 10001 --home-dir /app app

RUN set -x \
    && apt-get update \
    && apt-get install locales -y \
    && locale-gen en_US.UTF-8

# install a few essentials and clean apt caches afterwards
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential curl git libpq-dev \
        postgresql-client gettext sqlite3 libffi-dev \
        inotify-tools wget bzip2 && \
    apt-get autoremove -y && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

RUN pip install -U pip

COPY requirements.txt /tmp/

RUN set -x \
    && pip install --no-cache-dir -r /tmp/requirements.txt \
    && find /usr/local -type f -name '*.pyc' -name '*.pyo' -delete

COPY . /app/

COPY --from=npm /tmp/node_modules /app/node_modules/

RUN chown -R 10001:10001 /app

USER 10001

WORKDIR /app

ENTRYPOINT ["/app/docker-entrypoint.sh", "--"]
