import { useSyncExternalStore } from "react";

const subscribe = () => () => undefined;

/**
 * False during server rendering and hydration, true once React controls the page.
 * Credential forms keep their submit button disabled until then, so an early Enter can
 * never fall back to a native form submission.
 */
export function useHydrated(): boolean {
  return useSyncExternalStore(
    subscribe,
    () => true,
    () => false,
  );
}
