export type Budget = "low" | "medium" | "high";

export type PreferenceForm = {
  location: string;
  budget: Budget;
  cuisines: string[];
  minRating: number;
  additionalPreferences: string;
  topK: number;
  dryRun: boolean;
};

export type OptionsResponse = {
  locations: string[];
  cuisines: string[];
  default_location: string;
};

export type RecommendationItem = {
  rank: number;
  name: string;
  cuisine: string | null;
  rating: number | null;
  estimated_cost: string | null;
  location: string | null;
  explanation: string;
  restaurant_id?: number | null;
  budget?: string | null;
  cost_for_two?: number | null;
};

export type RecommendationMeta = {
  candidates_considered: number;
  candidates_before_cap: number;
  filters_requested: string[];
  filters_applied: string[];
  filters_relaxed: string[];
  relaxed: boolean;
  top_k: number;
  candidate_cap: number;
  budget_range: Record<string, unknown> | null;
  empty_reason: string | null;
  llm_fallback: boolean;
  llm_error: string | null;
  dry_run: boolean;
  error: string | null;
};

export type RecommendationResponse = {
  summary: string | null;
  recommendations: RecommendationItem[];
  meta: RecommendationMeta;
  preferences: Record<string, unknown> | null;
};

export type UiPhase = "idle" | "loading" | "results" | "empty" | "error";
