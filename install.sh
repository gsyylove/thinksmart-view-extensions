#!/usr/bin/env bash
set -euo pipefail

target="${1:-all}"
case "$target" in all|weather|music) ;; *) echo 'Usage: bash install.sh [all|weather|music]' >&2; exit 1;; esac
if [[ "$(id -un)" != ubuntu ]]; then
  echo 'Run this script as the device ubuntu user. It invokes sudo for system files.' >&2
  exit 1
fi
root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
client=/opt/thinksmart/client/current
hub="$HOME/xiaozhi-hub-server/main/xiaozhi-server"
test -f "$client/web/v2/index.html"
test -f "$hub/core/handle/receiveAudioHandle.py"
sudo -v

if [[ "$target" == all || "$target" == music ]]; then
  uv="$HOME/.local/bin/uv"
  if [[ ! -x "$uv" ]]; then
    echo 'Missing uv. Install uv for ubuntu before continuing.' >&2
    exit 1
  fi
  env_dir="$HOME/thinksmart-music/venv"
  if [[ ! -x "$env_dir/bin/python" ]]; then
    "$uv" venv --python python3 "$env_dir"
  fi
  "$uv" pip install --python "$env_dir/bin/python" -r "$root/extensions/music/requirements.txt"
  sudo mkdir -p /opt/thinksmart/extensions/music
  for file in server.py voice.py music.js music.css install.py README.md requirements.txt; do
    sudo install -m 644 "$root/extensions/music/$file" "/opt/thinksmart/extensions/music/$file"
  done
  sudo install -m 644 "$root/extensions/music/thinksmart-music.service" /etc/systemd/system/thinksmart-music.service
  sudo python3 /opt/thinksmart/extensions/music/install.py
  sudo systemctl daemon-reload
  sudo systemctl enable thinksmart-music
  sudo systemctl restart thinksmart-music
fi

if [[ "$target" == all || "$target" == weather ]]; then
  sudo mkdir -p /opt/thinksmart/extensions/weather
  for file in backend.py voice.py weather.js weather.css install.py README.md; do
    sudo install -m 644 "$root/extensions/weather/$file" "/opt/thinksmart/extensions/weather/$file"
  done
  sudo python3 /opt/thinksmart/extensions/weather/install.py
fi

systemctl --user restart xiaozhi-hub
sudo systemctl restart thinksmart-client
echo 'Installed. Allow the gateway a moment to finish loading its speech models.'
