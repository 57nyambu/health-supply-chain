"use client";

import { MutationCache, QueryCache, QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState } from "react";

import { ToastProvider } from "@/components/ui/toast";
import { authRoute } from "@/lib/auth/session";

/** Expired sessions, locked workstations and missing MFA move the user to that screen. */
function routeAuthProblem(error: unknown) {
  const route = authRoute(error);
  if (route && window.location.pathname !== route) window.location.assign(route);
}

export function Providers({ children }: { children: React.ReactNode }) {
  const [client] = useState(
    () =>
      new QueryClient({
        queryCache: new QueryCache({ onError: routeAuthProblem }),
        mutationCache: new MutationCache({ onError: routeAuthProblem }),
        defaultOptions: {
          // Patient data is never kept around longer than the screen that shows it.
          queries: { retry: false, staleTime: 0, gcTime: 60_000, refetchOnWindowFocus: false },
          mutations: { retry: false },
        },
      }),
  );
  return (
    <QueryClientProvider client={client}>
      <ToastProvider>{children}</ToastProvider>
    </QueryClientProvider>
  );
}
