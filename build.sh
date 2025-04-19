#!/bin/bash
set -euo pipefail
set -x

rsync -a --exclude '.git' --exclude '.devbox' --exclude '.envrc' --exclude 'devbox.json' --exclude '.venv' ../koreo-core/ ./koreo-core

docker build -t koreo-controller:local .
kind load docker-image koreo-controller:local --name deployments-demo
kubectl delete pods -l app.kubernetes.io/instance=koreo-controller
