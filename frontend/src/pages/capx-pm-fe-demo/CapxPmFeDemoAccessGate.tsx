import { useState, type FormEvent, type ReactNode } from "react";

import { capxPmFeDemoGateCopy, capxPmFeDemoReviewCode } from "./capxPmFeDemoCopy";
import "./capxPmFeDemo.css";

const ACCESS_STORAGE_KEY = "capx_pm_fe_demo_access_granted";

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
    // Session storage is optional for this local-only speed bump.
  }
}

export function resetCapxPmFeDemoAccessForTest(): void {
  try {
    window.sessionStorage.removeItem(ACCESS_STORAGE_KEY);
  } catch {
    // Test helper only.
  }
}

export function CapxPmFeDemoAccessGate({ children }: { children: ReactNode }): JSX.Element {
  const [enteredCode, setEnteredCode] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [hasAccess, setHasAccess] = useState(readAccess);

  function handleSubmit(event: FormEvent<HTMLFormElement>): void {
    event.preventDefault();
    if (enteredCode.trim() !== capxPmFeDemoReviewCode) {
      setError("Review code did not match. Use the local demo handoff phrase.");
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
    <main className="capx-pm-fe-demo capx-pm-fe-gate" data-testid="capx-pm-fe-access-gate">
      <section className="capx-pm-fe-gate__card" aria-labelledby="capx-pm-fe-gate-title">
        <p className="capx-pm-fe-eyebrow">CAPX PM Demo</p>
        <h1 id="capx-pm-fe-gate-title">{capxPmFeDemoGateCopy.title}</h1>
        <p>{capxPmFeDemoGateCopy.body}</p>
        <form className="capx-pm-fe-gate__form" onSubmit={handleSubmit}>
          <label htmlFor="capx-pm-fe-review-code">Local review code</label>
          <input
            id="capx-pm-fe-review-code"
            autoComplete="off"
            value={enteredCode}
            onChange={(event) => setEnteredCode(event.target.value)}
            placeholder="Use local handoff phrase"
            type="text"
          />
          {error ? <p role="alert">{error}</p> : null}
          <button type="submit">Open demo</button>
        </form>
        <p className="capx-pm-fe-security-note">{capxPmFeDemoGateCopy.security}</p>
      </section>
    </main>
  );
}
