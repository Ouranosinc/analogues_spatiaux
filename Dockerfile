FROM continuumio/miniconda3

# The environment variable ensures that the python output is set straight
# to the terminal without buffering it first
ENV PYTHONUNBUFFERED 1

WORKDIR /

# COPY ./requirements.txt app/

WORKDIR /app



COPY ./reqs.debug.txt /app/

RUN conda install cartopy netcdf4=1.5.6 && conda clean -afy
RUN conda install --channel conda-forge esmpy && conda clean -afy

RUN pip install -r reqs.debug.txt


WORKDIR /

COPY . app

WORKDIR /app

EXPOSE 5006

ENTRYPOINT ["panel", "serve", "Dashboard.ipynb", "--session-token-expiration", "86400", "--prefix", "analogs", "--use-xheaders", "--log-level=debug"]
