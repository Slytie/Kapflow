import type { PropsWithChildren } from "react";

interface LaneColumnProps extends PropsWithChildren {
  title: string;
  count: number;
}

export function LaneColumn({ title, count, children }: LaneColumnProps): JSX.Element {
  return (
    <section className="lane-column" aria-label={title}>
      <header>
        <h3>{title}</h3>
        <span>{count}</span>
      </header>
      <div className="lane-column__content">{children}</div>
    </section>
  );
}
