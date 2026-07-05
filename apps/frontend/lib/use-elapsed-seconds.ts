import { useEffect, useRef, useState } from "react";

/**
 * Verstrichene Sekunden, seit `active` zuletzt auf true wechselte - für ein
 * "Wird generiert… (12s)"-Feedback bei lang laufenden Requests (Studio-
 * Generierung, Chat-Antwort). Zaehlt waehrend `active` hochzaehlt, setzt bei
 * jedem Start (false -> true) zurueck auf 0 und stoppt/haelt den letzten
 * Stand, sobald `active` wieder false wird.
 */
export function useElapsedSeconds(active: boolean): number {
  const [elapsed, setElapsed] = useState(0);
  const startedAtRef = useRef<number | null>(null);

  useEffect(() => {
    if (!active) return;

    startedAtRef.current = Date.now();
    setElapsed(0);
    const interval = setInterval(() => {
      const startedAt = startedAtRef.current;
      if (startedAt !== null) {
        setElapsed(Math.floor((Date.now() - startedAt) / 1000));
      }
    }, 1000);

    return () => clearInterval(interval);
  }, [active]);

  return elapsed;
}
