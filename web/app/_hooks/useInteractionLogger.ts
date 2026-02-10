/**
 * Hook for logging user interactions with debouncing.
 *
 * Part D3 of Phase 2: Debounce rapid interactions to avoid flooding system events.
 */

import { useCallback, useRef, useEffect } from "react";
import { api } from "@/app/_lib/api";

interface InteractionEvent {
  type: string;
  [key: string]: unknown;
}

const DEBOUNCE_MS = 500;

/**
 * Hook to log user interactions with debouncing.
 *
 * Batches rapid interactions into a single system event to avoid flooding.
 */
export function useInteractionLogger(sessionId: string | null) {
  const pendingEvents = useRef<InteractionEvent[]>([]);
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const lastSessionId = useRef<string | null>(sessionId);

  // Flush pending events to API
  const flush = useCallback(() => {
    if (!lastSessionId.current || pendingEvents.current.length === 0) return;

    const events = [...pendingEvents.current];
    pendingEvents.current = [];

    // Summarize events by type
    const summary = summarizeEvents(events);

    api.logSystemEvent(
      lastSessionId.current,
      "user_interaction",
      summary,
      { events }
    ).catch((err) => {
      // Log in development for debugging, silently fail in production
      if (process.env.NODE_ENV === "development") {
        console.warn("Failed to log interaction events:", err);
      }
    });
  }, []);

  // Log an interaction (debounced)
  const logInteraction = useCallback((event: InteractionEvent) => {
    pendingEvents.current.push(event);

    // Reset debounce timer
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
    }

    timeoutRef.current = setTimeout(() => {
      flush();
    }, DEBOUNCE_MS);
  }, [flush]);

  // Flush when session changes
  useEffect(() => {
    if (sessionId !== lastSessionId.current) {
      flush();
      lastSessionId.current = sessionId;
    }
  }, [sessionId, flush]);

  // Flush on unmount - capture current state to avoid stale closure issues
  useEffect(() => {
    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
        timeoutRef.current = null;
      }
      // Directly flush with current refs to avoid stale closure
      const currentSessionId = lastSessionId.current;
      const currentEvents = pendingEvents.current;
      if (currentSessionId && currentEvents.length > 0) {
        const events = [...currentEvents];
        pendingEvents.current = [];
        api.logSystemEvent(
          currentSessionId,
          "user_interaction",
          summarizeEvents(events),
          { events }
        ).catch((err) => {
          // Log in development for debugging
          if (process.env.NODE_ENV === "development") {
            console.warn("Failed to flush interaction events on unmount:", err);
          }
        });
      }
    };
  }, []); // Empty deps - cleanup should use refs directly

  return { logInteraction };
}

/**
 * Summarize events into a human-readable string.
 */
function summarizeEvents(events: InteractionEvent[]): string {
  const counts: Record<string, number> = {};

  for (const event of events) {
    const type = event.type;
    counts[type] = (counts[type] || 0) + 1;
  }

  const parts: string[] = [];
  for (const [type, count] of Object.entries(counts)) {
    if (type === "node_click") {
      parts.push(`clicked ${count} node${count > 1 ? "s" : ""}`);
    } else if (type === "edge_click") {
      parts.push(`clicked ${count} edge${count > 1 ? "s" : ""}`);
    } else if (type === "point_click") {
      parts.push(`clicked ${count} point${count > 1 ? "s" : ""}`);
    } else {
      parts.push(`${count} ${type} event${count > 1 ? "s" : ""}`);
    }
  }

  return parts.length > 0 ? `User ${parts.join(", ")}` : "User interaction";
}
