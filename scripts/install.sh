#!/usr/bin/env bash
set -euo pipefail
mkdir -p data
docker compose up -d --build
