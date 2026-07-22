#!/usr/bin/env bash
# Simple installer for the CodeCore Linux Agent.
set -e
echo "Installing CodeCore Linux Agent…"
INSTALL_DIR=/opt/codecore-agent
sudo mkdir -p "$INSTALL_DIR" /etc/codecore /var/lib/codecore-agent
sudo cp -r codecore_agent "$INSTALL_DIR/"
pip3 install -r requirements.txt
if [ ! -f /etc/codecore/agent.conf ]; then
  sudo cp agent.conf.example /etc/codecore/agent.conf
  echo "Created /etc/codecore/agent.conf — edit it with your collector URL + enroll secret."
fi
sudo cp codecore-agent.service codecore-agent.timer /etc/systemd/system/
echo "Installed. Edit /etc/codecore/agent.conf, then:"
echo "  sudo systemctl daemon-reload && sudo systemctl enable --now codecore-agent.timer"
echo "Or run once now:  sudo python3 -m codecore_agent.agent --once"
