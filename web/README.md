# Longform web

The landing page and the planning half of the `longform` engine, as a Next.js
app. Deployed on Vercel.

It writes the script. It does not render the video, and it cannot: rendering
needs ffmpeg, Whisper (torch plus model weights, well past Vercel's 250 MB
function bundle limit), minutes of CPU per video, and writable disk. So this app
does the part that is pure language and hands the script to the CLI.

```
browser                              your machine
  outline  ->  /api/outline            longform import-script
  script   ->  /api/section  (xN)      longform produce
  download ->  script.md               longform upload
```

## The one architectural decision

**The browser drives the loop, one HTTP request per section.**

The CLI writes a 15-minute script in about a dozen LLM calls taking several
minutes in total. A dozen calls inside one request would exceed any serverless
timeout. So `/api/section` writes exactly one section per request and the client
walks the list, passing forward a summary of every section already written.

Three things fall out of that, all of them good:

- No function invocation ever runs longer than a single LLM call.
- A failure on section six keeps sections one to five. The UI says so and still
  offers the download.
- Progress is visible per section instead of a spinner for three minutes.

## Deploying

The Next.js app lives in `web/`, not at the repository root, so Vercel needs to
be told where it is.

1. Import the repository at [vercel.com/new](https://vercel.com/new).
2. Set **Root Directory** to `web`. Everything else is detected.
3. Add an API key under **Settings → Environment Variables** (optional, see
   below), then deploy.

Or with the CLI:

```bash
npm i -g vercel
cd web
vercel        # first run links the project, answer "web" for the root directory
vercel --prod
```

## Environment variables

All optional. Set none and the planner requires each visitor to supply their own
key, which is the right setting for a public URL.

| Variable | Effect |
|---|---|
| `ANTHROPIC_API_KEY` | Claude is the default provider when this is set |
| `GEMINI_API_KEY` | Enables Gemini |
| `OPENAI_API_KEY` | Enables GPT |

A visitor-supplied key always takes precedence over the server's. Keys are read
per request, held in memory, and never written anywhere. The planner page is
`force-dynamic`, so adding a key in Vercel takes effect without a rebuild.

**If you set a server key and the URL is public, every visitor spends your
credits.** There is no rate limiting in this app. Either leave the keys unset,
or put the deployment behind Vercel's password protection.

## Format profiles

`lib/formats.ts` is generated from `formats/*.yaml` at the repository root, so
the planner and the CLI share one source of truth. After editing any format:

```bash
python3 scripts/gen_web_formats.py
```

`tests/test_web_formats_sync.py` fails if the generated file is stale.

## Local development

```bash
cd web
npm install
npm run dev
```

`http://localhost:3000`. Paste an API key into the planner; no env file needed.

## Layout

```
web/
├── app/
│   ├── page.tsx              # landing
│   ├── plan/page.tsx         # planner
│   └── api/
│       ├── outline/route.ts  # one call: plan the chapters
│       └── section/route.ts  # one call: write one section
├── components/
│   ├── planner.tsx           # the client that drives the loop
│   ├── chapter-strip.tsx     # chapter timeline, shared by both pages
│   ├── sections.tsx          # landing page sections
│   └── nav.tsx
└── lib/
    ├── formats.ts            # generated from formats/*.yaml
    ├── prompts.ts            # ports of the CLI's prompt builders
    ├── budgets.ts            # runtime target to word budget
    ├── plan.ts               # outline to ordered section list
    ├── llm.ts                # Claude / Gemini / GPT router
    └── types.ts
```

## What this app deliberately does not do

- **Render video.** Covered above.
- **Live research.** The CLI gates claims against a DuckDuckGo pass. The planner
  has none, so its prompts instruct the model not to invent statistics, dates,
  or quotations. Scripts from here are a draft to fact-check, not a source.
- **Store anything.** No database, no session, no analytics. Refreshing the page
  loses the script, which is why the download button appears as soon as the
  first section lands.
