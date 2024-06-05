#!/bin/bash

SETUP_FILE="${SETUP_FILE:-setup_cache.py}" # default to "setup_cache.py"
DASHBOARD_FILE="${DASHBOARD_FILE:-Dashboard.py}" # default to "Dashboard.py"
echo "SETUP_FILE: $SETUP_FILE"
echo "DASHBOARD_FILE: $DASHBOARD_FILE"

SESSION_TOKEN_EXPIRATION="${SESSION_TOKEN_EXPIRATION:-86400}"
echo "SESSION_TOKEN_EXPIRATION: $SESSION_TOKEN_EXPIRATION"
# one of [debug, info, warning, error, critical]
LOG_LEVEL="${LOG_LEVEL:-info}" # default to "info"
echo "LOG_LEVEL: $LOG_LEVEL"
MAX_PROCS="${MAX_PROCS:-$(nproc --all)}" # default to number of cores
echo "MAX_PROCS: $MAX_PROCS"
NUM_PROCS="${NUM_PROCS:-$((MAX_PROCS - 1 > 16 ? 16 : MAX_PROCS - 1))}" # default to number of cores - 1, or 16, if number of cores is more than 16.
echo "NUM_PROCS: $NUM_PROCS"
#NUM_PROCS=0
NUM_THREADS=0

panel serve \
"${DASHBOARD_FILE}" \
--setup "${SETUP_FILE}" \
--session-token-expiration "${SESSION_TOKEN_EXPIRATION}" \
--prefix "${PREFIX}" \
--use-xheaders --log-level "${LOG_LEVEL}" \
--static-dirs fonts=./fonts scripts=./scripts \
--num-procs $NUM_PROCS \
--num-threads $NUM_THREADS
