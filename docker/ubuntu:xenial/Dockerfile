FROM ubuntu:xenial
# Requirements for the python test environment
RUN apt-get --yes update \
 && apt-get install --yes --no-install-recommends \
    gettext \
    python3-setuptools \
 && rm -rf /var/lib/apt/lists/*
# Install newest pip, tox and its plugins
RUN apt-get --yes update \
 && apt-get install --yes --no-install-recommends \
    python3-pip \
 && rm -rf /var/lib/apt/lists/* \
 && pip3 install --upgrade \
    pip \
    tox \
 && apt-get purge --yes python3-pip
