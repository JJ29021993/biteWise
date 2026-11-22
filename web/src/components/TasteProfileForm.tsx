"use client";

import { IconSparkle, IconTune } from "@/components/icons";
import type { Budget, PreferenceForm } from "@/lib/types";

type Props = {
  value: PreferenceForm;
  locations: string[];
  cuisineOptions: string[];
  loading: boolean;
  onChange: (next: PreferenceForm) => void;
  onSubmit: () => void;
};

const BUDGETS: Budget[] = ["low", "medium", "high"];

export function TasteProfileForm({
  value,
  locations,
  cuisineOptions,
  loading,
  onChange,
  onSubmit,
}: Props) {
  const toggleCuisine = (cuisine: string) => {
    const exists = value.cuisines.includes(cuisine);
    onChange({
      ...value,
      cuisines: exists
        ? value.cuisines.filter((c) => c !== cuisine)
        : [...value.cuisines, cuisine],
    });
  };

  const quickAdds = cuisineOptions
    .filter((c) => !value.cuisines.includes(c))
    .slice(0, 4);

  return (
    <form
      className="flex flex-col gap-5 rounded-2xl border border-stroke bg-surface-2 p-5 shadow-card"
      onSubmit={(event) => {
        event.preventDefault();
        onSubmit();
      }}
    >
      <div className="flex items-start justify-between gap-3">
        <div>
          <h2 className="font-display text-2xl font-bold text-ink">
            Set Your Taste Profile
          </h2>
          <p className="mt-1 text-sm text-muted">
            Facts from Zomato listings, ranking by AI
          </p>
        </div>
        <IconTune className="mt-1 h-5 w-5 text-crimson-bright" />
      </div>

      <label className="flex flex-col gap-1.5">
        <span className="flex items-center justify-between text-sm font-semibold text-ink">
          Neighborhood
          <span className="text-[11px] font-normal text-muted">
            Bangalore Central &amp; Suburbs
          </span>
        </span>
        <select
          className="w-full appearance-none rounded-lg border border-stroke bg-surface-high px-3 py-2.5 text-ink outline-none ring-crimson focus:ring-2"
          value={value.location}
          onChange={(e) => onChange({ ...value, location: e.target.value })}
          disabled={loading || locations.length === 0}
        >
          {locations.map((loc) => (
            <option key={loc} value={loc}>
              {loc}
            </option>
          ))}
        </select>
      </label>

      <div className="flex flex-col gap-1.5">
        <span className="flex items-center justify-between text-sm font-semibold text-ink">
          Budget Band
          <span className="text-[11px] font-normal text-muted">
            Avg. cost for two
          </span>
        </span>
        <div className="grid grid-cols-3 gap-1 rounded-lg bg-surface-lowest p-1">
          {BUDGETS.map((budget) => {
            const active = value.budget === budget;
            return (
              <button
                key={budget}
                type="button"
                disabled={loading}
                onClick={() => onChange({ ...value, budget })}
                className={`rounded-md py-2 text-sm font-semibold capitalize transition ${
                  active
                    ? "bg-[#B1021E] text-[#FFBDB9] shadow-md"
                    : "text-muted hover:text-ink"
                }`}
              >
                {budget}
              </button>
            );
          })}
        </div>
      </div>

      <div className="flex flex-col gap-1.5">
        <span className="flex items-center justify-between text-sm font-semibold text-ink">
          Preferred Cuisines
          <span className="text-[11px] font-bold text-crimson-soft">
            {value.cuisines.length} Active
          </span>
        </span>
        <div className="flex flex-wrap gap-2">
          {value.cuisines.map((cuisine) => (
            <button
              key={cuisine}
              type="button"
              disabled={loading}
              onClick={() => toggleCuisine(cuisine)}
              className="inline-flex items-center gap-1.5 rounded-full bg-[#B1021E]/30 px-3 py-1 text-sm font-semibold text-[#FFBDB9]"
            >
              {cuisine}
              <span aria-hidden>×</span>
            </button>
          ))}
          {value.cuisines.length === 0 && (
            <span className="text-sm text-muted">Any cuisine</span>
          )}
        </div>
        {quickAdds.length > 0 && (
          <div className="mt-1 flex flex-wrap items-center gap-2">
            <span className="text-[11px] font-bold uppercase tracking-wider text-muted">
              Quick add:
            </span>
            {quickAdds.map((cuisine) => (
              <button
                key={cuisine}
                type="button"
                disabled={loading}
                onClick={() => toggleCuisine(cuisine)}
                className="rounded bg-surface-high px-2 py-0.5 text-[11px] font-semibold text-ink transition hover:text-crimson-bright"
              >
                + {cuisine}
              </button>
            ))}
          </div>
        )}
        <select
          className="mt-1 w-full rounded-lg border border-stroke bg-surface-high px-3 py-2 text-sm text-ink outline-none ring-crimson focus:ring-2"
          value=""
          disabled={loading}
          onChange={(e) => {
            const next = e.target.value;
            if (next) toggleCuisine(next);
          }}
        >
          <option value="">Add cuisine…</option>
          {cuisineOptions
            .filter((c) => !value.cuisines.includes(c))
            .map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
        </select>
      </div>

      <label className="flex flex-col gap-2">
        <span className="flex items-center justify-between text-sm font-semibold text-ink">
          Minimum Rating
          <span className="inline-flex items-center gap-1 rounded-full bg-tertiary/20 px-2.5 py-0.5 text-sm font-bold text-tertiary">
            ★ {value.minRating.toFixed(1)}
            <span className="font-normal text-muted">/ 5.0</span>
          </span>
        </span>
        <input
          type="range"
          min={0}
          max={5}
          step={0.1}
          value={value.minRating}
          disabled={loading}
          onChange={(e) =>
            onChange({ ...value, minRating: Number(e.target.value) })
          }
          className="w-full accent-crimson-bright"
        />
        <div className="flex justify-between text-[11px] text-muted">
          <span>0.0</span>
          <span>4.0 Recommended</span>
          <span>5.0</span>
        </div>
      </label>

      <label className="flex flex-col gap-1.5">
        <span className="flex items-center justify-between text-sm font-semibold text-ink">
          Sensory &amp; Ambiance Notes
          <span className="text-[11px] font-normal text-muted">AI natural query</span>
        </span>
        <textarea
          rows={3}
          disabled={loading}
          value={value.additionalPreferences}
          onChange={(e) =>
            onChange({ ...value, additionalPreferences: e.target.value })
          }
          placeholder="quiet corner, outdoor seating, authentic pasta, date night…"
          className="resize-none rounded-lg border border-stroke bg-surface-high p-3 text-sm text-ink outline-none ring-crimson placeholder:text-muted/70 focus:ring-2"
        />
      </label>

      <div className="flex items-center justify-between rounded-lg bg-surface p-3">
        <div>
          <p className="text-sm font-semibold text-ink">Target Shortlist (Top-K)</p>
          <p className="text-[11px] text-muted">How many restaurants to return</p>
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            disabled={loading || value.topK <= 1}
            onClick={() => onChange({ ...value, topK: Math.max(1, value.topK - 1) })}
            className="grid h-8 w-8 place-items-center rounded bg-surface-high font-bold text-ink hover:bg-surface-3 disabled:opacity-40"
          >
            −
          </button>
          <span className="w-6 text-center font-display text-lg font-bold text-crimson-soft">
            {value.topK}
          </span>
          <button
            type="button"
            disabled={loading || value.topK >= 10}
            onClick={() => onChange({ ...value, topK: Math.min(10, value.topK + 1) })}
            className="grid h-8 w-8 place-items-center rounded bg-surface-high font-bold text-ink hover:bg-surface-3 disabled:opacity-40"
          >
            +
          </button>
        </div>
      </div>

      <label className="flex items-center justify-between py-1">
        <span className="text-sm text-muted">Dry-run / offline test mode</span>
        <input
          type="checkbox"
          checked={value.dryRun}
          disabled={loading}
          onChange={(e) => onChange({ ...value, dryRun: e.target.checked })}
          className="h-4 w-4 accent-crimson"
        />
      </label>

      <button
        type="submit"
        disabled={loading || !value.location}
        className="inline-flex w-full items-center justify-center gap-2 rounded-xl bg-crimson-bright px-6 py-3.5 font-display text-lg font-bold text-[#5B000E] shadow-glow transition hover:brightness-110 active:scale-[0.99] disabled:cursor-not-allowed disabled:opacity-60"
      >
        <IconSparkle className="h-5 w-5" />
        {loading ? "Ranking restaurants…" : "Find restaurants"}
      </button>
    </form>
  );
}
