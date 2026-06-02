import { useState, type ReactNode } from "react";

const ACKNOWLEDGEMENT_KEY = "capx-ceo-cockpit-demo-acknowledged";

interface CapxCeoCockpitAccessGateProps {
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

export function resetCapxCeoCockpitAcknowledgementForTest(): void {
  try {
    window.sessionStorage.removeItem(ACKNOWLEDGEMENT_KEY);
  } catch {
    // Test helper only.
  }
}

export function CapxCeoCockpitAccessGate({ children }: CapxCeoCockpitAccessGateProps): JSX.Element {
  const [acknowledged, setAcknowledged] = useState(readAcknowledgement);

  if (acknowledged) {
    return <>{children}</>;
  }

  return (
    <main className="capx-ceo-cockpit-demo capx-access-gate" data-testid="capx-access-gate">
      <section className="capx-access-gate__panel" aria-labelledby="capx-access-gate-title">
        <p className="capx-access-gate__eyebrow">Private design demo</p>
        <h1 id="capx-access-gate-title">CAPX CEO Cockpit</h1>
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
          className="capx-command-button"
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
