import type {
  OptionsResponse,
  PreferenceForm,
  RecommendationResponse,
} from "@/lib/types";

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") ||
  "http://127.0.0.1:8000";

async function parseError(res: Response): Promise<string> {
  try {
    const body = await res.json();
    const detail = body?.detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) {
      return detail
        .map((item) =>
          typeof item === "object" && item?.msg
            ? String(item.msg)
            : JSON.stringify(item),
        )
        .join("; ");
    }
    return res.statusText || "Request failed";
  } catch {
    return res.statusText || "Request failed";
  }
}

export async function fetchOptions(): Promise<OptionsResponse> {
  const res = await fetch(`${API_BASE}/api/options`, {
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(await parseError(res));
  }
  return res.json();
}

export async function fetchRecommendations(
  form: PreferenceForm,
): Promise<RecommendationResponse> {
  const cuisine =
    form.cuisines.length > 0 ? form.cuisines.join(", ") : null;
  const res = await fetch(`${API_BASE}/api/recommendations`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      location: form.location,
      budget: form.budget,
      cuisine,
      min_rating: form.minRating,
      additional_preferences: form.additionalPreferences.trim() || null,
      top_k: form.topK,
      dry_run: form.dryRun,
    }),
  });
  if (!res.ok) {
    throw new Error(await parseError(res));
  }
  return res.json();
}

export { API_BASE };
