import { createContext, useContext, useMemo, useState } from "react";
import type { PropsWithChildren } from "react";

import type { DrawerPayload } from "@/lib/types/ui";

interface DrawerContextValue {
  payload: DrawerPayload | null;
  open: (payload: DrawerPayload) => void;
  close: () => void;
}

const DrawerContext = createContext<DrawerContextValue | null>(null);

export function DrawerProvider({ children }: PropsWithChildren): JSX.Element {
  const [payload, setPayload] = useState<DrawerPayload | null>(null);

  const value = useMemo<DrawerContextValue>(
    () => ({
      payload,
      open: (nextPayload) => setPayload(nextPayload),
      close: () => setPayload(null)
    }),
    [payload]
  );

  return <DrawerContext.Provider value={value}>{children}</DrawerContext.Provider>;
}

export function useDrawer(): DrawerContextValue {
  const context = useContext(DrawerContext);
  if (!context) {
    throw new Error("useDrawer must be used inside DrawerProvider");
  }
  return context;
}
