FROM continuumio/miniconda3:23.5.2-0 as base

# The environment variable ensures that the python output is set straight
# to the terminal without buffering it first
ENV PYTHONUNBUFFERED 1

WORKDIR /app
RUN conda install conda==23.7.3 -y && conda install conda-libmamba-solver -y
RUN conda install --solver=libmamba --channel conda-forge gxx_linux-64==11.1.0 python=3.9 cartopy=0.21.1 esmpy=8.4.2 -y && conda clean -afy

COPY  ./requirements_prod.txt /app/

RUN pip install -r requirements_prod.txt

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
