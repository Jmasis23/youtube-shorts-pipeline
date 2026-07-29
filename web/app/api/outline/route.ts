import { NextResponse } from "next/server";

import { chapterWordBudgets, MAX_TARGET_MINUTES, MIN_TARGET_MINUTES } from "@/lib/budgets";
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
import { outlinePrompt } from "@/lib/prompts";
import type { Outline, Provider } from "@/lib/types";

// One LLM call per request is the whole point of this design: the CLI writes a
// 15-minute script in a dozen calls, and a dozen calls in one request would
// blow any serverless timeout. The browser drives the loop instead.
export const maxDuration = 60;
export const runtime = "nodejs";

export async function POST(request: Request) {
  try {
    const body = await request.json();

    const topic = asString(body.topic);
    if (!topic) {
      return NextResponse.json({ error: "A topic is required." }, { status: 400 });
    }

    const format = getFormat(asString(body.format) || "explainer");
    const minutes = clamp(
      Number(body.minutes) || format.targetMinutes,
      MIN_TARGET_MINUTES,
      MAX_TARGET_MINUTES,
    );
    const chapters = clamp(Number(body.chapters) || format.chapters, 1, 20);
    const provider: Provider = body.provider || defaultProvider();
    const apiKey = resolveKey(provider, body.apiKey);

    const budgets = chapterWordBudgets(minutes, chapters);

    const raw = await callLlm(
      outlinePrompt({
        topic,
        format,
        minutes,
        chapters,
        budgets,
        context: asString(body.context),
      }),
      provider,
      apiKey,
      4000,
    );

    const data = parseJsonResponse<Record<string, unknown>>(raw);
    const outline = normalise(data, budgets, chapters, {
      topic,
      format: format.name,
      targetMinutes: minutes,
    });

    return NextResponse.json({ outline, budgets });
  } catch (e) {
    return errorResponse(e);
  }
}

function clamp(value: number, min: number, max: number): number {
  if (!Number.isFinite(value)) return min;
  return Math.min(max, Math.max(min, value));
}

/**
 * Coerce the model's outline into the shape the planner expects.
 * Same forgiveness as longform/outline.py: models return the right content in
 * slightly the wrong shape often enough that failing the request is worse than
 * repairing it, and the word budgets stay authoritative either way.
 */
function normalise(
  data: Record<string, unknown>,
  budgets: ReturnType<typeof chapterWordBudgets>,
  expectedChapters: number,
  meta: { topic: string; format: string; targetMinutes: number },
): Outline {
  const rawChapters = Array.isArray(data.chapters) ? data.chapters : [];
  const chapters = rawChapters.slice(0, expectedChapters).map((c) => {
    const chapter = (typeof c === "object" && c !== null ? c : {}) as Record<string, unknown>;
    return {
      title: asString(chapter.title) || "Chapter",
      job: asString(chapter.job),
      beats: asStringList(chapter.beats, 6),
      endsOn: asString(chapter.ends_on),
      wordBudget: 0,
    };
  });

  while (chapters.length < expectedChapters) {
    chapters.push({
      title: `Chapter ${chapters.length + 1}`,
      job: "Continue developing the thesis with new material.",
      beats: [],
      endsOn: "",
      wordBudget: 0,
    });
  }
  chapters.forEach((c, i) => {
    c.wordBudget = budgets.chapters[i] ?? budgets.chapters[0];
  });

  const rawLoop = (typeof data.open_loop === "object" && data.open_loop !== null
    ? data.open_loop
    : {}) as Record<string, unknown>;
  let payoffChapter = Number(rawLoop.payoff_chapter);
  if (!Number.isFinite(payoffChapter)) payoffChapter = 0;
  payoffChapter = Math.max(0, Math.min(Math.trunc(payoffChapter), chapters.length));

  const section = (key: string, fallbackTitle: string, wordBudget: number) => {
    const raw = (typeof data[key] === "object" && data[key] !== null
      ? data[key]
      : {}) as Record<string, unknown>;
    return {
      title: asString(raw.title) || fallbackTitle,
      job: asString(raw.job),
      beats: asStringList(raw.beats, 6),
      wordBudget,
    };
  };

  return {
    workingTitle: asString(data.working_title) || "Untitled",
    thesis: asString(data.thesis),
    audiencePromise: asString(data.audience_promise),
    coldOpenHook: asString(data.cold_open_hook),
    openLoop: { setup: asString(rawLoop.setup), payoffChapter },
    intro: section("intro", "Intro", budgets.intro),
    chapters,
    outro: section("outro", "Outro", budgets.outro),
    payoff: asString(data.payoff),
    cta: asString(data.cta),
    thumbnailPrompt: asString(data.thumbnail_prompt),
    keywords: asStringList(data.keywords, 15),
    ...meta,
  };
}

function errorResponse(e: unknown) {
  if (e instanceof LlmError) {
    return NextResponse.json({ error: e.message }, { status: e.status });
  }
  const message = e instanceof Error ? e.message : "Unexpected error.";
  return NextResponse.json({ error: message }, { status: 500 });
}
