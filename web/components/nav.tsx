import Link from "next/link";
import { GithubLogo } from "@phosphor-icons/react/dist/ssr";

export function Nav() {
  return (
    <header
      className="sticky top-0 z-40 border-b backdrop-blur-md"
      style={{
        borderColor: "var(--line)",
        background: "color-mix(in srgb, var(--surface) 88%, transparent)",
      }}
    >
      <nav className="mx-auto flex h-16 max-w-6xl items-center justify-between gap-6 px-5">
        <Link href="/" className="flex items-baseline gap-2">
          <span className="text-[15px] font-semibold tracking-tight">
            Longform
          </span>
          <span
            className="hidden font-mono text-xs sm:inline"
            style={{ color: "var(--text-faint)" }}
          >
            faceless video engine
          </span>
        </Link>

        <div className="flex items-center gap-5">
          <Link
            href="#formats"
            className="hidden text-sm transition-colors hover:opacity-70 sm:block"
            style={{ color: "var(--text-muted)" }}
          >
            Formats
          </Link>
          <Link
            href="#pipeline"
            className="hidden text-sm transition-colors hover:opacity-70 sm:block"
            style={{ color: "var(--text-muted)" }}
          >
            Pipeline
          </Link>
          <Link
            href="#install"
            className="hidden text-sm transition-colors hover:opacity-70 sm:block"
            style={{ color: "var(--text-muted)" }}
          >
            Install
          </Link>
          <a
            href="https://github.com/Jmasis23/youtube-shorts-pipeline"
            target="_blank"
            rel="noreferrer"
            aria-label="Source on GitHub"
            className="transition-opacity hover:opacity-70"
            style={{ color: "var(--text-muted)" }}
          >
            <GithubLogo size={19} weight="regular" />
          </a>
          <Link
            href="/plan"
            className="rounded-[--radius-card] px-3.5 py-2 text-sm font-medium transition-transform active:translate-y-px"
            style={{ background: "var(--accent)", color: "var(--accent-contrast)" }}
          >
            Plan a video
          </Link>
        </div>
      </nav>
    </header>
  );
}
