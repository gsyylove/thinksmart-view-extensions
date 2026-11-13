#!/usr/bin/env bash
set -euo pipefail
target="${1:-all}"
case "$target" in all|weather|music) ;; *) echo 'Usage: bash uninstall.sh [all|weather|music]' >&2; exit 1;; esac
if [[ "$(id -un)" != ubuntu ]]; then echo 'Run as ubuntu.' >&2; exit 1; fi
sudo -v
if [[ "$target" == all || "$target" == weather ]]; then
  sudo rm -f /opt/thinksmart/extensions/runtime/weather.enabled
  if grep -q '<!-- local-weather -->' /opt/thinksmart/client/current/web/v2/index.html; then
    sudo python3 /opt/thinksmart/extensions/weather/install.py --remove
  fi
fi
if [[ "$target" == all || "$target" == music ]]; then
  sudo rm -f /opt/thinksmart/extensions/runtime/music.enabled
  if grep -q '<!-- local-music -->' /opt/thinksmart/client/current/web/v2/index.html; then
    sudo python3 /opt/thinksmart/extensions/music/install.py --remove
  fi
  if systemctl list-unit-files thinksmart-music.service --no-legend | grep -q thinksmart-music; then
    sudo systemctl disable --now thinksmart-music
  fi
fi
if [[ ! -f /opt/thinksmart/extensions/runtime/music.enabled && ! -f /opt/thinksmart/extensions/runtime/weather.enabled ]]; then
  sudo rm -f /etc/systemd/system/thinksmart-client.service.d/thinksmart-extensions.conf /etc/systemd/user/xiaozhi-hub.service.d/thinksmart-extensions.conf
fi
sudo systemctl daemon-reload
systemctl --user daemon-reload
systemctl --user restart xiaozhi-hub
sudo systemctl restart thinksmart-client
echo 'Hooks removed. Module files, backups and account data remain on this device.'
