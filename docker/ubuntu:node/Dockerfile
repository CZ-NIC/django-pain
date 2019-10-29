########################################################################################################################
# This file was generated using python_env, please do not edit directly.
########################################################################################################################

FROM ubuntu:bionic
# Requirements for the stylelint
RUN apt-get --yes update \
 && apt-get install --yes --no-install-recommends \
    ca-certificates \
    git \
    npm \
    build-essential \
 && rm -rf /var/lib/apt/lists/*
RUN npm install -g @cz-nic/json-python-coverage
