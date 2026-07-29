import Image from "next/image";
import Link from "next/link";
import {
  ArrowRight,
  FilmSlate,
  Microphone,
  Notches,
  Question,
  Ranking,
  ScrollIcon,
  Sparkle,
  Waveform,
} from "@phosphor-icons/react/dist/ssr";

import { chapterWordBudgets } from "@/lib/budgets";
import { FORMATS } from "@/lib/formats";
import { ChapterStrip } from "./chapter-strip";

const SAMPLE_BUDGETS = chapterWordBudgets(14, 6);
const SAMPLE_CHAPTERS = [
  "Intro",
  "Before The Box",
  "Newark, 1956",
  "The Standard Nobody Wanted",
  "The Ports That Bet Wrong",
  "What Moved Instead",
  "The Second-Order World",
  "Outro",
];

// ─────────────────────────────────────────────────────
// Hero: asymmetric split, real component on the right
// ─────────────────────────────────────────────────────

export function Hero() {
  const strip = [
    { title: SAMPLE_CHAPTERS[0], wordBudget: SAMPLE_BUDGETS.intro },
    ...SAMPLE_BUDGETS.chapters.map((wordBudget, i) => ({
      title: SAMPLE_CHAPTERS[i + 1],
      wordBudget,
    })),
    { title: "Outro", wordBudget: SAMPLE_BUDGETS.outro },
  ];

  return (
    <section className="mx-auto max-w-6xl px-5 pt-16 pb-20 sm:pt-24 sm:pb-28">
      <div className="grid items-center gap-12 lg:grid-cols-[1.05fr_0.95fr] lg:gap-16">
        <div className="rise">
          {/* Eight words, so the scale stays in the 4xl/5xl band and the
              explicit break holds it to two lines at every width. */}
          <h1 className="text-4xl font-semibold leading-[1.08] tracking-tight sm:text-5xl">
            Long videos that hold,
            <br />
            written a chapter at a time.
          </h1>
          <p
            className="mt-6 max-w-[54ch] text-base leading-relaxed sm:text-lg"
            style={{ color: "var(--text-muted)" }}
          >
            One prompt cannot write 2,500 coherent words. Longform plans the
            chapters first, then writes each one knowing what came before.
          </p>
          <div className="mt-9 flex flex-wrap items-center gap-3">
            <Link
              href="/plan"
              className="inline-flex items-center gap-2 rounded-[--radius-card] px-5 py-3 text-sm font-medium transition-transform active:translate-y-px"
              style={{
                background: "var(--accent)",
                color: "var(--accent-contrast)",
              }}
            >
              Plan a video
              <ArrowRight size={16} weight="bold" />
            </Link>
            <Link
              href="#install"
              className="inline-flex items-center gap-2 rounded-[--radius-card] border px-5 py-3 text-sm font-medium transition-colors"
              style={{ borderColor: "var(--line)", color: "var(--text)" }}
            >
              Run it locally
            </Link>
          </div>
        </div>

        <div className="rise" style={{ animationDelay: "120ms" }}>
          <ChapterStrip
            chapters={strip}
            totalWords={SAMPLE_BUDGETS.total}
            caption="A 14 minute documentary plan. Timestamps here are estimates from the word budget; the CLI replaces them with timings measured from the rendered audio."
          />
        </div>
      </div>
    </section>
  );
}

// ─────────────────────────────────────────────────────
// Why two passes: full-width editorial statement
// ─────────────────────────────────────────────────────

export function TwoPasses() {
  return (
    <section
      className="border-y py-20 sm:py-28"
      style={{ borderColor: "var(--line)", background: "var(--surface-sunken)" }}
    >
      <div className="mx-auto max-w-6xl px-5">
        <h2 className="max-w-[22ch] text-3xl font-semibold leading-tight tracking-tight sm:text-4xl">
          Ask for the whole script at once and it drifts.
        </h2>
        <p
          className="mt-5 max-w-[62ch] text-base leading-relaxed"
          style={{ color: "var(--text-muted)" }}
        >
          By the halfway mark the model has forgotten its own cold open, started
          repeating itself in new words, and hit the output token ceiling. So
          Longform never asks for the whole thing.
        </p>

        <div className="mt-14 grid gap-px overflow-hidden rounded-[--radius-card] border md:grid-cols-2"
          style={{ borderColor: "var(--line)", background: "var(--line)" }}
        >
          <article className="p-7 sm:p-9" style={{ background: "var(--surface-raised)" }}>
            <Notches size={22} weight="regular" style={{ color: "var(--accent)" }} />
            <h3 className="mt-4 text-lg font-semibold tracking-tight">
              Plan the chapters
            </h3>
            <p
              className="mt-3 text-sm leading-relaxed"
              style={{ color: "var(--text-muted)" }}
            >
              Your runtime target fixes a word budget per chapter. Each chapter
              gets a distinct job, three to five concrete beats, and the
              unresolved note it has to end on. The open loop is assigned a
              chapter that knows it is the payoff.
            </p>
          </article>

          <article className="p-7 sm:p-9" style={{ background: "var(--surface-raised)" }}>
            <ScrollIcon size={22} weight="regular" style={{ color: "var(--accent)" }} />
            <h3 className="mt-4 text-lg font-semibold tracking-tight">
              Write them in order
            </h3>
            <p
              className="mt-3 text-sm leading-relaxed"
              style={{ color: "var(--text-muted)" }}
            >
              One call per section, each carrying a summary of every section
              already written. Chapter four can see the thesis, the open loop,
              and what chapters one to three established, so it moves the
              argument instead of restating it.
            </p>
          </article>
        </div>
      </div>
    </section>
  );
}

// ─────────────────────────────────────────────────────
// Formats: bento, exactly six cells for six formats
// ─────────────────────────────────────────────────────

// Every cell carries artwork so the grid has no dead space, and each seed is
// chosen to stand in for that format's own visual direction.
const FORMAT_ART: Record<string, { seed: string; alt: string }> = {
  documentary: {
    seed: "longform-documentary-archive-terrain",
    alt: "Wide desaturated landscape, the documentary format's visual direction",
  },
  explainer: {
    seed: "longform-explainer-macro-material",
    alt: "Macro detail shot in clean natural light, the explainer format's visual direction",
  },
  case_study: {
    seed: "longform-casestudy-logistics-infrastructure",
    alt: "Cool-graded infrastructure photography, the case study format's visual direction",
  },
  story: {
    seed: "longform-story-interior-window-light",
    alt: "Empty interior with warm practical light, the story format's visual direction",
  },
  listicle: {
    seed: "longform-listicle-highkey-object",
    alt: "Bright high-key product photography, the countdown format's visual direction",
  },
  video_essay: {
    seed: "longform-essay-threshold-negative-space",
    alt: "Editorial photograph with negative space, the video essay format's visual direction",
  },
};

const FORMAT_ICON: Record<string, typeof FilmSlate> = {
  documentary: FilmSlate,
  explainer: Question,
  listicle: Ranking,
  story: Sparkle,
  case_study: Notches,
  video_essay: ScrollIcon,
};

export function Formats() {
  // Six formats, six cells. The three with artwork span wider so the grid has
  // rhythm rather than six identical tiles.
  const order = [
    "documentary",
    "explainer",
    "case_study",
    "story",
    "listicle",
    "video_essay",
  ];
  const formats = order
    .map((name) => FORMATS.find((f) => f.name === name))
    .filter(Boolean) as typeof FORMATS;

  return (
    <section id="formats" className="mx-auto max-w-6xl scroll-mt-20 px-5 py-20 sm:py-28">
      <h2 className="max-w-[20ch] text-3xl font-semibold leading-tight tracking-tight sm:text-4xl">
        Six formats. Each one builds a video differently.
      </h2>
      <p
        className="mt-5 max-w-[62ch] text-base leading-relaxed"
        style={{ color: "var(--text-muted)" }}
      >
        A format owns structure: how many chapters, what each has to accomplish,
        where the open loop pays off, which voice reads it and how. Pair it with
        a niche and the niche supplies the subject flavour.
      </p>

      <div className="mt-12 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {formats.map((format, i) => {
          const art = FORMAT_ART[format.name];
          const Icon = FORMAT_ICON[format.name] ?? FilmSlate;
          const wide = i === 0 || i === 3;

          return (
            <article
              key={format.name}
              className={`flex flex-col overflow-hidden rounded-[--radius-card] border ${
                wide ? "sm:col-span-2 lg:col-span-2" : ""
              }`}
              style={{
                borderColor: "var(--line)",
                background: "var(--surface-raised)",
              }}
            >
              {art ? (
                <div
                  className={`relative w-full overflow-hidden ${
                    wide ? "aspect-[16/6]" : "aspect-[16/9]"
                  }`}
                  style={{ background: "var(--surface-sunken)" }}
                >
                  <Image
                    src={`https://picsum.photos/seed/${art.seed}/1200/675`}
                    alt={art.alt}
                    fill
                    sizes="(max-width: 640px) 100vw, (max-width: 1024px) 50vw, 640px"
                    className="object-cover"
                  />
                </div>
              ) : null}

              <div className="flex flex-1 flex-col p-6">
                <Icon size={20} weight="regular" style={{ color: "var(--accent)" }} />
                <h3 className="mt-3.5 text-base font-semibold tracking-tight">
                  {format.displayName}
                </h3>
                <p
                  className="mt-2 flex-1 text-sm leading-relaxed"
                  style={{ color: "var(--text-muted)" }}
                >
                  {format.description}
                </p>
                <dl
                  className="mt-5 flex flex-wrap gap-x-5 gap-y-1 font-mono text-xs"
                  style={{ color: "var(--text-faint)" }}
                >
                  <div className="flex gap-1.5">
                    <dt className="sr-only">Runtime</dt>
                    <dd>{format.targetMinutes} min</dd>
                  </div>
                  <div className="flex gap-1.5">
                    <dt className="sr-only">Chapters</dt>
                    <dd>{format.chapters} chapters</dd>
                  </div>
                  <div className="flex gap-1.5">
                    <dt className="sr-only">Narration voice</dt>
                    <dd>{format.voiceName}</dd>
                  </div>
                </dl>
              </div>
            </article>
          );
        })}
      </div>

      <p className="mt-6 text-xs" style={{ color: "var(--text-faint)" }}>
        Artwork above is placeholder photography standing in for each format's
        visual direction. The engine generates its own scenes at render time.
      </p>
    </section>
  );
}

// ─────────────────────────────────────────────────────
// Pipeline: horizontal rail, split into what runs where
// ─────────────────────────────────────────────────────

const BROWSER_STAGES = [
  { name: "outline", note: "Chapters, jobs, beats, word budgets" },
  { name: "script", note: "One call per section, rolling context" },
];

const LOCAL_STAGES = [
  { name: "narration", note: "Chunked Gemini TTS per section", icon: Microphone },
  { name: "scenes", note: "One visual every few seconds", icon: FilmSlate },
  { name: "chapters", note: "Timestamps measured from audio", icon: Notches },
  { name: "render", note: "ffmpeg, ducking, loudness", icon: Waveform },
];

export function Pipeline() {
  return (
    <section
      id="pipeline"
      className="border-y py-20 sm:py-28"
      style={{ borderColor: "var(--line)", background: "var(--surface-sunken)" }}
    >
      <div className="mx-auto max-w-6xl px-5">
        <h2 className="max-w-[24ch] text-3xl font-semibold leading-tight tracking-tight sm:text-4xl">
          The writing runs here. The render runs on your machine.
        </h2>
        <p
          className="mt-5 max-w-[62ch] text-base leading-relaxed"
          style={{ color: "var(--text-muted)" }}
        >
          Rendering needs ffmpeg, Whisper, and minutes of CPU per video, which no
          serverless function will give you. So this site does the part that is
          pure language, and hands the script to the CLI for everything after.
        </p>

        <div className="mt-12 grid gap-8 lg:grid-cols-[0.8fr_1.2fr] lg:gap-12">
          <div>
            <h3 className="font-mono text-xs" style={{ color: "var(--accent)" }}>
              in the browser
            </h3>
            <ul className="mt-4 grid gap-3">
              {BROWSER_STAGES.map((stage) => (
                <li
                  key={stage.name}
                  className="rounded-[--radius-card] border p-4"
                  style={{
                    borderColor: "var(--accent)",
                    background: "var(--surface-raised)",
                  }}
                >
                  <span className="font-mono text-sm">{stage.name}</span>
                  <p className="mt-1 text-sm" style={{ color: "var(--text-muted)" }}>
                    {stage.note}
                  </p>
                </li>
              ))}
            </ul>
          </div>

          <div>
            <h3 className="font-mono text-xs" style={{ color: "var(--text-faint)" }}>
              on your machine
            </h3>
            <ul className="mt-4 grid gap-3 sm:grid-cols-2">
              {LOCAL_STAGES.map((stage) => {
                const Icon = stage.icon;
                return (
                  <li
                    key={stage.name}
                    className="rounded-[--radius-card] border p-4"
                    style={{
                      borderColor: "var(--line)",
                      background: "var(--surface-raised)",
                    }}
                  >
                    <Icon size={18} weight="regular" style={{ color: "var(--text-faint)" }} />
                    <span className="mt-2 block font-mono text-sm">{stage.name}</span>
                    <p className="mt-1 text-sm" style={{ color: "var(--text-muted)" }}>
                      {stage.note}
                    </p>
                  </li>
                );
              })}
            </ul>
          </div>
        </div>
      </div>
    </section>
  );
}

// ─────────────────────────────────────────────────────
// Install: two column, code left, prose right
// ─────────────────────────────────────────────────────

export function Install() {
  return (
    <section id="install" className="mx-auto max-w-6xl scroll-mt-20 px-5 py-20 sm:py-28">
      <div className="grid gap-10 lg:grid-cols-2 lg:gap-16">
        <div>
          <h2 className="text-3xl font-semibold leading-tight tracking-tight sm:text-4xl">
            Take the script and render it
          </h2>
          <p
            className="mt-5 text-base leading-relaxed"
            style={{ color: "var(--text-muted)" }}
          >
            Download the script from the planner, then hand it to the CLI. It
            narrates each section, generates a scene every few seconds, measures
            the audio to build real chapter timestamps, and renders a 16:9 file
            ready to upload.
          </p>
          <p
            className="mt-4 text-base leading-relaxed"
            style={{ color: "var(--text-muted)" }}
          >
            You need Python 3.10 or newer and ffmpeg. Everything else is
            optional: without an image key the render still runs, using
            placeholder scenes, so you can check pacing before spending
            anything.
          </p>
        </div>

        <div
          className="overflow-hidden rounded-[--radius-card] border"
          style={{ borderColor: "var(--line)", background: "var(--surface-raised)" }}
        >
          <pre className="overflow-x-auto p-6 font-mono text-[13px] leading-relaxed">
            <code>
              <span style={{ color: "var(--text-faint)" }}># install</span>
              {"\n"}
              git clone https://github.com/Jmasis23/youtube-shorts-pipeline
              {"\n"}
              cd youtube-shorts-pipeline{"\n"}
              pip install -r requirements.txt{"\n\n"}
              <span style={{ color: "var(--text-faint)" }}>
                # render the script you just downloaded
              </span>
              {"\n"}
              python -m longform import-script \{"\n"}
              {"  "}--file script.md \{"\n"}
              {"  "}--topic <span style={{ color: "var(--accent)" }}>&quot;your topic&quot;</span> \{"\n"}
              {"  "}--format documentary{"\n\n"}
              python -m longform produce --project{" "}
              <span style={{ color: "var(--accent)" }}>&lt;id&gt;</span>
              {"\n"}
              python -m longform upload --project{" "}
              <span style={{ color: "var(--accent)" }}>&lt;id&gt;</span>
              {"\n\n"}
              <span style={{ color: "var(--text-faint)" }}>
                # or skip the browser entirely
              </span>
              {"\n"}
              python -m longform run --topic{" "}
              <span style={{ color: "var(--accent)" }}>&quot;your topic&quot;</span> \{"\n"}
              {"  "}--format documentary --minutes 14
            </code>
          </pre>
        </div>
      </div>
    </section>
  );
}

export function Footer() {
  return (
    <footer
      className="border-t py-10"
      style={{ borderColor: "var(--line)" }}
    >
      <div className="mx-auto flex max-w-6xl flex-col gap-4 px-5 sm:flex-row sm:items-center sm:justify-between">
        <p className="text-sm" style={{ color: "var(--text-faint)" }}>
          Longform is the long-form half of an open source video engine. MIT
          licensed.
        </p>
        <a
          href="https://github.com/Jmasis23/youtube-shorts-pipeline"
          target="_blank"
          rel="noreferrer"
          className="text-sm transition-opacity hover:opacity-70"
          style={{ color: "var(--text-muted)" }}
        >
          Source and documentation
        </a>
      </div>
    </footer>
  );
}
