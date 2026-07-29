import { estimateTimestamp } from "@/lib/budgets";

export interface StripChapter {
  title: string;
  wordBudget: number;
}

/**
 * The chapter timeline. This is a real part of the planner, reused on the
 * landing page rather than mocked up, so what the page shows is what the tool
 * actually renders.
 */
export function ChapterStrip({
  chapters,
  totalWords,
  caption,
}: {
  chapters: StripChapter[];
  totalWords: number;
  caption?: string;
}) {
  let cumulative = 0;
  const rows = chapters.map((chapter) => {
    const timestamp = estimateTimestamp(cumulative);
    cumulative += chapter.wordBudget;
    const share = totalWords ? (chapter.wordBudget / totalWords) * 100 : 0;
    return { ...chapter, timestamp, share };
  });

  return (
    <div
      className="rounded-[--radius-card] border p-5 sm:p-6"
      style={{ borderColor: "var(--line)", background: "var(--surface-raised)" }}
    >
      <div className="flex items-baseline justify-between gap-4">
        <span
          className="font-mono text-xs"
          style={{ color: "var(--text-faint)" }}
        >
          chapters
        </span>
        <span
          className="font-mono text-xs tabular-nums"
          style={{ color: "var(--text-faint)" }}
        >
          {estimateTimestamp(totalWords)} total
        </span>
      </div>

      <ol className="mt-4 grid gap-2.5">
        {rows.map((row, i) => (
          <li key={`${row.title}-${i}`} className="grid gap-1.5">
            <div className="flex items-baseline gap-3">
              <span
                className="font-mono text-xs tabular-nums"
                style={{ color: "var(--accent)" }}
              >
                {row.timestamp}
              </span>
              <span className="min-w-0 flex-1 truncate text-sm">
                {row.title}
              </span>
              <span
                className="font-mono text-xs tabular-nums"
                style={{ color: "var(--text-faint)" }}
              >
                {row.wordBudget}w
              </span>
            </div>
            <div
              className="h-[3px] rounded-[--radius-chip]"
              style={{ background: "var(--surface-sunken)" }}
            >
              <div
                className="h-full rounded-[--radius-chip]"
                style={{
                  width: `${Math.max(row.share, 3)}%`,
                  background: "var(--accent)",
                  opacity: row.share > 12 ? 1 : 0.55,
                }}
              />
            </div>
          </li>
        ))}
      </ol>

      {caption ? (
        <p className="mt-5 text-xs" style={{ color: "var(--text-faint)" }}>
          {caption}
        </p>
      ) : null}
    </div>
  );
}
