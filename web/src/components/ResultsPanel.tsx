import { EmptyState } from "@/components/EmptyState";
import { RestaurantCard } from "@/components/RestaurantCard";
import type { RecommendationResponse } from "@/lib/types";

type Props = {
  response: RecommendationResponse;
};

export function ResultsPanel({ response }: Props) {
  const { meta, recommendations, summary } = response;

  if (meta.error) {
    return (
      <div className="rounded-2xl border border-crimson/40 bg-crimson/10 p-5 text-crimson-soft">
        Something went wrong while generating recommendations. Please try again.
      </div>
    );
  }

  if (recommendations.length === 0) {
    return (
      <EmptyState
        reason={meta.empty_reason || "No restaurants matched your preferences."}
      />
    );
  }

  return (
    <div className="space-y-4">
      {meta.relaxed && meta.filters_relaxed.length > 0 && (
        <div className="rounded-xl border border-rating-mid/30 bg-rating-mid/10 px-4 py-3 text-sm text-ink">
          Constraint boundary reached — relaxed:{" "}
          <strong>{meta.filters_relaxed.join(", ")}</strong>. Location was kept.
        </div>
      )}

      {meta.llm_fallback && (
        <div className="rounded-xl border border-stroke bg-surface px-4 py-3 text-sm text-muted">
          AI ranking was unavailable, so results are sorted by rating/cost.
          Restaurant facts are still from the dataset.
        </div>
      )}

      {meta.dry_run && (
        <p className="text-xs text-muted">
          Dry-run mode: mock explanations (no live LLM call).
        </p>
      )}

      <div className="flex flex-wrap gap-2">
        <span className="rounded-full border border-crimson/35 bg-crimson/15 px-3 py-1 text-xs font-semibold text-crimson-soft">
          {meta.candidates_considered} places matched
        </span>
        {meta.filters_applied.length > 0 && (
          <span className="rounded-full border border-crimson/35 bg-crimson/15 px-3 py-1 text-xs font-semibold text-crimson-soft">
            filters: {meta.filters_applied.join(", ")}
          </span>
        )}
      </div>

      {summary && (
        <div className="rounded-r-xl border border-crimson/30 border-l-[3px] border-l-crimson bg-crimson/[0.06] px-4 py-3">
          <span className="mb-1 block text-[11px] font-bold uppercase tracking-[0.1em] text-crimson-bright">
            AI executive synthesis
          </span>
          <p className="text-sm leading-relaxed text-ink">{summary}</p>
        </div>
      )}

      <h2 className="font-display text-xl font-bold text-ink">
        {recommendations.length} restaurants for you
      </h2>

      <div className="space-y-4">
        {recommendations.map((item) => (
          <RestaurantCard key={`${item.rank}-${item.name}`} item={item} />
        ))}
      </div>
    </div>
  );
}
