FROM continuumio/miniconda3

# The environment variable ensures that the python output is set straight
# to the terminal without buffering it first
ENV PYTHONUNBUFFERED 1

WORKDIR /app

RUN conda install cartopy netcdf4=1.5.6 && conda clean -afy
RUN conda install --channel conda-forge esmpy && conda clean -afy

COPY ./requirements.txt /app/

RUN pip install -r requirements.txt

WORKDIR /

COPY . app

WORKDIR /app

EXPOSE 5006

ENTRYPOINT ["panel", "serve", "Dashboard.ipynb", "--warm", "--static-dirs", "assets=./assets", "--session-token-expiration", "86400", "--prefix", "analogs", "--use-xheaders", "--log-level=debug"]
