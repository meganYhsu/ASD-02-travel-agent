#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 2 ]]; then
  printf 'Usage: bash deployment/aws/tunnel.sh KEY_FILE ubuntu@EC2_PUBLIC_IP\n' >&2
  exit 2
fi

ssh -N -o ExitOnForwardFailure=yes -o IdentitiesOnly=yes \
  -i "$1" \
  -L 127.0.0.1:8080:127.0.0.1:8080 \
  -L 127.0.0.1:3001:127.0.0.1:3001 \
  -L 127.0.0.1:3002:127.0.0.1:3002 \
  -L 127.0.0.1:3003:127.0.0.1:3003 \
  -L 127.0.0.1:3004:127.0.0.1:3004 \
  -L 127.0.0.1:5004:127.0.0.1:5004 \
  -L 127.0.0.1:8505:127.0.0.1:8505 \
  "$2"
