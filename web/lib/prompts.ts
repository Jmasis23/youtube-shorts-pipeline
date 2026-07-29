import type { FormatProfile } from "./formats";
import type { WordBudgets } from "./budgets";
import type { Outline, WrittenSection } from "./types";

// Ports of the prompt builders in longform/outline.py and longform/script.py.
// The wording is kept close to the Python on purpose: the planner and the CLI
// should produce comparable output for the same topic and format.

export const FACELESS_RULES = `FACELESS CONSTRAINTS (hard requirements for every visual prompt):
- No faces, no portraits, no presenters, no talking heads.
- No identifiable real people, living or dead. If a person must be present in
  frame, they are distant, silhouetted, or cropped below the shoulders.
- No legible text, captions, signage, logos, brand marks, or UI in the image.
- No charts, graphs, or diagrams. Generated ones are wrong and unreadable.
- Prompts describe a photograph or film frame, not an illustration of a
  sentence. Evoke the idea; do not caption it.`;

export function structureContext(f: FormatProfile): string {
  const parts = [`FORMAT: ${f.displayName}`];
  if (f.description) parts.push(`FORMAT INTENT: ${f.description}`);
  if (f.tone) parts.push(`TONE: ${f.tone}`);
  if (f.narrationStyle) parts.push(`NARRATION STYLE: ${f.narrationStyle}`);
  if (f.perspective) parts.push(`PERSPECTIVE: ${f.perspective}`);

  const arcKeys = ["intro", "early", "middle", "late", "outro"];
  const arcLines = arcKeys
    .filter((k) => f.arc[k])
    .map((k) => `  ${k}: ${f.arc[k]}`);
  if (arcLines.length) {
    parts.push("CHAPTER ARC (each chapter must do its job):", ...arcLines);
  }

  if (f.openLoop || f.retentionRules.length) {
    parts.push("RETENTION MECHANICS:");
    if (f.openLoop) parts.push(`  Open loop: ${f.openLoop}`);
    f.retentionRules.forEach((r) => parts.push(`  - ${r}`));
  }

  if (f.hooks.length) {
    parts.push("COLD-OPEN HOOK PATTERNS (pick the best fit for this topic):");
    f.hooks.forEach((h) =>
      parts.push(`  "${h.template}"${h.when ? ` (use when: ${h.when})` : ""}`),
    );
  }

  if (f.cta) parts.push(`CALL TO ACTION: ${f.cta}`);
  if (f.forbiddenPhrases.length) {
    parts.push(`NEVER USE THESE PHRASES: ${f.forbiddenPhrases.join(", ")}`);
  }

  return parts.join("\n");
}

export function visualGuidance(f: FormatProfile): string {
  const parts = ["VISUAL DIRECTION:"];
  if (f.visualStyle) parts.push(`  Style: ${f.visualStyle}`);
  if (f.visualMood) parts.push(`  Mood: ${f.visualMood}`);
  if (f.subjectsPrefer.length) {
    parts.push(`  Prefer: ${f.subjectsPrefer.slice(0, 8).join(", ")}`);
  }
  if (f.subjectsAvoid.length) {
    parts.push(`  Avoid: ${f.subjectsAvoid.slice(0, 8).join(", ")}`);
  }
  if (f.promptSuffix) {
    parts.push(`  Every prompt is automatically suffixed with: ${f.promptSuffix}`);
  }
  return parts.join("\n");
}

export function outlinePrompt(args: {
  topic: string;
  format: FormatProfile;
  minutes: number;
  chapters: number;
  budgets: WordBudgets;
  context: string;
}): string {
  const { topic, format, minutes, chapters, budgets, context } = args;
  const channelNote = context ? `\nCHANNEL CONTEXT: ${context}` : "";

  return `You are planning a ${minutes.toFixed(0)}-minute faceless YouTube video: narration over b-roll, with no presenter on camera and no host persona.${channelNote}

${structureContext(format)}

TOPIC: ${topic}

Plan ${chapters} body chapters plus an intro and an outro. Word budgets are fixed by the runtime target and are not negotiable:
- intro: ${budgets.intro} words
- each body chapter: ${budgets.chapters.join(", ")} words respectively
- outro: ${budgets.outro} words

Requirements:
- Every chapter needs a distinct JOB. If two chapters could be swapped without loss, the plan is wrong. Redo them.
- The \`beats\` for a chapter are the specific things that chapter must cover, in order. Three to five beats each, concrete, not topic labels.
- The open loop opened in the intro must be paid off in a named chapter, and that chapter must know it is the payoff.
- \`title\` is the on-screen chapter name in the YouTube description. Short, concrete, no numbering.
- Because this is faceless, never plan a beat that requires showing a person's face, a presenter, or an on-camera demonstration.
- You have no live research available. Stay on ground you are confident about, prefer well-established facts, and do not invent specific statistics, dates, or quotations. Where a precise figure would strengthen a beat but you are unsure of it, describe the kind of evidence needed instead of fabricating a number.

Output JSON exactly, with no prose around it:
{
  "working_title": "...",
  "thesis": "one sentence stating what this video argues or explains",
  "audience_promise": "what the viewer can do or explain by the end",
  "cold_open_hook": "the first 2-3 sentences of narration, written out in full",
  "open_loop": {"setup": "what the intro teases", "payoff_chapter": 3},
  "intro": {"title": "Intro", "job": "...", "beats": ["...", "..."]},
  "chapters": [
    {"title": "...", "job": "what this chapter must accomplish",
     "beats": ["...", "...", "..."],
     "ends_on": "the unresolved beat that forces the next chapter"}
  ],
  "outro": {"title": "Outro", "job": "...", "beats": ["...", "..."]},
  "payoff": "the single sentence the whole video builds to",
  "cta": "the closing call to action, written out",
  "thumbnail_prompt": "image description for a 16:9 thumbnail, no text in the image",
  "keywords": ["...", "..."]
}`;
}

export function sectionPrompt(args: {
  outline: Outline;
  format: FormatProfile;
  spec: {
    key: "intro" | "chapter" | "outro";
    title: string;
    job: string;
    beats: string[];
    endsOn: string;
    wordBudget: number;
    isPayoff: boolean;
  };
  previous: WrittenSection[];
  scenes: number;
}): string {
  const { outline, format, spec, previous, scenes } = args;

  const storySoFar = previous.length
    ? previous.map((p, i) => `  ${i + 1}. ${p.title}: ${p.summary}`).join("\n")
    : "  (nothing yet, this is the opening of the video)";

  const beats = spec.beats.length
    ? spec.beats.map((b) => `  - ${b}`).join("\n")
    : "  (use your judgement)";

  const roleNote = {
    intro:
      "This is the cold open. It must work for someone who arrived from a thumbnail and knows nothing. Do not introduce yourself or the channel. Open the loop described below and do not resolve it.",
    chapter:
      "This is a body chapter. Move the video forward. Never recap what earlier sections already established.",
    outro:
      "This is the close. Land the payoff, then the call to action. Do not introduce new material.",
  }[spec.key];

  const payoffNote = spec.isPayoff
    ? `\nTHIS CHAPTER PAYS OFF THE OPEN LOOP: "${outline.openLoop.setup}"\nResolve it explicitly and satisfyingly inside this chapter.`
    : "";

  const endsOn = spec.endsOn ? `\nEND THIS SECTION ON: ${spec.endsOn}` : "";

  const hookNote =
    spec.key === "intro" && outline.coldOpenHook
      ? `\nUSE THIS AS THE OPENING LINES (polish the wording, keep the substance): ${outline.coldOpenHook}`
      : "";

  const ctaNote =
    spec.key === "outro" && outline.cta
      ? `\nCLOSE WITH THIS CALL TO ACTION: ${outline.cta}`
      : "";

  const styleParts = [`FORMAT: ${format.displayName}`];
  if (format.tone) styleParts.push(`TONE: ${format.tone}`);
  if (format.narrationStyle) {
    styleParts.push(`NARRATION STYLE: ${format.narrationStyle}`);
  }
  if (format.perspective) styleParts.push(`PERSPECTIVE: ${format.perspective}`);
  if (format.retentionRules.length) {
    styleParts.push("WRITING RULES:");
    format.retentionRules.forEach((r) => styleParts.push(`  - ${r}`));
  }
  if (format.forbiddenPhrases.length) {
    styleParts.push(
      `NEVER USE THESE PHRASES: ${format.forbiddenPhrases.join(", ")}`,
    );
  }

  const budget = spec.wordBudget;

  return `You are writing one section of narration for a faceless long-form YouTube video.

${styleParts.join("\n")}

VIDEO THESIS: ${outline.thesis}
PROMISE TO THE VIEWER: ${outline.audiencePromise}
THE VIDEO BUILDS TO: ${outline.payoff}
OPEN LOOP: ${outline.openLoop.setup}

STORY SO FAR (already written, do not repeat any of it):
${storySoFar}

NOW WRITE: "${spec.title}"
${roleNote}${payoffNote}
THIS SECTION'S JOB: ${spec.job}
BEATS TO COVER, IN ORDER:
${beats}${endsOn}${hookNote}${ctaNote}

LENGTH: ${budget} words. Between ${Math.trunc(budget * 0.9)} and ${Math.trunc(budget * 1.1)} is acceptable; outside that range is a failure. This is narration read aloud. No headings, no bullet points, no stage directions, no speaker labels, no emoji.

You have no live research available. Do not invent statistics, dates, or quotations. Prefer well-established material you are confident about.

Also write exactly ${scenes} visual prompts, one per b-roll shot, in the order they appear under this section's narration. They must track what is being said at that point.

${visualGuidance(format)}

${FACELESS_RULES}

Output JSON exactly, with no prose around it:
{
  "narration": "the spoken narration for this section, as continuous prose",
  "visual_prompts": ["...", "..."],
  "summary": "one sentence describing what this section established, for the next section's context"
}`;
}
