import { IconCheck, IconDining } from "@/components/icons";

const PRESETS = [
  "Quiet cafes in Indiranagar",
  "Best sushi under ₹1500",
  "Romantic Cunningham Road",
];

type Props = {
  onPreset?: (label: string) => void;
};

export function IdlePanel({ onPreset }: Props) {
  return (
    <section className="relative animate-fadeUp overflow-hidden rounded-2xl border border-stroke bg-surface-2 px-6 py-10 text-center shadow-card sm:px-10">
      <div
        className="pointer-events-none absolute left-1/2 top-1/4 h-64 w-64 -translate-x-1/2 rounded-full bg-[#B1021E]/10 blur-2xl"
        aria-hidden
      />
      <div className="relative z-10 mx-auto mb-4 grid h-20 w-20 place-items-center rounded-full bg-surface-high text-crimson-bright shadow-md">
        <IconDining className="h-10 w-10" />
      </div>
      <h3 className="relative z-10 font-display text-3xl font-bold tracking-tight text-ink">
        Your AI Tasting Menu Awaits
      </h3>
      <p className="relative z-10 mx-auto mt-3 max-w-lg text-base text-muted">
        Select your dining mood, location, and cuisine preferences on the left.
        BiteWise will filter verified Bangalore listings and rank an explained
        shortlist tailored to you.
      </p>
      <div className="relative z-10 mt-6 flex flex-wrap items-center justify-center gap-2">
        {PRESETS.map((label) => (
          <button
            key={label}
            type="button"
            onClick={() => onPreset?.(label)}
            className="rounded-lg border border-stroke bg-surface-high px-4 py-2 text-sm font-semibold text-ink transition hover:bg-surface-3"
          >
            {label}
          </button>
        ))}
      </div>
      <p className="relative z-10 mt-8 inline-flex items-center gap-2 rounded-full bg-tertiary/15 px-3 py-1.5 text-xs font-semibold text-tertiary">
        <span className="grid h-4 w-4 place-items-center rounded-full bg-tertiary/25">
          <IconCheck className="h-3 w-3" />
        </span>
        Strict ground truth — ratings and cost come from Zomato listings
      </p>
    </section>
  );
}
