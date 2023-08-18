#!/bin/bash

SETUP_FILE="setup_cache.py"
DASHBOARD_FILE="Dashboard.py"

SESSION_TOKEN_EXPIRATION=86400
PREFIX="analogs"
LOG_LEVEL="debug"
MAX_PROCS=$(nproc --all)

NUM_PROCS=$((MAX_PROCS - 1 > 16 ? 16 : MAX_PROCS - 1))
NUM_THREADS=0

panel serve "${DASHBOARD_FILE}" --setup "${SETUP_FILE}" --session-token-expiration "${SESSION_TOKEN_EXPIRATION}" --prefix "${PREFIX}" --use-xheaders --log-level="${LOG_LEVEL}" --static-dirs fonts=./fonts scripts=./scripts --num-procs $NUM_PROCS --num-threads $NUM_THREADS
