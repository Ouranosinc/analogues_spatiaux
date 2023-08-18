#!/bin/bash

SESSION_TOKEN_EXPIRATION=86400
PREFIX="analogs"
LOG_LEVEL="debug"
MAX_PROCS=$(nproc --all)

NUM_PROCS=$((MAX_PROCS - 1 > 16 ? 16 : MAX_PROCS - 1))
NUM_THREADS=0

panel serve Dashboard.py --session-token-expiration "${SESSION_TOKEN_EXPIRATION}" --prefix "${PREFIX}" --use-xheaders --log-level="${LOG_LEVEL}" --static-dirs fonts=./fonts scripts=./scripts --num-procs $NUM_PROCS --num-threads $NUM_THREADS
