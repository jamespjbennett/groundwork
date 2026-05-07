# Groundwork — thin wrappers around scripts/ (Option B quick setup)

.PHONY: setup start start-web start-all stop status logs logs-web

setup:
	bash scripts/setup.sh

start:
	bash scripts/start.sh

start-web:
	bash scripts/start-web.sh

start-all: start start-web

stop:
	bash scripts/stop.sh

status:
	@test -f api/.groundwork-server.pid && kill -0 "$$(cat api/.groundwork-server.pid)" 2>/dev/null && echo "API    running (PID $$(cat api/.groundwork-server.pid))" || echo "API    not running"
	@test -f web/.groundwork-web.pid && kill -0 "$$(cat web/.groundwork-web.pid)" 2>/dev/null && echo "Web    running (PID $$(cat web/.groundwork-web.pid))" || echo "Web    not running"
	@curl -s -o /dev/null -w "GET /docs   → HTTP %{http_code}\n" http://127.0.0.1:8000/docs || true
	@curl -s -o /dev/null -w "GET :3000/ → HTTP %{http_code}\n" http://127.0.0.1:3000/ || true

logs:
	@test -f api/.groundwork-server.log && tail -n 80 api/.groundwork-server.log || echo "no API log yet"

logs-web:
	@test -f web/.groundwork-web.log && tail -n 80 web/.groundwork-web.log || echo "no web log yet"
