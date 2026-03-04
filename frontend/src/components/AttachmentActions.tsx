import { type ChangeEvent, useId, useRef } from "react";

interface AttachmentActionsProps {
  compact?: boolean;
  onUpload?: (file: File) => void;
  onDownload?: () => void;
  disabled?: boolean;
}

export function AttachmentActions({
  compact = false,
  onUpload,
  onDownload,
  disabled = false
}: AttachmentActionsProps): JSX.Element {
  const inputRef = useRef<HTMLInputElement | null>(null);
  const inputId = useId();

  const openFilePicker = (): void => {
    if (disabled || !onUpload) {
      return;
    }
    inputRef.current?.click();
  };

  const onInputChanged = (event: ChangeEvent<HTMLInputElement>): void => {
    const file = event.currentTarget.files?.[0];
    if (file && onUpload) {
      onUpload(file);
    }
    event.currentTarget.value = "";
  };

  return (
    <div className={`attachment-actions ${compact ? "attachment-actions--compact" : ""}`}>
      <input
        id={inputId}
        ref={inputRef}
        type="file"
        onChange={onInputChanged}
        tabIndex={-1}
        style={{ display: "none" }}
      />
      <button
        type="button"
        className="link-button"
        onClick={openFilePicker}
        disabled={disabled || !onUpload}
      >
        Upload
      </button>
      <button
        type="button"
        className="link-button"
        onClick={onDownload}
        disabled={disabled || !onDownload}
      >
        Download
      </button>
    </div>
  );
}
