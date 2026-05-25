#!/usr/bin/env bash
set -euo pipefail

SERVICE_NAME="sci-treatment-radar.service"
LOG_TAG="sci-treatment-radar-healthcheck"

if systemctl is-active --quiet "$SERVICE_NAME"; then
  systemd-cat -t "$LOG_TAG" echo "$SERVICE_NAME is active"
  exit 0
fi

systemd-cat -t "$LOG_TAG" echo "$SERVICE_NAME is not active, restarting"
systemctl restart "$SERVICE_NAME"
