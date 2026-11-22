export function Hero() {
  return (
    <section className="relative mb-8 overflow-hidden rounded-2xl border border-stroke bg-surface p-5 shadow-card sm:p-8">
      <div
        className="pointer-events-none absolute -right-24 -top-24 h-96 w-96 rounded-full bg-crimson-bright/10 blur-3xl"
        aria-hidden
      />
      <div className="relative z-10 flex flex-col justify-between gap-4 md:flex-row md:items-end">
        <div className="max-w-2xl space-y-2">
          <p className="inline-flex items-center gap-2 text-[11px] font-bold uppercase tracking-[0.14em] text-crimson-bright">
            <span className="h-2 w-2 animate-pulseDot rounded-full bg-crimson-bright" />
            Neural Engine
          </p>
          <h1 className="font-display text-4xl font-bold tracking-tight text-ink sm:text-5xl">
            BiteWise<span className="text-crimson-bright">.</span>
          </h1>
          <p className="font-body text-lg text-[#E4BEBC]">
            Discover restaurants that match your taste
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {["Bangalore", "Zomato listings", "AI shortlist"].map((label) => (
            <span
              key={label}
              className="rounded-full border border-stroke bg-surface-2 px-3 py-1.5 text-sm font-semibold text-ink shadow-sm"
            >
              {label}
            </span>
          ))}
        </div>
      </div>
    </section>
  );
}
