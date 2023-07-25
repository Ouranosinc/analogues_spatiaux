export ANALOGUES_WRITE_DIR=./WRITE
panel serve ./Dashboard.py --port=9094 --allow-websocket-origin=* --static-dirs fonts=./fonts scripts=./scripts --autoreload --admin