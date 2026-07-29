"use client";

import { useCallback, useMemo, useRef, useState } from "react";
import {
  ArrowClockwise,
  DownloadSimple,
  Key,
  Warning,
} from "@phosphor-icons/react";

import { countWords, MAX_TARGET_MINUTES, MIN_TARGET_MINUTES } from "@/lib/budgets";
import { FORMATS, getFormat } from "@/lib/formats";
import type { Outline, Provider, WrittenSection } from "@/lib/types";
import { ChapterStrip } from "./chapter-strip";

type Phase = "idle" | "outlining" | "writing" | "done" | "error";

const PROVIDERS: { value: Provider; label: string }[] = [
  { value: "anthropic", label: "Claude" },
  { value: "gemini", label: "Gemini" },
  { value: "openai", label: "GPT" },
];

export function Planner({ serverKeyAvailable }: { serverKeyAvailable: boolean }) {
  const [topic, setTopic] = useState("");
  const [formatName, setFormatName] = useState("documentary");
  const [minutes, setMinutes] = useState(14);
  const [context, setContext] = useState("");
  const [provider, setProvider] = useState<Provider>("anthropic");
  const [apiKey, setApiKey] = useState("");

  const [phase, setPhase] = useState<Phase>("idle");
  const [outline, setOutline] = useState<Outline | null>(null);
  const [sections, setSections] = useState<WrittenSection[]>([]);
  const [progress, setProgress] = useState({ done: 0, total: 0 });
  const [error, setError] = useState("");

  const cancelled = useRef(false);
  const format = getFormat(formatName);
  const busy = phase === "outlining" || phase === "writing";

  const totalWords = useMemo(
    () => sections.reduce((sum, s) => sum + s.wordCount, 0),
    [sections],
  );

  const onFormatChange = useCallback((name: string) => {
    setFormatName(name);
    setMinutes(getFormat(name).targetMinutes);
  }, []);

  async function post(path: string, payload: Record<string, unknown>) {
    const r = await fetch(path, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        ...payload,
        provider,
        apiKey: apiKey.trim() || undefined,
      }),
    });
    const data = await r.json();
    if (!r.ok) throw new Error(data?.error ?? `Request failed (${r.status})`);
    return data;
  }

  async function run() {
    cancelled.current = false;
    setError("");
    setSections([]);
    setOutline(null);
    setProgress({ done: 0, total: 0 });
    setPhase("outlining");

    try {
      const { outline: plan } = (await post("/api/outline", {
        topic: topic.trim(),
        format: formatName,
        minutes,
        chapters: format.chapters,
        context: context.trim(),
      })) as { outline: Outline };

      if (cancelled.current) return;
      setOutline(plan);

      const total = plan.chapters.length + 2;
      setProgress({ done: 0, total });
      setPhase("writing");

      // The loop lives here, in the browser. Each iteration is one short
      // request, so no single function invocation can time out, and a failure
      // on section six does not throw away sections one to five.
      const written: WrittenSection[] = [];
      for (let index = 0; index < total; index += 1) {
        if (cancelled.current) return;

        const { section } = (await post("/api/section", {
          outline: plan,
          index,
          previous: written.map((s) => ({ title: s.title, summary: s.summary })),
        })) as { section: WrittenSection };

        written.push(section);
        setSections([...written]);
        setProgress({ done: index + 1, total });
      }

      setPhase("done");
    } catch (e) {
      if (cancelled.current) return;
      setError(e instanceof Error ? e.message : "Something went wrong.");
      setPhase("error");
    }
  }

  function stop() {
    cancelled.current = true;
    setPhase(sections.length ? "done" : "idle");
  }

  function download() {
    if (!outline) return;
    const body = [
      `# ${outline.workingTitle}`,
      "",
      `<!-- topic: ${outline.topic} -->`,
      `<!-- format: ${outline.format} | target: ${outline.targetMinutes} min -->`,
      `<!-- thesis: ${outline.thesis} -->`,
      "",
      ...sections.flatMap((s) => [`## ${s.title}`, "", s.narration, ""]),
    ].join("\n");

    const url = URL.createObjectURL(
      new Blob([body], { type: "text/markdown;charset=utf-8" }),
    );
    const a = document.createElement("a");
    a.href = url;
    a.download = `${slug(outline.workingTitle)}.md`;
    a.click();
    URL.revokeObjectURL(url);
  }

  const strip = outline
    ? [
        { title: outline.intro.title, wordBudget: outline.intro.wordBudget },
        ...outline.chapters.map((c) => ({
          title: c.title,
          wordBudget: c.wordBudget,
        })),
        { title: outline.outro.title, wordBudget: outline.outro.wordBudget },
      ]
    : [];

  return (
    <div className="grid gap-10 lg:grid-cols-[360px_1fr] lg:gap-12">
      {/* ── controls ─────────────────────────────── */}
      <form
        className="grid h-fit gap-5 lg:sticky lg:top-24"
        onSubmit={(e) => {
          e.preventDefault();
          if (!busy && topic.trim()) run();
        }}
      >
        <Field label="Topic" htmlFor="topic">
          <textarea
            id="topic"
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            rows={3}
            required
            placeholder="How container shipping actually works"
            className="w-full resize-y rounded-[--radius-card] border px-3.5 py-2.5 text-sm outline-none"
            style={inputStyle}
          />
        </Field>

        <Field label="Format" htmlFor="format">
          <select
            id="format"
            value={formatName}
            onChange={(e) => onFormatChange(e.target.value)}
            className="w-full rounded-[--radius-card] border px-3.5 py-2.5 text-sm outline-none"
            style={inputStyle}
          >
            {FORMATS.map((f) => (
              <option key={f.name} value={f.name}>
                {f.displayName}
              </option>
            ))}
          </select>
          <p className="mt-2 text-xs leading-relaxed" style={{ color: "var(--text-faint)" }}>
            {format.description}
          </p>
        </Field>

        <Field label={`Runtime: ${minutes} minutes`} htmlFor="minutes">
          <input
            id="minutes"
            type="range"
            min={MIN_TARGET_MINUTES}
            max={Math.min(MAX_TARGET_MINUTES, 30)}
            value={minutes}
            onChange={(e) => setMinutes(Number(e.target.value))}
            className="w-full accent-[var(--accent)]"
          />
          <p className="mt-1 text-xs" style={{ color: "var(--text-faint)" }}>
            About {minutes * 150} words across {format.chapters + 2} sections.
          </p>
        </Field>

        <Field label="Channel context (optional)" htmlFor="context">
          <input
            id="context"
            value={context}
            onChange={(e) => setContext(e.target.value)}
            placeholder="Who watches, and what they already know"
            className="w-full rounded-[--radius-card] border px-3.5 py-2.5 text-sm outline-none"
            style={inputStyle}
          />
        </Field>

        <Field label="Model" htmlFor="provider">
          <div className="flex gap-2">
            {PROVIDERS.map((p) => (
              <button
                key={p.value}
                type="button"
                onClick={() => setProvider(p.value)}
                className="flex-1 rounded-[--radius-card] border px-3 py-2 text-sm transition-transform active:translate-y-px"
                style={
                  provider === p.value
                    ? {
                        borderColor: "var(--accent)",
                        background: "var(--accent)",
                        color: "var(--accent-contrast)",
                      }
                    : { borderColor: "var(--line)", color: "var(--text-muted)" }
                }
              >
                {p.label}
              </button>
            ))}
          </div>
        </Field>

        <Field
          label={serverKeyAvailable ? "Your API key (optional)" : "Your API key"}
          htmlFor="apiKey"
        >
          <div className="relative">
            <Key
              size={15}
              className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2"
              style={{ color: "var(--text-faint)" }}
            />
            <input
              id="apiKey"
              type="password"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              autoComplete="off"
              required={!serverKeyAvailable}
              placeholder={serverKeyAvailable ? "Leave blank to use the site key" : "sk-..."}
              className="w-full rounded-[--radius-card] border py-2.5 pl-9 pr-3.5 text-sm outline-none"
              style={inputStyle}
            />
          </div>
          <p className="mt-2 text-xs leading-relaxed" style={{ color: "var(--text-faint)" }}>
            Sent with each request and never stored. It stays in this tab.
          </p>
        </Field>

        {busy ? (
          <button
            type="button"
            onClick={stop}
            className="rounded-[--radius-card] border px-5 py-3 text-sm font-medium"
            style={{ borderColor: "var(--line)", color: "var(--text)" }}
          >
            Stop after this section
          </button>
        ) : (
          <button
            type="submit"
            disabled={!topic.trim()}
            className="rounded-[--radius-card] px-5 py-3 text-sm font-medium transition-transform active:translate-y-px disabled:cursor-not-allowed disabled:opacity-40"
            style={{ background: "var(--accent)", color: "var(--accent-contrast)" }}
          >
            {sections.length ? "Write it again" : "Write the script"}
          </button>
        )}
      </form>

      {/* ── output ───────────────────────────────── */}
      <div className="min-w-0">
        {phase === "idle" && !sections.length ? <EmptyState /> : null}

        {error ? (
          <div
            className="mb-8 flex gap-3 rounded-[--radius-card] border p-4"
            style={{ borderColor: "var(--accent)", background: "var(--surface-raised)" }}
          >
            <Warning size={18} style={{ color: "var(--accent)" }} className="mt-0.5 shrink-0" />
            <div>
              <p className="text-sm font-medium">Could not finish</p>
              <p className="mt-1 text-sm" style={{ color: "var(--text-muted)" }}>
                {error}
              </p>
              {sections.length ? (
                <p className="mt-2 text-sm" style={{ color: "var(--text-muted)" }}>
                  The {sections.length} section
                  {sections.length === 1 ? "" : "s"} already written are below and
                  can still be downloaded.
                </p>
              ) : null}
            </div>
          </div>
        ) : null}

        {phase === "outlining" ? (
          <OutlineSkeleton />
        ) : outline ? (
          <div className="grid gap-8">
            <header>
              <h2 className="text-2xl font-semibold tracking-tight">
                {outline.workingTitle}
              </h2>
              <p className="mt-2 text-sm leading-relaxed" style={{ color: "var(--text-muted)" }}>
                {outline.thesis}
              </p>
            </header>

            <ChapterStrip
              chapters={strip}
              totalWords={
                strip.reduce((sum, c) => sum + c.wordBudget, 0) || 1
              }
              caption={
                outline.openLoop.setup
                  ? `Open loop: ${outline.openLoop.setup}`
                  : undefined
              }
            />

            {busy || sections.length ? (
              <div className="flex items-center justify-between gap-4">
                <span
                  className={`font-mono text-xs ${phase === "writing" ? "working" : ""}`}
                  style={{ color: "var(--text-faint)" }}
                >
                  {phase === "writing"
                    ? `writing ${progress.done + 1} of ${progress.total}`
                    : `${sections.length} sections, ${totalWords} words`}
                </span>
                {sections.length ? (
                  <button
                    type="button"
                    onClick={download}
                    className="inline-flex items-center gap-2 rounded-[--radius-card] border px-3.5 py-2 text-sm transition-transform active:translate-y-px"
                    style={{ borderColor: "var(--line)", color: "var(--text)" }}
                  >
                    <DownloadSimple size={15} />
                    Download script.md
                  </button>
                ) : null}
              </div>
            ) : null}

            {sections.map((section) => (
              <SectionCard key={section.index} section={section} />
            ))}

            {phase === "writing" ? <SectionSkeleton /> : null}

            {phase === "done" && sections.length ? (
              <NextStep topic={outline.topic} format={outline.format} />
            ) : null}
          </div>
        ) : null}
      </div>
    </div>
  );
}

const inputStyle = {
  borderColor: "var(--line)",
  background: "var(--surface-raised)",
  color: "var(--text)",
} as const;

function Field({
  label,
  htmlFor,
  children,
}: {
  label: string;
  htmlFor: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <label htmlFor={htmlFor} className="mb-2 block text-sm font-medium">
        {label}
      </label>
      {children}
    </div>
  );
}

function SectionCard({ section }: { section: WrittenSection }) {
  const drift = section.wordCount - section.targetWords;
  const onTarget = Math.abs(drift) <= section.targetWords * 0.15;

  return (
    <article
      className="rise rounded-[--radius-card] border p-6"
      style={{ borderColor: "var(--line)", background: "var(--surface-raised)" }}
    >
      <div className="flex flex-wrap items-baseline justify-between gap-3">
        <h3 className="text-base font-semibold tracking-tight">{section.title}</h3>
        <span
          className="font-mono text-xs tabular-nums"
          style={{ color: onTarget ? "var(--text-faint)" : "var(--accent)" }}
        >
          {section.wordCount}w of {section.targetWords}
        </span>
      </div>

      <p className="mt-4 whitespace-pre-wrap text-[15px] leading-[1.75]">
        {section.narration}
      </p>

      {section.visualPrompts.length ? (
        <details className="mt-5 border-t pt-4" style={{ borderColor: "var(--line)" }}>
          <summary className="cursor-pointer text-sm" style={{ color: "var(--text-muted)" }}>
            {section.visualPrompts.length} shots
          </summary>
          <ol className="mt-3 grid gap-2">
            {section.visualPrompts.map((prompt, i) => (
              <li key={i} className="flex gap-3 text-sm" style={{ color: "var(--text-muted)" }}>
                <span className="font-mono text-xs tabular-nums" style={{ color: "var(--text-faint)" }}>
                  {String(i + 1).padStart(2, "0")}
                </span>
                <span className="min-w-0">{prompt}</span>
              </li>
            ))}
          </ol>
        </details>
      ) : null}
    </article>
  );
}

function EmptyState() {
  return (
    <div
      className="rounded-[--radius-card] border border-dashed p-10 text-center"
      style={{ borderColor: "var(--line)" }}
    >
      <p className="text-sm" style={{ color: "var(--text-muted)" }}>
        Give it a topic and a format. It plans the chapters first, then writes
        each one in order.
      </p>
      <p className="mt-2 text-xs" style={{ color: "var(--text-faint)" }}>
        A 14 minute script is about 9 model calls and takes a couple of minutes.
      </p>
    </div>
  );
}

function OutlineSkeleton() {
  return (
    <div className="grid gap-4" aria-live="polite" aria-busy="true">
      <div className="working h-7 w-2/3 rounded-[--radius-chip]" style={{ background: "var(--surface-sunken)" }} />
      <div className="working h-4 w-full rounded-[--radius-chip]" style={{ background: "var(--surface-sunken)" }} />
      <div
        className="working mt-4 h-64 rounded-[--radius-card]"
        style={{ background: "var(--surface-sunken)" }}
      />
      <p className="font-mono text-xs" style={{ color: "var(--text-faint)" }}>
        planning chapters
      </p>
    </div>
  );
}

function SectionSkeleton() {
  return (
    <div
      className="rounded-[--radius-card] border p-6"
      style={{ borderColor: "var(--line)" }}
      aria-live="polite"
      aria-busy="true"
    >
      <div className="working h-5 w-40 rounded-[--radius-chip]" style={{ background: "var(--surface-sunken)" }} />
      <div className="mt-4 grid gap-2.5">
        {[100, 96, 92, 98, 60].map((w, i) => (
          <div
            key={i}
            className="working h-3.5 rounded-[--radius-chip]"
            style={{ width: `${w}%`, background: "var(--surface-sunken)" }}
          />
        ))}
      </div>
    </div>
  );
}

function NextStep({ topic, format }: { topic: string; format: string }) {
  const command = `python -m longform import-script \\
  --file script.md \\
  --topic "${topic.replace(/"/g, '\\"')}" \\
  --format ${format}`;

  return (
    <div
      className="rounded-[--radius-card] border p-6"
      style={{ borderColor: "var(--line)", background: "var(--surface-sunken)" }}
    >
      <div className="flex items-center gap-2">
        <ArrowClockwise size={16} style={{ color: "var(--accent)" }} />
        <h3 className="text-sm font-semibold">Render it</h3>
      </div>
      <p className="mt-2 text-sm leading-relaxed" style={{ color: "var(--text-muted)" }}>
        Download the script, then run this where you have Python and ffmpeg.
      </p>
      <pre
        className="mt-4 overflow-x-auto rounded-[--radius-card] border p-4 font-mono text-xs leading-relaxed"
        style={{ borderColor: "var(--line)", background: "var(--surface-raised)" }}
      >
        <code>{command}</code>
      </pre>
    </div>
  );
}

function slug(text: string): string {
  return (
    text
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-|-$/g, "")
      .slice(0, 60) || "script"
  );
}
