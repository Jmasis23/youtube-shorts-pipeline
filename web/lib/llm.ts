import type { Provider } from "./types";

// Port of verticals/llm.py's router, trimmed to the three providers that make
// sense from a serverless function (no local Ollama, no CLI fallback).

// Google retires Gemini model IDs on a rolling basis (2.0 Flash was cut off
// mid-2026); check https://ai.google.dev/gemini-api/docs/models if this
// starts 404ing and bump it here.
const MODELS: Record<Provider, string> = {
  anthropic: "claude-sonnet-4-6",
  gemini: "gemini-3.6-flash",
  openai: "gpt-4o-mini",
};

export class LlmError extends Error {
  status: number;
  constructor(message: string, status = 502) {
    super(message);
    this.status = status;
  }
}

/** Resolve the key: caller-supplied first, then the server's own. */
export function resolveKey(provider: Provider, supplied?: string): string {
  if (supplied && supplied.trim()) return supplied.trim();

  const envKey =
    provider === "anthropic"
      ? process.env.ANTHROPIC_API_KEY
      : provider === "gemini"
        ? process.env.GEMINI_API_KEY
        : process.env.OPENAI_API_KEY;

  if (!envKey) {
    throw new LlmError(
      `No API key for ${provider}. Add one in the planner, or set it in the Vercel project environment.`,
      401,
    );
  }
  return envKey;
}

export function defaultProvider(): Provider {
  if (process.env.ANTHROPIC_API_KEY) return "anthropic";
  if (process.env.GEMINI_API_KEY) return "gemini";
  if (process.env.OPENAI_API_KEY) return "openai";
  return "anthropic";
}

export function hasServerKey(): boolean {
  return Boolean(
    process.env.ANTHROPIC_API_KEY ||
      process.env.GEMINI_API_KEY ||
      process.env.OPENAI_API_KEY,
  );
}

export async function callLlm(
  prompt: string,
  provider: Provider,
  apiKey: string,
  maxTokens = 4000,
): Promise<string> {
  if (provider === "anthropic") return callAnthropic(prompt, apiKey, maxTokens);
  if (provider === "gemini") return callGemini(prompt, apiKey, maxTokens);
  return callOpenAi(prompt, apiKey, maxTokens);
}

async function callAnthropic(prompt: string, apiKey: string, maxTokens: number) {
  const r = await fetch("https://api.anthropic.com/v1/messages", {
    method: "POST",
    headers: {
      "content-type": "application/json",
      "x-api-key": apiKey,
      "anthropic-version": "2023-06-01",
    },
    body: JSON.stringify({
      model: MODELS.anthropic,
      max_tokens: maxTokens,
      messages: [{ role: "user", content: prompt }],
    }),
  });

  if (!r.ok) throw await httpError(r, "Anthropic");
  const data = await r.json();
  const text = data?.content?.[0]?.text;
  if (!text) throw new LlmError("Empty response from Anthropic");
  return text.trim();
}

async function callGemini(prompt: string, apiKey: string, maxTokens: number) {
  const r = await fetch(
    `https://generativelanguage.googleapis.com/v1beta/models/${MODELS.gemini}:generateContent`,
    {
      method: "POST",
      headers: { "content-type": "application/json", "x-goog-api-key": apiKey },
      body: JSON.stringify({
        contents: [{ parts: [{ text: prompt }] }],
        generationConfig: { maxOutputTokens: maxTokens, temperature: 0.7 },
      }),
    },
  );

  if (!r.ok) {
    if (r.status === 404) {
      const detail = await r.text();
      throw new LlmError(
        `Gemini 404: ${detail.slice(0, 200)} — ${MODELS.gemini} may have been ` +
          "retired; check current model IDs at " +
          "https://ai.google.dev/gemini-api/docs/models and update MODELS.gemini " +
          "in web/lib/llm.ts",
      );
    }
    throw await httpError(r, "Gemini");
  }
  const data = await r.json();
  const parts = data?.candidates?.[0]?.content?.parts ?? [];
  const text = parts.map((p: { text?: string }) => p.text ?? "").join(" ").trim();
  if (!text) throw new LlmError("Empty response from Gemini");
  return text;
}

async function callOpenAi(prompt: string, apiKey: string, maxTokens: number) {
  const r = await fetch("https://api.openai.com/v1/chat/completions", {
    method: "POST",
    headers: {
      "content-type": "application/json",
      authorization: `Bearer ${apiKey}`,
    },
    body: JSON.stringify({
      model: MODELS.openai,
      max_tokens: maxTokens,
      temperature: 0.7,
      messages: [{ role: "user", content: prompt }],
    }),
  });

  if (!r.ok) throw await httpError(r, "OpenAI");
  const data = await r.json();
  const text = data?.choices?.[0]?.message?.content;
  if (!text) throw new LlmError("Empty response from OpenAI");
  return text.trim();
}

async function httpError(r: Response, label: string): Promise<LlmError> {
  const body = await r.text();
  let detail = body.slice(0, 300);
  try {
    const parsed = JSON.parse(body);
    detail = parsed?.error?.message ?? detail;
  } catch {
    // keep the raw body
  }
  // 401 and 429 are the two the user can act on, so pass them through intact.
  const status = r.status === 401 || r.status === 429 ? r.status : 502;
  return new LlmError(`${label} ${r.status}: ${detail}`, status);
}

/**
 * Extract a JSON object from an LLM response.
 * Port of longform/util.py's parseJsonResponse, same failure behaviour.
 */
export function parseJsonResponse<T>(raw: string): T {
  let text = (raw ?? "").trim();

  if (text.includes("```")) {
    const parts = text.split("```");
    if (parts.length >= 2) {
      let block = parts[1];
      if (block.trimStart().toLowerCase().startsWith("json")) {
        block = block.trimStart().slice(4);
      }
      text = block.trim();
    }
  }

  const start = text.indexOf("{");
  const end = text.lastIndexOf("}") + 1;
  if (start < 0 || end <= start) {
    throw new LlmError(`No JSON object in model response: ${raw.slice(0, 200)}`);
  }

  try {
    return JSON.parse(text.slice(start, end)) as T;
  } catch (e) {
    throw new LlmError(
      `Malformed JSON from model: ${(e as Error).message}. Try again, or switch provider.`,
    );
  }
}

export function asStringList(value: unknown, limit?: number): string[] {
  const items = Array.isArray(value) ? value : value == null ? [] : [value];
  const out = items
    .map((v) => (typeof v === "string" ? v.trim() : String(v).trim()))
    .filter(Boolean);
  return limit ? out.slice(0, limit) : out;
}

export function asString(value: unknown): string {
  if (value == null) return "";
  if (typeof value === "string") return value.trim();
  if (Array.isArray(value)) return value.map(asString).join(" ").trim();
  return String(value).trim();
}
