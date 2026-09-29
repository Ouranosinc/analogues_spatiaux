FROM mambaorg/micromamba as base

# The environment variable ensures that the python output is set straight
# to the terminal without buffering it first
ENV PYTHONUNBUFFERED 1

WORKDIR /app

COPY ./environment.yml /app 

RUN  micromamba install -y -n base -f environment.yml && micromamba clean -afy

ENV MAMBA_DOCKERFILE_ACTIVATE=1
RUN python -c 'import uuid; print(uuid.uuid4())' > /tmp/my_uuid

# RUN pip install -r requirements_minimal.txt

USER root
RUN mkdir -p /notebook_dir/writable-workspace && chown -R ${MAMBA_USER} /notebook_dir

WORKDIR /

COPY --chown=${MAMBA_USER} . app

WORKDIR /app

RUN pip install --no-dependencies -e ./
USER ${MAMBA_USER}

EXPOSE 5006

# LANG is used in dashboard.py to set the language on initial load.
# It can be changed in the about section, but this is not visible on climatedata.ca
ENV LANG=en
# PREFIX is used in start_panel.sh to set the subpath for the dashboard.
# Dashboard will be available at http://<host>:<port_external>/<PREFIX>/Dashboard
ENV PREFIX=analogs

# MAP URLS:
# options:
# CARTO - requires API key: 
#   labels: 'https://a.basemaps.cartocdn.com/light_only_labels/{z}/{x}/{y}@2x.png' 
#   base: 'https://cartodb-basemaps-4.global.ssl.fastly.net/light_nolabels/{Z}/{X}/{Y}@2x.png'
# ESRI:
#   labels: "https://server.arcgisonline.com/arcgis/rest/services/Reference/World_Boundaries_and_Places_Alternate/MapServer/tile/{Z}/{Y}/{X}@2x"
#   base: "https://server.arcgisonline.com/ArcGIS/rest/services/World_Physical_Map/MapServer/tile/{Z}/{Y}/{X}@2x"
# CDN:
#   labels_en: 'https://maps-cartes.services.geo.ca/server2_serveur2/rest/services/BaseMaps/CBMT_TXT_3857/MapServer/WMTS/tile/1.0.0/BaseMaps_CBMT_TXT_3857/default/default/{z}/{y}/{x}.png'
#   labels_fr: 'https://maps-cartes.services.geo.ca/server2_serveur2/rest/services/BaseMaps/CBCT_TXT_3857/MapServer/WMTS/tile/1.0.0/BaseMaps_CBMT_TXT_3857/default/default/{z}/{y}/{x}.png'
#   base: 'https://maps-cartes.services.geo.ca/server2_serveur2/rest/services/BaseMaps/CBMT_CBCT_GEOM_3857/MapServer/WMTS/tile/1.0.0/BaseMaps_CBMT_CBCT_GEOM_3857/default/default/{z}/{y}/{x}.png'

# BASE_MAP_URL:
ENV BASE_MAP_URL="https://maps-cartes.services.geo.ca/server2_serveur2/rest/services/BaseMaps/CBMT_CBCT_GEOM_3857/MapServer/WMTS/tile/1.0.0/BaseMaps_CBMT_CBCT_GEOM_3857/default/default/{z}/{y}/{x}.png"
# LABEL_MAP_URL_EN:
ENV LABEL_MAP_URL_EN="https://server.arcgisonline.com/arcgis/rest/services/Reference/World_Boundaries_and_Places_Alternate/MapServer/tile/{Z}/{Y}/{X}@2x"
ENV LABEL_MAP_URL_FR="https://server.arcgisonline.com/arcgis/rest/services/Reference/World_Boundaries_and_Places_Alternate/MapServer/tile/{Z}/{Y}/{X}@2x"

# SHOW_HEADER and SHOW_MODAL control whether the header and modal are shown, respectively.
# Unset/set to 0 to hide them. (for climatedata.ca)
ENV SHOW_HEADER=1
ENV SHOW_MODAL=1

CMD exec ./start_panel.sh
