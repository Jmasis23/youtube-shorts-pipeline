import type { Outline } from "./types";

export interface SectionSpec {
  key: "intro" | "chapter" | "outro";
  title: string;
  job: string;
  beats: string[];
  endsOn: string;
  wordBudget: number;
  isPayoff: boolean;
}

/**
 * Flatten an outline into the ordered list of sections to write.
 * Port of `_section_plan` in longform/script.py.
 */
export function sectionPlan(outline: Outline): SectionSpec[] {
  const plan: SectionSpec[] = [
    {
      key: "intro",
      title: outline.intro?.title || "Intro",
      job: outline.intro?.job ?? "",
      beats: outline.intro?.beats ?? [],
      endsOn: "",
      wordBudget: outline.intro?.wordBudget ?? 120,
      isPayoff: false,
    },
  ];

  outline.chapters.forEach((chapter, i) => {
    plan.push({
      key: "chapter",
      title: chapter.title || `Chapter ${i + 1}`,
      job: chapter.job ?? "",
      beats: chapter.beats ?? [],
      endsOn: chapter.endsOn ?? "",
      wordBudget: chapter.wordBudget ?? 350,
      isPayoff: i + 1 === outline.openLoop?.payoffChapter,
    });
  });

  plan.push({
    key: "outro",
    title: outline.outro?.title || "Outro",
    job: outline.outro?.job ?? "",
    beats: outline.outro?.beats ?? [],
    endsOn: "",
    wordBudget: outline.outro?.wordBudget ?? 100,
    isPayoff: false,
  });

  return plan;
}
