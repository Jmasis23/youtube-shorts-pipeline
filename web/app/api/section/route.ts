import { NextResponse } from "next/server";

import { countWords, WORDS_PER_MINUTE } from "@/lib/budgets";
import { getFormat } from "@/lib/formats";
import {
  asString,
  asStringList,
  callLlm,
  defaultProvider,
  LlmError,
  parseJsonResponse,
  resolveKey,
} from "@/lib/llm";
import { sectionPlan } from "@/lib/plan";
import { sectionPrompt } from "@/lib/prompts";
import type { Outline, Provider, WrittenSection } from "@/lib/types";

// One section per request. The browser walks the section list and calls this
// once each, carrying forward the summaries of what has already been written,
// which is how a 15-minute script stays coherent without one long request.
export const maxDuration = 60;
export const runtime = "nodejs";

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const outline = body.outline as Outline;
    const index = Number(body.index);

    if (!outline || !Array.isArray(outline.chapters)) {
      return NextResponse.json({ error: "An outline is required." }, { status: 400 });
    }

    const plan = sectionPlan(outline);
    if (!Number.isInteger(index) || index < 0 || index >= plan.length) {
      return NextResponse.json({ error: "Section index out of range." }, { status: 400 });
    }

    const format = getFormat(outline.format);
    const spec = plan[index];
    const previous = (body.previous ?? []) as WrittenSection[];

    const estimatedSeconds = (spec.wordBudget / WORDS_PER_MINUTE) * 60;
    const scenes = Math.max(1, Math.round(estimatedSeconds / format.sceneSeconds));

    const provider: Provider = body.provider || defaultProvider();
    const apiKey = resolveKey(provider, body.apiKey);

    const raw = await callLlm(
      sectionPrompt({ outline, format, spec, previous, scenes }),
      provider,
      apiKey,
      maxTokensFor(spec.wordBudget),
    );

    const data = parseJsonResponse<Record<string, unknown>>(raw);
    const narration = asString(data.narration);

    if (!narration) {
      throw new LlmError(
        `The model returned no narration for "${spec.title}". Try again, or switch provider.`,
      );
    }

    const section: WrittenSection = {
      key: spec.key,
      index,
      title: spec.title,
      narration,
      visualPrompts: asStringList(data.visual_prompts),
      summary: asString(data.summary) || truncateWords(narration, 40),
      wordCount: countWords(narration),
      targetWords: spec.wordBudget,
    };

    return NextResponse.json({ section, total: plan.length });
  } catch (e) {
    if (e instanceof LlmError) {
      return NextResponse.json({ error: e.message }, { status: e.status });
    }
    const message = e instanceof Error ? e.message : "Unexpected error.";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}

function maxTokensFor(wordBudget: number): number {
  return Math.max(2000, Math.trunc(wordBudget * 1.4 * 2) + 600);
}

function truncateWords(text: string, limit: number): string {
  const words = text.trim().split(/\s+/);
  if (words.length <= limit) return text.trim();
  return words.slice(0, limit).join(" ").replace(/[,;:]$/, "") + ".";
}
