import { useState, type FormEvent, type ReactNode } from "react";

import { capxPmFeDemoReviewCode } from "@/pages/capx-pm-fe-demo/capxPmFeDemoCopy";
import "./capxPmFeDemoV2.css";

const ACCESS_STORAGE_KEY = "capx_pm_fe_demo_v2_access_granted";

function readAccess(): boolean {
  try {
    return window.sessionStorage.getItem(ACCESS_STORAGE_KEY) === "true";
  } catch {
    return false;
  }
}

function writeAccess(): void {
  try {
    window.sessionStorage.setItem(ACCESS_STORAGE_KEY, "true");
  } catch {
    // Session-only local review speed bump.
  }
}

export function resetCapxPmFeDemoV2AccessForTest(): void {
  try {
    window.sessionStorage.removeItem(ACCESS_STORAGE_KEY);
  } catch {
    // Test helper only.
  }
}

export function CapxPmFeDemoV2AccessGate({ children }: { children: ReactNode }): JSX.Element {
  const [enteredCode, setEnteredCode] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [hasAccess, setHasAccess] = useState(readAccess);

  function handleSubmit(event: FormEvent<HTMLFormElement>): void {
    event.preventDefault();
    if (enteredCode.trim() !== capxPmFeDemoReviewCode) {
      setError("Use the local handoff phrase for this design review.");
      return;
    }
    writeAccess();
    setError(null);
    setHasAccess(true);
  }

  if (hasAccess) {
    return <>{children}</>;
  }

  return (
    <main className="capx-pm-v2 capx-pm-v2-gate" data-testid="capx-pm-v2-access-gate">
      <section className="capx-pm-v2-gate__panel" aria-labelledby="capx-pm-v2-gate-title">
        <p className="capx-pm-v2-eyebrow">CAPX PM Demo V2</p>
        <h1 id="capx-pm-v2-gate-title">Private design review</h1>
        <p>
          V2 is a separate local prototype. The first PM demo route remains available and unchanged at
          `/demo/capx/pm/projects`.
        </p>
        <form onSubmit={handleSubmit}>
          <label htmlFor="capx-pm-v2-review-code">Local handoff phrase</label>
          <input
            id="capx-pm-v2-review-code"
            autoComplete="off"
            onChange={(event) => setEnteredCode(event.target.value)}
            placeholder="capx-demo-local"
            type="text"
            value={enteredCode}
          />
          {error ? <p role="alert">{error}</p> : null}
          <button type="submit">Open V2</button>
        </form>
      </section>
    </main>
  );
}
