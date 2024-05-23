FROM mambaorg/micromamba as base

# The environment variable ensures that the python output is set straight
# to the terminal without buffering it first
ENV PYTHONUNBUFFERED 1

USER root
ENV $MAMBA_USER=root

WORKDIR /app

COPY ./environment.yml /app 

RUN  micromamba install -y -n base -f environment.yml && micromamba clean -afy

ENV MAMBA_DOCKERFILE_ACTIVATE=1
RUN python -c 'import uuid; print(uuid.uuid4())' > /tmp/my_uuid

# RUN pip install -r requirements_minimal.txt

RUN mkdir -p /notebook_dir/writable-workspace

WORKDIR /

COPY . app

WORKDIR /app

RUN pip install --no-dependencies ./

EXPOSE 5006

# LANG is used in dashboard.py to set the language on initial load.
# It can be changed in the about section, but this is not visible on climatedata.ca
ENV LANG=en
# PREFIX is used in start_panel.sh to set the subpath for the dashboard.
# Dashboard will be available at http://<host>:<port_external>/<PREFIX>/Dashboard
ENV PREFIX=analogs

# SHOW_HEADER and SHOW_MODAL control whether the header and modal are shown, respectively.
# Unset/set to 0 to hide them. (for climatedata.ca)
ENV SHOW_HEADER=1
ENV SHOW_MODAL=1

CMD exec ./start_panel.sh

FROM base as base-fr

ENV LANG=fr
ENV PREFIX=analogs-fr

CMD exec ./start_panel.sh
