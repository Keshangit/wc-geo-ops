#!/bin/sh
set -e
exec python -m api.workers.full_worker
