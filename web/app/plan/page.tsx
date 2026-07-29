import type { Metadata } from "next";

import { Nav } from "@/components/nav";
import { Planner } from "@/components/planner";
import { Footer } from "@/components/sections";
import { hasServerKey } from "@/lib/llm";

export const metadata: Metadata = {
  title: "Plan a video — Longform",
  description:
    "Plan the chapters and write the narration for a faceless long-form YouTube video.",
};

// Read at request time so adding a key in Vercel takes effect without a rebuild.
export const dynamic = "force-dynamic";

export default function PlanPage() {
  return (
    <>
      <Nav />
      <main className="mx-auto max-w-6xl px-5 py-12 sm:py-16">
        <header className="mb-10 max-w-[52ch]">
          <h1 className="text-3xl font-semibold tracking-tight sm:text-4xl">
            Plan a video
          </h1>
          <p
            className="mt-4 text-base leading-relaxed"
            style={{ color: "var(--text-muted)" }}
          >
            The chapters get planned first, then each section is written in
            order with the previous ones in context. Download the result and
            render it with the CLI.
          </p>
        </header>

        <Planner serverKeyAvailable={hasServerKey()} />
      </main>
      <Footer />
    </>
  );
}
