export function TopBar() {
  return (
    <header className="sticky top-0 z-40 border-b border-stroke/80 bg-surface-lowest/85 backdrop-blur-xl">
      <div className="mx-auto flex h-16 max-w-shell items-center justify-between gap-4 px-4 sm:px-6">
        <div className="flex min-w-0 flex-wrap items-center gap-2 sm:gap-3">
          <div className="flex items-center gap-2">
            <span className="font-display text-xl font-bold tracking-tight text-crimson-soft sm:text-2xl">
              BiteWise
            </span>
            <span className="rounded-full bg-surface-high px-2 py-0.5 text-[11px] font-bold uppercase tracking-[0.08em] text-[#E4BEBC]">
              AI Curated
            </span>
          </div>
          <span className="hidden text-sm text-muted md:inline">
            Discover restaurants that match your taste
          </span>
          <span className="hidden items-center gap-1 rounded-full bg-surface-2 px-2.5 py-1 text-xs font-semibold text-ink lg:inline-flex">
            <span className="text-crimson">◉</span> Bangalore
          </span>
          <span className="hidden items-center gap-1 rounded-full bg-surface px-2.5 py-1 text-[11px] font-semibold text-muted xl:inline-flex">
            Zomato Verified
          </span>
        </div>
        <div className="flex items-center gap-2">
          <nav className="hidden items-center gap-1 md:flex" aria-label="Primary">
            <span className="rounded-lg bg-crimson-bright px-2.5 py-1.5 text-sm font-semibold text-[#5B000E]">
              Discovery Feed
            </span>
            <span className="rounded-lg px-2.5 py-1.5 text-sm font-semibold text-[#E4BEBC]">
              Taste Match
            </span>
            <span className="rounded-lg px-2.5 py-1.5 text-sm font-semibold text-[#E4BEBC]">
              Collections
            </span>
          </nav>
          <span className="inline-flex items-center gap-1.5 rounded-full bg-tertiary/20 px-2.5 py-1 text-[11px] font-bold text-tertiary">
            <span className="h-1.5 w-1.5 animate-pulseDot rounded-full bg-tertiary" />
            AI Shortlist Ready
          </span>
        </div>
      </div>
    </header>
  );
}
