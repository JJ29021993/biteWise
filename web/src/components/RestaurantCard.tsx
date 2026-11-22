import { IconSparkle, IconStar } from "@/components/icons";
import {
  cuisineList,
  formatRating,
  ratingTier,
  shortCost,
} from "@/lib/rating";
import type { RecommendationItem } from "@/lib/types";

const TIER_CLASS = {
  high: "border-rating-high/30 bg-rating-high/15 text-rating-high",
  mid: "border-rating-mid/30 bg-rating-mid/15 text-rating-mid",
  low: "border-rating-low/30 bg-rating-low/15 text-rating-low",
  na: "border-muted/30 bg-muted/10 text-muted",
} as const;

type Props = {
  item: RecommendationItem;
};

export function RestaurantCard({ item }: Props) {
  const tier = ratingTier(item.rating);
  const chips = cuisineList(item.cuisine);
  const pickLabel = item.rank === 1 ? `#${item.rank} Pick` : `#${item.rank}`;

  return (
    <article className="animate-fadeUp overflow-hidden rounded-2xl border border-stroke bg-surface-2 shadow-card transition duration-200 hover:-translate-y-0.5 hover:border-stroke-hot">
      <div className="border-b border-stroke bg-[linear-gradient(135deg,rgba(226,55,68,0.18)_0%,transparent_55%),linear-gradient(180deg,#292A2D_0%,#1B1B1F_100%)] px-4 py-3.5 sm:px-5">
        <div className="flex items-center justify-between gap-3">
          <span className="rounded-full bg-crimson-bright px-3 py-1 text-xs font-bold text-[#5B000E] shadow-glow">
            {pickLabel}
          </span>
          <span
            className={`inline-flex items-center gap-1 rounded-full border px-2.5 py-1 text-sm font-bold ${TIER_CLASS[tier]}`}
          >
            {tier !== "na" && <IconStar className="h-3.5 w-3.5" />}
            {formatRating(item.rating)}
          </span>
        </div>
        <p className="mt-3 text-xs font-semibold text-ink/85">
          {item.location || "Bangalore"}
          <span className="mx-1.5 opacity-60">·</span>
          {item.estimated_cost || "Cost n/a"}
        </p>
      </div>

      <div className="space-y-3 p-4 sm:p-5">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <span className="font-display text-sm font-bold text-crimson-bright">
                #{item.rank}
              </span>
              <h3 className="truncate font-display text-xl font-bold tracking-tight text-ink sm:text-2xl">
                {item.name}
              </h3>
            </div>
            <p className="mt-1 text-sm text-muted">
              {item.cuisine || "All cuisines"}
              <span className="mx-1.5">·</span>
              {item.location || "Bangalore"}
            </p>
          </div>
          <div className="shrink-0 text-right">
            <span className="block text-[10px] font-bold uppercase tracking-wider text-muted">
              Est. Cost
            </span>
            <span className="font-display text-base font-bold text-crimson-bright">
              {shortCost(item.estimated_cost)}
            </span>
          </div>
        </div>

        {chips.length > 0 && (
          <div className="flex flex-wrap gap-1.5">
            {chips.map((chip) => (
              <span
                key={chip}
                className="rounded-md bg-surface-high px-2 py-0.5 text-[11px] font-semibold text-ink"
              >
                {chip}
              </span>
            ))}
          </div>
        )}

        <div className="flex items-start gap-2 rounded-xl border-l-[3px] border-crimson bg-crimson/10 px-3 py-2.5">
          <IconSparkle className="mt-0.5 h-4 w-4 shrink-0 text-crimson-bright" />
          <p className="text-sm leading-relaxed text-ink">{item.explanation}</p>
        </div>
      </div>
    </article>
  );
}
