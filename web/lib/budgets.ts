// Port of longform/config.py — runtime target to word budget.
// Kept deliberately small and pure so it can be reasoned about on both sides.

export const WORDS_PER_MINUTE = 150;
export const MIN_TARGET_MINUTES = 3;
export const MAX_TARGET_MINUTES = 60;

export interface WordBudgets {
  intro: number;
  chapters: number[];
  outro: number;
  total: number;
}

export function wordsForMinutes(minutes: number): number {
  return Math.trunc(minutes * WORDS_PER_MINUTE);
}

/**
 * Split a runtime budget into intro / per-chapter / outro word counts.
 *
 * Intro and outro are deliberately short: the first thirty seconds decide
 * retention, and a long outro is where viewers leave.
 */
export function chapterWordBudgets(
  targetMinutes: number,
  chapterCount: number,
  introShare = 0.08,
  outroShare = 0.06,
): WordBudgets {
  const count = Math.max(1, Math.trunc(chapterCount));
  const total = wordsForMinutes(targetMinutes);

  const intro = Math.trunc(total * introShare);
  const outro = Math.trunc(total * outroShare);
  const body = Math.max(total - intro - outro, count * 50);

  const per = Math.trunc(body / count);
  const chapters = new Array(count).fill(per);
  // The remainder goes to the first chapter, the one doing the most work.
  chapters[0] += body - per * count;

  return {
    intro,
    chapters,
    outro,
    total: intro + chapters.reduce((a, b) => a + b, 0) + outro,
  };
}

/** Seconds of runtime a word count implies, formatted as M:SS. */
export function estimateTimestamp(wordsBefore: number): string {
  const seconds = Math.round((wordsBefore / WORDS_PER_MINUTE) * 60);
  const m = Math.trunc(seconds / 60);
  const s = seconds % 60;
  return `${m}:${String(s).padStart(2, "0")}`;
}

export function countWords(text: string): number {
  return text.trim() ? text.trim().split(/\s+/).length : 0;
}
