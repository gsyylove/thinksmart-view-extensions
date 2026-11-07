#!/usr/bin/env bash
set -euo pipefail
target="${1:-all}"
case "$target" in all|weather|music) ;; *) echo 'Usage: bash uninstall.sh [all|weather|music]' >&2; exit 1;; esac
if [[ "$(id -un)" != ubuntu ]]; then echo 'Run as ubuntu.' >&2; exit 1; fi
sudo -v
if [[ "$target" == all || "$target" == weather ]]; then
  if [[ -f /opt/thinksmart/extensions/weather/install.py ]]; then
    sudo python3 /opt/thinksmart/extensions/weather/install.py --remove
  fi
fi
if [[ "$target" == all || "$target" == music ]]; then
  if [[ -f /opt/thinksmart/extensions/music/install.py ]]; then
    sudo python3 /opt/thinksmart/extensions/music/install.py --remove
  fi
  if systemctl list-unit-files thinksmart-music.service --no-legend | grep -q thinksmart-music; then
    sudo systemctl disable --now thinksmart-music
  fi
fi
sudo systemctl daemon-reload
systemctl --user restart xiaozhi-hub
sudo systemctl restart thinksmart-client
echo 'Hooks removed. Module files, backups and account data remain on this device.'
