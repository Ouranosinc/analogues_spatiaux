FROM continuumio/miniconda3
# The environment variable ensures that the python output is set straight
# to the terminal without buffering it first
ENV PYTHONUNBUFFERED 1

COPY . /

RUN pip install -r requirements_locust.txt

EXPOSE 8089

CMD locust