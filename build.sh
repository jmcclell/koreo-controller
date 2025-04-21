#!/bin/bash
set -euo pipefail
set -x

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

rsync -a --exclude '.git' --exclude '.devbox' --exclude '.envrc' --exclude 'devbox.json' --exclude '.venv' "${SCRIPT_DIR}/../koreo-core/" "${SCRIPT_DIR}/koreo-core"

docker build -t koreo-controller:local "${SCRIPT_DIR}"
kind load docker-image koreo-controller:local --name deployments-demo
kubectl delete pods -l app.kubernetes.io/instance=koreo-controller
