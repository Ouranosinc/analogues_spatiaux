FROM continuumio/miniconda3
# The environment variable ensures that the python output is set straight
# to the terminal without buffering it first
ENV PYTHONUNBUFFERED 1

ENV LOADWRIGHT_HEADLESS 1
ENV LOADWRIGHT_HOST="https://app-spatial-analogs-staging.climatedata.ca"

COPY . /

RUN pip install -r requirements_loadwright.txt

CMD pytest test_loadwright.py