export function LoadingState() {
  return (
    <section
      className="animate-fadeUp rounded-2xl border border-stroke bg-surface-2 p-4 shadow-card sm:p-5"
      aria-busy="true"
      aria-live="polite"
    >
      <div className="mb-4 flex items-start justify-between gap-3">
        <div>
          <p className="font-display text-lg font-bold text-ink">
            BiteWise Neural Ranker
          </p>
          <p className="mt-1 text-sm text-muted">
            Analyzing Bangalore restaurant candidates…
          </p>
        </div>
        <span className="rounded-full bg-tertiary/15 px-2.5 py-1 text-[11px] font-bold uppercase tracking-wide text-tertiary">
          Synthesizing
        </span>
      </div>

      <div className="mb-5 flex flex-wrap gap-2">
        <span className="inline-flex items-center gap-1.5 rounded-lg border border-tertiary/30 bg-tertiary/10 px-3 py-1.5 text-xs font-semibold text-tertiary">
          ✓ Filter pool
        </span>
        <span className="inline-flex items-center gap-1.5 rounded-lg border border-tertiary/30 bg-tertiary/10 px-3 py-1.5 text-xs font-semibold text-tertiary">
          ✓ Vector alignment
        </span>
        <span className="inline-flex items-center gap-1.5 rounded-lg border border-crimson/40 bg-crimson/10 px-3 py-1.5 text-xs font-semibold text-crimson-soft">
          <span className="h-2 w-2 animate-pulseDot rounded-full bg-crimson-bright" />
          Review synthesis
        </span>
      </div>

      {[0, 1, 2].map((index) => (
        <div
          key={index}
          className={`mb-3 rounded-xl border border-stroke bg-surface p-3 ${
            index === 2 ? "opacity-55" : ""
          }`}
        >
          <div className="mb-3 h-16 animate-shimmer rounded-lg bg-[linear-gradient(90deg,#292A2D_0%,#343538_50%,#292A2D_100%)] bg-[length:200%_100%]" />
          <div className="mb-2 h-3 w-[60%] animate-shimmer rounded bg-[linear-gradient(90deg,#292A2D_0%,#343538_50%,#292A2D_100%)] bg-[length:200%_100%]" />
          <div className="mb-2 h-3 w-[90%] animate-shimmer rounded bg-[linear-gradient(90deg,#292A2D_0%,#343538_50%,#292A2D_100%)] bg-[length:200%_100%]" />
          <div className="h-3 w-[75%] animate-shimmer rounded bg-[linear-gradient(90deg,#292A2D_0%,#343538_50%,#292A2D_100%)] bg-[length:200%_100%]" />
        </div>
      ))}
    </section>
  );
}
