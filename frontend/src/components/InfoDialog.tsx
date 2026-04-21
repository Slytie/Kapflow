import { type ReactNode, useEffect, useId, useState } from "react";

interface InfoDialogProps {
  triggerLabel: string;
  dialogTitle: string;
  dialogDescription?: string;
  children: ReactNode;
  className?: string;
  triggerContent?: ReactNode;
}

export function InfoDialog({
  triggerLabel,
  dialogTitle,
  dialogDescription,
  children,
  className,
  triggerContent
}: InfoDialogProps): JSX.Element {
  const [isOpen, setIsOpen] = useState(false);
  const titleId = useId();
  const descriptionId = useId();

  useEffect(() => {
    if (!isOpen) {
      return undefined;
    }
    const handleKeyDown = (event: KeyboardEvent): void => {
      if (event.key === "Escape") {
        setIsOpen(false);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => {
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [isOpen]);

  return (
    <>
      <button
        type="button"
        className={`info-button${className ? ` ${className}` : ""}`}
        aria-label={triggerLabel}
        onClick={() => {
          setIsOpen(true);
        }}
      >
        {triggerContent ?? "i"}
      </button>
      {isOpen ? (
        <div
          className="info-dialog-backdrop"
          onClick={(event) => {
            if (event.target === event.currentTarget) {
              setIsOpen(false);
            }
          }}
        >
          <section
            className="info-dialog"
            role="dialog"
            aria-modal="true"
            aria-labelledby={titleId}
            aria-describedby={dialogDescription ? descriptionId : undefined}
          >
            <header className="info-dialog__header">
              <div>
                <h2 id={titleId}>{dialogTitle}</h2>
                {dialogDescription ? <p id={descriptionId}>{dialogDescription}</p> : null}
              </div>
              <button
                type="button"
                className="action-btn"
                aria-label={`Close ${dialogTitle}`}
                onClick={() => {
                  setIsOpen(false);
                }}
              >
                Close
              </button>
            </header>
            <div className="info-dialog__body">{children}</div>
          </section>
        </div>
      ) : null}
    </>
  );
}
