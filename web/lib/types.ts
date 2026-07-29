export type Provider = "anthropic" | "gemini" | "openai";

export interface OutlineChapter {
  title: string;
  job: string;
  beats: string[];
  endsOn: string;
  wordBudget: number;
}

export interface OutlineSection {
  title: string;
  job: string;
  beats: string[];
  wordBudget: number;
}

export interface Outline {
  workingTitle: string;
  thesis: string;
  audiencePromise: string;
  coldOpenHook: string;
  openLoop: { setup: string; payoffChapter: number };
  intro: OutlineSection;
  chapters: OutlineChapter[];
  outro: OutlineSection;
  payoff: string;
  cta: string;
  thumbnailPrompt: string;
  keywords: string[];
  topic: string;
  format: string;
  targetMinutes: number;
}

export interface WrittenSection {
  key: "intro" | "chapter" | "outro";
  index: number;
  title: string;
  narration: string;
  visualPrompts: string[];
  summary: string;
  wordCount: number;
  targetWords: number;
}

export interface PlanRequest {
  topic: string;
  format: string;
  minutes: number;
  chapters?: number;
  context?: string;
  provider?: Provider;
  apiKey?: string;
}
