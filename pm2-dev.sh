#!/bin/bash

# PM2 Development Server Manager for Orbital
# Supports multiple worktrees with dynamic port allocation

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Source port resolution script
source "$SCRIPT_DIR/scripts/resolve-ports.sh"

# Derive process names
API_NAME="orbital-api${ORBITAL_INSTANCE_SUFFIX}"
WEB_NAME="orbital-web${ORBITAL_INSTANCE_SUFFIX}"

case "$1" in
  start)
    echo -e "${GREEN}Starting Orbital dev servers...${NC}"
    if [ -n "$ORBITAL_INSTANCE_SUFFIX" ]; then
      echo -e "${BLUE}Workspace: ${ORBITAL_INSTANCE_SUFFIX#-}${NC}"
    fi
    pm2 restart ecosystem.config.js 2>/dev/null || pm2 start ecosystem.config.js
    echo ""
    echo -e "${GREEN}Servers started!${NC}"
    echo "  Frontend: http://localhost:${ORBITAL_WEB_PORT}"
    echo "  Backend:  http://localhost:${ORBITAL_API_PORT}"
    echo ""
    echo "Commands:"
    echo "  ./pm2-dev.sh logs     - View all logs"
    echo "  ./pm2-dev.sh web      - View frontend logs"
    echo "  ./pm2-dev.sh api      - View backend logs"
    echo "  ./pm2-dev.sh status   - Check status"
    echo "  ./pm2-dev.sh stop     - Stop servers"
    echo "  ./pm2-dev.sh ports    - Show port configuration"
    echo ""
    echo -e "${BLUE}Log files (for Claude to read):${NC}"
    echo "  ~/.pm2/logs/${API_NAME}-out.log"
    echo "  ~/.pm2/logs/${WEB_NAME}-out.log"
    ;;

  stop)
    echo -e "${YELLOW}Stopping servers...${NC}"
    pm2 stop ecosystem.config.js
    ;;

  restart)
    echo -e "${YELLOW}Restarting servers...${NC}"
    pm2 restart ecosystem.config.js
    ;;

  logs)
    echo -e "${GREEN}All logs (Ctrl+C to exit)${NC}"
    pm2 logs "$API_NAME" "$WEB_NAME" --timestamp="HH:mm:ss"
    ;;

  web|frontend)
    echo -e "${GREEN}Frontend logs (Ctrl+C to exit)${NC}"
    pm2 logs "$WEB_NAME" --timestamp="HH:mm:ss"
    ;;

  api|backend)
    echo -e "${GREEN}Backend logs (Ctrl+C to exit)${NC}"
    pm2 logs "$API_NAME" --timestamp="HH:mm:ss"
    ;;

  status)
    pm2 status
    ;;

  ports)
    echo -e "${GREEN}Port Configuration${NC}"
    echo ""
    if [ -n "$ORBITAL_INSTANCE_SUFFIX" ]; then
      echo -e "  Workspace:  ${BLUE}${ORBITAL_INSTANCE_SUFFIX#-}${NC}"
    else
      echo -e "  Workspace:  ${BLUE}(main worktree)${NC}"
    fi
    echo "  API Port:   ${ORBITAL_API_PORT}"
    echo "  Web Port:   ${ORBITAL_WEB_PORT}"
    echo "  API Name:   ${API_NAME}"
    echo "  Web Name:   ${WEB_NAME}"
    echo ""
    echo "URLs:"
    echo "  Frontend: http://localhost:${ORBITAL_WEB_PORT}"
    echo "  Backend:  http://localhost:${ORBITAL_API_PORT}"
    ;;

  flush)
    echo -e "${YELLOW}Flushing logs...${NC}"
    pm2 flush
    ;;

  kill)
    echo -e "${RED}Killing PM2 daemon...${NC}"
    pm2 kill
    ;;

  *)
    echo "Orbital Dev Server Manager"
    if [ -n "$ORBITAL_INSTANCE_SUFFIX" ]; then
      echo -e "Workspace: ${BLUE}${ORBITAL_INSTANCE_SUFFIX#-}${NC}"
    fi
    echo ""
    echo "Usage: $0 {start|stop|restart|logs|status|web|api|ports|flush|kill}"
    echo ""
    echo "Commands:"
    echo "  start   - Start frontend (${ORBITAL_WEB_PORT}) and backend (${ORBITAL_API_PORT})"
    echo "  stop    - Stop all servers"
    echo "  restart - Restart all servers"
    echo "  logs    - View all logs (real-time)"
    echo "  web     - View frontend logs only"
    echo "  api     - View backend logs only"
    echo "  ports   - Show port configuration"
    echo "  status  - Show server status"
    echo "  flush   - Clear log files"
    echo "  kill    - Kill PM2 daemon"
    echo ""
    echo "Log files for Claude:"
    echo "  ~/.pm2/logs/${API_NAME}-out.log"
    echo "  ~/.pm2/logs/${WEB_NAME}-out.log"
    exit 1
    ;;
esac
