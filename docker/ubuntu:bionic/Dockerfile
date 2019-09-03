FROM ubuntu:bionic
# Requirements for the python test environment
RUN apt-get --yes update \
 && apt-get install --yes --no-install-recommends \
    ca-certificates \
    gettext \
    git \
    python3-setuptools \
    ssh \
    wget \
 && rm -rf /var/lib/apt/lists/*
# CA CZ.NIC
RUN wget -O /etc/ssl/certs/cz.nic2-cacert.pem https://archive.nic.cz/private/cz.nic2-cacert.pem \
 && update-ca-certificates
# Install newest pip, tox and its plugins
RUN apt-get --yes update \
 && apt-get install --yes --no-install-recommends \
    python3-pip \
 && rm -rf /var/lib/apt/lists/* \
 && pip3 install --upgrade \
    pip \
    tox \
 && apt-get purge --yes python3-pip
# Install report-json-coverage
RUN pip3 install git+https://gitlab.office.nic.cz/jmusilek/report-json-coverage.git
