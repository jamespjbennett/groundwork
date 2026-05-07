import { randomUUID } from "node:crypto";

// Mirrors api/session_manager.py — keep these in sync if the timeout changes.
const SESSION_TIMEOUT_MS = 30 * 60 * 1000;

let _sessionId: string | null = null;
let _lastActivityMs = 0;

// Returns the current session id, rotating to a fresh UUID after
// SESSION_TIMEOUT_MS of inactivity. The first call on activation
// always allocates a new id.
export function getSessionId(): string {
  const now = Date.now();
  if (_sessionId === null || now - _lastActivityMs > SESSION_TIMEOUT_MS) {
    _sessionId = randomUUID();
  }
  _lastActivityMs = now;
  return _sessionId;
}
