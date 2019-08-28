FROM ubuntu:bionic
# Requirements for the stylelint
RUN apt-get --yes update \
 && apt-get install --yes --no-install-recommends \
    ca-certificates \
    git \
    npm \
 && rm -rf /var/lib/apt/lists/*
