FROM continuumio/miniconda3

# The environment variable ensures that the python output is set straight
# to the terminal without buffering it first
ENV PYTHONUNBUFFERED 1

WORKDIR /app

RUN conda install --channel conda-forge cartopy -y
RUN conda install --channel conda-forge esmpy && conda clean -afy

COPY ./requirements_minimal.txt /app/

RUN pip install -r requirements_minimal.txt
RUN apt update
RUN apt install -y libtiff5

WORKDIR /

COPY . app

WORKDIR /app

EXPOSE 5006

ENTRYPOINT ["panel", "serve", "Dashboard.ipynb", "--session-token-expiration", "86400", "--prefix", "analogs", "--use-xheaders", "--log-level=debug", "--static-dirs", "fonts=./fonts"]
