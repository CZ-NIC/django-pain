########################################################################################################################
# This file was generated using python_env, please do not edit directly.
########################################################################################################################

FROM ubuntu:bionic
# Requirements for the stylelint
RUN apt-get --yes update \
 && apt-get install --yes --no-install-recommends \
    build-essential \
    ca-certificates \
    git \
    npm \
 && rm -rf /var/lib/apt/lists/*
RUN npm install -g npm @cz-nic/json-python-coverage
