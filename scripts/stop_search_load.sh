#!/usr/bin/env bash
set -euo pipefail

kubectl -n lab-main delete deploy/main-search-load --ignore-not-found
