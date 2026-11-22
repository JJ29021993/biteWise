"use client";

import { useCallback, useEffect, useState } from "react";

import { EmptyState } from "@/components/EmptyState";
import { Hero } from "@/components/Hero";
import { IdlePanel } from "@/components/IdlePanel";
import { LoadingState } from "@/components/LoadingState";
import { ResultsPanel } from "@/components/ResultsPanel";
import { SiteFooter } from "@/components/SiteFooter";
import { TasteProfileForm } from "@/components/TasteProfileForm";
import { TopBar } from "@/components/TopBar";
import { fetchOptions, fetchRecommendations } from "@/lib/api";
import type {
  PreferenceForm,
  RecommendationResponse,
  UiPhase,
} from "@/lib/types";

const INITIAL_FORM: PreferenceForm = {
  location: "Indiranagar",
  budget: "medium",
  cuisines: [],
  minRating: 4.0,
  additionalPreferences: "",
  topK: 5,
  dryRun: true,
};

export function DiscoverApp() {
  const [form, setForm] = useState<PreferenceForm>(INITIAL_FORM);
  const [locations, setLocations] = useState<string[]>([]);
  const [cuisineOptions, setCuisineOptions] = useState<string[]>([]);
  const [optionsError, setOptionsError] = useState<string | null>(null);
  const [phase, setPhase] = useState<UiPhase>("idle");
  const [response, setResponse] = useState<RecommendationResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const options = await fetchOptions();
        if (cancelled) return;
        setLocations(options.locations);
        setCuisineOptions(options.cuisines);
        setForm((prev) => ({
          ...prev,
          location: options.default_location || prev.location,
        }));
        setOptionsError(null);
      } catch (err) {
        if (cancelled) return;
        setOptionsError(
          err instanceof Error
            ? err.message
            : "Could not load filter options from the API.",
        );
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const runSearch = useCallback(async () => {
    if (!form.location.trim()) {
      setError("Location is required.");
      setPhase("error");
      return;
    }
    setError(null);
    setPhase("loading");
    try {
      const result = await fetchRecommendations(form);
      setResponse(result);
      if (result.meta.error) {
        setPhase("error");
        setError(
          "Something went wrong while generating recommendations. Please try again.",
        );
        return;
      }
      setPhase(result.recommendations.length === 0 ? "empty" : "results");
    } catch (err) {
      setResponse(null);
      setPhase("error");
      setError(
        err instanceof Error
          ? err.message
          : "Unexpected error while recommending.",
      );
    }
  }, [form]);

  const applyPreset = (label: string) => {
    const next = { ...form };
    if (label.toLowerCase().includes("indiranagar")) {
      next.location = locations.find((l) =>
        l.toLowerCase().includes("indiranagar"),
      ) || next.location;
      if (!next.cuisines.includes("Cafe")) {
        const cafe = cuisineOptions.find((c) => c.toLowerCase() === "cafe");
        if (cafe) next.cuisines = [...next.cuisines, cafe];
      }
      next.additionalPreferences = "quiet ambience, good coffee";
    } else if (label.toLowerCase().includes("sushi")) {
      next.budget = "medium";
      next.additionalPreferences = "best sushi under 1500";
      const japanese = cuisineOptions.find((c) =>
        c.toLowerCase().includes("japanese"),
      );
      if (japanese && !next.cuisines.includes(japanese)) {
        next.cuisines = [...next.cuisines, japanese];
      }
    } else if (label.toLowerCase().includes("cunningham")) {
      next.location =
        locations.find((l) => l.toLowerCase().includes("cunningham")) ||
        next.location;
      next.additionalPreferences = "romantic evening, intimate setting";
    }
    setForm(next);
  };

  return (
    <div className="relative min-h-screen bg-canvas text-ink">
      <div
        className="pointer-events-none fixed inset-x-0 top-0 h-[480px] bg-[radial-gradient(ellipse_80%_60%_at_50%_-10%,rgba(226,55,68,0.12),transparent_75%)]"
        aria-hidden
      />
      <TopBar />
      <main className="relative z-10 mx-auto max-w-shell px-4 py-8 sm:px-6">
        <Hero />

        {optionsError && (
          <div className="mb-6 rounded-xl border border-crimson/40 bg-crimson/10 px-4 py-3 text-sm text-crimson-soft">
            {optionsError} — start the API with{" "}
            <code className="rounded bg-surface px-1.5 py-0.5 text-ink">
              python -m src.api
            </code>{" "}
            and ensure processed data exists.
          </div>
        )}

        <div className="grid grid-cols-1 items-start gap-7 lg:grid-cols-12">
          <div className="lg:col-span-5">
            <TasteProfileForm
              value={form}
              locations={locations}
              cuisineOptions={cuisineOptions}
              loading={phase === "loading"}
              onChange={setForm}
              onSubmit={runSearch}
            />
          </div>

          <div className="lg:col-span-7">
            <div className="mb-4">
              <h2 className="font-display text-xl font-bold text-ink">
                Recommendations
              </h2>
              <p className="text-sm text-muted">
                AI-ranked shortlist with grounded explanations
              </p>
            </div>

            {phase === "idle" && <IdlePanel onPreset={applyPreset} />}
            {phase === "loading" && <LoadingState />}
            {phase === "empty" && response && (
              <EmptyState
                reason={
                  response.meta.empty_reason ||
                  "No restaurants matched your preferences."
                }
              />
            )}
            {phase === "results" && response && (
              <ResultsPanel response={response} />
            )}
            {phase === "error" && (
              <div className="rounded-2xl border border-crimson/40 bg-crimson/10 p-5 text-crimson-soft">
                {error || "Something went wrong. Please try again."}
              </div>
            )}
          </div>
        </div>

        <SiteFooter />
      </main>
    </div>
  );
}
