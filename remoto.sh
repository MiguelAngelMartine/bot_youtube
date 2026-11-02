#!/bin/bash
# Mantiene Claude Code accesible desde el navegador (claude.ai/code) sin SSH.
# Corre `claude remote-control` dentro de tmux (sesión «remoto»); si no está, lo arranca.
# Lo llama el cron al encender el servidor y cada 5 minutos como vigilante.
export PATH="/home/miguel/.local/bin:/usr/local/bin:/usr/bin:/bin"
cd /home/miguel/bot_youtube || exit 1
tmux has-session -t remoto 2>/dev/null && exit 0
tmux new-session -d -s remoto -c /home/miguel/bot_youtube \
  "claude remote-control --name 'Servidor bot_youtube' --spawn=same-dir"
