FROM continuumio/miniconda3

# The environment variable ensures that the python output is set straight
# to the terminal without buffering it first
ENV PYTHONUNBUFFERED 1

WORKDIR /

COPY ./requirements.txt app/

WORKDIR /app

RUN conda install --channel \ 
    conda-forge \ 
    cartopy \ 
    esmpy \ 
    netCDF4 \ 
    && conda clean -afy
RUN pip install -r requirements.txt

WORKDIR /

COPY . app

WORKDIR /app

EXPOSE 5006

ENTRYPOINT ["panel", "serve", "Dashboard.ipynb", "--session-token-expiration", "86400", "--prefix", "analogs", "--use-xheaders", "--log-level=debug"]
