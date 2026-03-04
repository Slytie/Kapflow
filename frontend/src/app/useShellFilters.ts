import { useMemo } from "react";
import { useSearchParams } from "react-router-dom";

import { parseFilters, toSearchParams } from "@/lib/state/urlFilters";
import type { ShellFilters } from "@/lib/types/ui";

export function useShellFilters(): {
  filters: ShellFilters;
  setFilters: (next: ShellFilters) => void;
} {
  const [searchParams, setSearchParams] = useSearchParams();

  const filters = useMemo(() => parseFilters(searchParams), [searchParams]);

  return {
    filters,
    setFilters: (next) => setSearchParams(toSearchParams(next), { replace: true })
  };
}
