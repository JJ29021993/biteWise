type Props = {
  reason: string;
};

export function EmptyState({ reason }: Props) {
  return (
    <section
      className="relative animate-fadeUp overflow-hidden rounded-2xl border border-stroke bg-surface-2 px-6 py-10 text-center shadow-card"
      role="status"
    >
      <div
        className="pointer-events-none absolute left-1/2 top-1/4 h-56 w-56 -translate-x-1/2 rounded-full bg-crimson/15 blur-2xl"
        aria-hidden
      />
      <span className="relative z-10 inline-flex rounded-full border border-crimson/40 bg-crimson/15 px-3 py-1 text-[11px] font-bold uppercase tracking-wide text-crimson-soft">
        Constraint boundary
      </span>
      <h3 className="relative z-10 mt-4 font-display text-2xl font-bold text-ink sm:text-3xl">
        No exact matches in this pocket
      </h3>
      <p className="relative z-10 mx-auto mt-3 max-w-lg text-muted">{reason}</p>
      <p className="relative z-10 mx-auto mt-4 max-w-md text-sm text-muted">
        Try another <strong className="text-ink">location</strong>, lower{" "}
        <strong className="text-ink">minimum rating</strong>, add a{" "}
        <strong className="text-ink">cuisine</strong>, or pick a wider{" "}
        <strong className="text-ink">budget</strong>.
      </p>
    </section>
  );
}
