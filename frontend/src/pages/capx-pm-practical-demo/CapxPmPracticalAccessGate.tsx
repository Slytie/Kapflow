import { useState, type ReactNode } from "react";

interface CapxPmPracticalAccessGateProps {
  children: ReactNode;
}

const ACKNOWLEDGEMENT_KEY = "capx-pm-practical-demo-acknowledged";

function readAcknowledgement(): boolean {
  try {
    return window.sessionStorage.getItem(ACKNOWLEDGEMENT_KEY) === "true";
  } catch {
    return false;
  }
}

function writeAcknowledgement(): void {
  try {
    window.sessionStorage.setItem(ACKNOWLEDGEMENT_KEY, "true");
  } catch {
    // Session storage can be unavailable in tests or hardened browsers.
  }
}

export function resetCapxPmPracticalAcknowledgementForTest(): void {
  try {
    window.sessionStorage.removeItem(ACKNOWLEDGEMENT_KEY);
  } catch {
    // Test helper only.
  }
}

export function CapxPmPracticalAccessGate({ children }: CapxPmPracticalAccessGateProps): JSX.Element {
  const [acknowledged, setAcknowledged] = useState(readAcknowledgement);

  if (acknowledged) {
    return <>{children}</>;
  }

  return (
    <main className="capx-pm-practical-demo capx-pm-practical-gate" data-testid="capx-pm-practical-access-gate">
      <section className="capx-pm-practical-gate__panel" aria-labelledby="capx-pm-practical-gate-title">
        <p className="capx-pm-practical-eyebrow">Private design demo</p>
        <h1 id="capx-pm-practical-gate-title">CAPX PM Project Workspace</h1>
        <p>
          This throw-away route uses fake mock project data only. The acknowledgement below is a local
          design-review screen; it does not protect bundled JavaScript, images, or mock data.
        </p>
        <p>
          Shared previews need protection outside the frontend bundle, such as private hosting, VPN,
          SSO, or reverse-proxy access control.
        </p>
        <button
          type="button"
          onClick={() => {
            writeAcknowledgement();
            setAcknowledged(true);
          }}
        >
          Acknowledge and open demo
        </button>
      </section>
    </main>
  );
}
