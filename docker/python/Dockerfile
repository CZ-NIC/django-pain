ARG PYTHON_VERSION=3.8
FROM reg.nic.cz/python/tox:${PYTHON_VERSION}
RUN apt-get --yes update \
# Install testing dependencies
 && apt-get install --yes --no-install-recommends \
    gettext \
    gcc \
    git \
    libxml2 \
    libxslt1-dev \
    ssh \
    zlib1g-dev \
 && rm -rf /var/lib/apt/lists/*
