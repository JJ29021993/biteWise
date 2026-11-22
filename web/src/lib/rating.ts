export function formatRating(rating: number | null | undefined): string {
  if (rating == null || Number.isNaN(Number(rating))) return "—";
  return Number(rating).toFixed(1);
}

export function ratingTier(
  rating: number | null | undefined,
): "high" | "mid" | "low" | "na" {
  if (rating == null || Number.isNaN(Number(rating))) return "na";
  const value = Number(rating);
  if (value >= 4) return "high";
  if (value >= 3) return "mid";
  if (value > 0) return "low";
  return "na";
}

export function shortCost(estimatedCost: string | null | undefined): string {
  if (!estimatedCost) return "n/a";
  const text = estimatedCost.trim();
  if (text.includes("₹")) {
    return text.split(/for/i)[0]?.trim() || text;
  }
  return text;
}

export function cuisineList(cuisine: string | null | undefined): string[] {
  if (!cuisine) return [];
  return cuisine
    .replace(/\|/g, ",")
    .split(",")
    .map((part) => part.trim())
    .filter(Boolean)
    .slice(0, 5);
}
