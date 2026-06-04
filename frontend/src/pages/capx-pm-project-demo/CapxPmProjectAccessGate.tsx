import { useState, type ReactNode } from "react";

const ACKNOWLEDGEMENT_KEY = "capx-pm-project-demo-acknowledged";

interface CapxPmProjectAccessGateProps {
  children: ReactNode;
}

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
    // Session storage can be unavailable in private or restricted browser modes.
  }
}

export function resetCapxPmProjectAcknowledgementForTest(): void {
  try {
    window.sessionStorage.removeItem(ACKNOWLEDGEMENT_KEY);
  } catch {
    // Test helper only.
  }
}

export function CapxPmProjectAccessGate({ children }: CapxPmProjectAccessGateProps): JSX.Element {
  const [acknowledged, setAcknowledged] = useState(readAcknowledgement);

  if (acknowledged) {
    return <>{children}</>;
  }

  return (
    <main className="capx-pm-project-demo capx-pm-access-gate" data-testid="capx-pm-access-gate">
      <section className="capx-pm-access-gate__panel" aria-labelledby="capx-pm-access-gate-title">
        <p className="capx-pm-eyebrow">Private design demo</p>
        <h1 id="capx-pm-access-gate-title">CAPX PM Project Workflow</h1>
        <p>
          This throw-away route uses fake mock data only. The acknowledgement below is a local
          design-review speed bump; it does not protect bundled JavaScript, images, or mock data.
        </p>
        <p>
          Shared previews need protection outside the frontend bundle, such as private hosting,
          VPN, SSO, or reverse-proxy access control.
        </p>
        <button
          type="button"
          className="capx-pm-command-button"
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
