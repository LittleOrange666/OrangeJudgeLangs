FROM ubuntu:22.04

WORKDIR /app

RUN apt-get clean && rm -rf /var/lib/apt/lists/* && apt-get update

RUN apt-get -y install build-essential cmake bzip2 libseccomp-dev