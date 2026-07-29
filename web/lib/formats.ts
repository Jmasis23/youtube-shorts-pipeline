// GENERATED FILE. Do not edit by hand.
// Source: formats/*.yaml
// Regenerate: python3 scripts/gen_web_formats.py
//
// The CLI reads the YAML directly; the web planner reads this module. Keeping
// one source of truth is what stops the two halves drifting apart.

export interface FormatHook {
  template: string;
  when?: string;
}

export interface FormatProfile {
  name: string;
  displayName: string;
  description: string;
  targetMinutes: number;
  chapters: number;
  sceneSeconds: number;
  tone: string;
  narrationStyle: string;
  perspective: string;
  arc: Record<string, string>;
  openLoop: string;
  retentionRules: string[];
  hooks: FormatHook[];
  cta: string;
  forbiddenPhrases: string[];
  voiceName: string;
  voiceStyle: string;
  categoryId: string;
  titleStyle: string;
  visualStyle: string;
  visualMood: string;
  promptSuffix: string;
  subjectsPrefer: string[];
  subjectsAvoid: string[];
  burnCaptions: boolean;
}

export const FORMATS: FormatProfile[] = [
  {
    "name": "case_study",
    "displayName": "Business Case Study",
    "description": "How a company, product, or person actually made or lost money. Numbers-led, mechanism-first, no hagiography. The strongest faceless format for high-CPM finance and business audiences.",
    "targetMinutes": 13,
    "chapters": 6,
    "sceneSeconds": 8.0,
    "tone": "analytical, sceptical, plainly numerate",
    "narrationStyle": "Second person for the lessons, third person for the events. Always give the number before the adjective — \"revenue fell 34%\", not \"revenue collapsed\". Name the mechanism, not the vibe. Assume the viewer can do arithmetic.",
    "perspective": "an analyst walking through the numbers, not a fan",
    "arc": {
      "intro": "Open with the single most striking number in the whole story and what it means. State the question the case study answers: how, specifically.",
      "early": "The starting conditions. What the market looked like, what the constraint was, and what everyone else was doing at the time.",
      "middle": "The decision and the mechanism. This is the heart — explain exactly how the money moved, with unit economics where the research supports them.",
      "late": "What broke or what compounded, and the counterfactual. What would have happened under the obvious alternative decision.",
      "outro": "Three transferable lessons, each stated as a rule the viewer could apply to a decision of their own. Then the call to action."
    },
    "openLoop": "Put a number in the intro that appears impossible given the starting conditions, and promise the mechanism that explains it. Deliver it in the middle chapter.",
    "retentionRules": [
      "Every chapter needs at least two specific figures from the research.",
      "State the time period any figure belongs to — undated numbers are noise.",
      "Name the counterargument before dismissing it.",
      "Never attribute an outcome to \"vision\" or \"genius\" — name the mechanism.",
      "Flag explicitly when a figure is an estimate rather than reported."
    ],
    "hooks": [
      {
        "template": "{company} spent {amount} to acquire customers worth {value}. That should have killed them. It did the opposite.",
        "when": "the unit economics look wrong at first glance"
      },
      {
        "template": "In {year}, {company} made {amount}. {years} later they made {amount2}. The difference is one decision, and it wasn't the product.",
        "when": "there is a single pivotal decision"
      },
      {
        "template": "Everyone explains {company}'s collapse the same way. The numbers say something else happened first.",
        "when": "the consensus explanation is wrong"
      }
    ],
    "cta": "Point at the specific adjacent case study that tests the same lesson. Frame it as further evidence, not as content.",
    "forbiddenPhrases": [
      "game changer",
      "disrupted the industry",
      "the rest is history",
      "changed everything",
      "genius move",
      "in today's video",
      "smash that like"
    ],
    "voiceName": "Sadaltager",
    "voiceStyle": "Read this as a business analyst walking through numbers — precise, even, slightly dry, emphasising figures rather than adjectives",
    "categoryId": "27",
    "titleStyle": "Company or product name, then the specific number or mechanism. Concrete over dramatic. Under 60 characters.",
    "visualStyle": "modern corporate documentary, clean, cool colour grade, architectural",
    "visualMood": "precise, considered, slightly cold",
    "promptSuffix": "editorial photography, 16:9, cool colour grade, clean composition, natural light, no text, no charts, no watermarks, no logos",
    "subjectsPrefer": [
      "the physical product or storefront being discussed",
      "warehouses, factories, logistics, and infrastructure",
      "empty modern offices and boardrooms",
      "the raw materials or inputs in the supply chain",
      "city skylines and financial districts at specific times of day"
    ],
    "subjectsAvoid": [
      "faces",
      "stock-photo handshakes and pointing-at-laptop shots",
      "fake charts or graphs, which will render as unreadable garbage",
      "legible on-screen text, brand marks, or currency symbols"
    ],
    "burnCaptions": false
  },
  {
    "name": "documentary",
    "displayName": "Documentary Deep Dive",
    "description": "A long, evidence-led investigation of one subject. Chronology carries the viewer; the narration stays restrained and lets the facts do the work. The register is prestige documentary, not YouTube commentary.",
    "targetMinutes": 16,
    "chapters": 6,
    "sceneSeconds": 11.0,
    "tone": "measured, restrained, quietly authoritative — never breathless",
    "narrationStyle": "Third person. Long sentences with real subordinate clauses, cut against short flat ones for emphasis. Dates, places, and names stated plainly. Understatement over emphasis: the material is dramatic, the narrator is not.",
    "perspective": "a narrator assembling evidence in front of the viewer",
    "arc": {
      "intro": "Cold open on the single most arresting moment in the whole story, told in present tense, out of chronological order. Cut away before resolving it. Then state what this film is about.",
      "early": "Go back to the beginning. Establish who, where, and when, and what the world looked like before any of this happened.",
      "middle": "The escalation. Each development makes the next one inevitable — show that causal chain rather than listing events.",
      "late": "The turn, and the consequences that followed. Return to the cold-open moment and resolve it in full context.",
      "outro": "What is left behind. Name what changed and what did not. End on the unresolved question rather than a tidy moral."
    },
    "openLoop": "The cold open is the loop. Reference it obliquely at least twice in the middle chapters before resolving it in the last body chapter.",
    "retentionRules": [
      "Every claim must be attributable to something in the research block.",
      "Give at least one specific number, date, or quantity per chapter.",
      "Never say \"we may never know\" — say what is actually documented.",
      "Withhold one named detail from the cold open and reveal it late.",
      "No rhetorical questions to the audience. This is narration, not chat."
    ],
    "hooks": [
      {
        "template": "On {date}, {subject} did something that should have been impossible. It took {duration} for anyone to notice.",
        "when": "there is a datable inciting incident"
      },
      {
        "template": "The official record of {topic} runs to a few paragraphs. What is missing from it is the entire story.",
        "when": "the accepted account is incomplete"
      },
      {
        "template": "{subject} was, by every measure available at the time, a complete success. That is what makes what happened next so difficult to explain.",
        "when": "the story is a reversal"
      }
    ],
    "cta": "A single restrained line pointing to the related film the viewer should watch next. No enthusiasm, no imperatives beyond one.",
    "forbiddenPhrases": [
      "in today's video",
      "little did they know",
      "you won't believe",
      "the rest is history",
      "shrouded in mystery",
      "to this day, nobody knows",
      "let that sink in"
    ],
    "voiceName": "Charon",
    "voiceStyle": "Read this as a restrained documentary narrator — measured, low-energy, letting the facts carry the weight, never dramatising",
    "categoryId": "27",
    "titleStyle": "Declarative, specific, slightly formal. Name the subject and the year or place. No questions, no second person, no punctuation beyond a colon.",
    "visualStyle": "archival-feeling cinematography, desaturated, heavy grain, deep shadows, anamorphic framing",
    "visualMood": "sombre, weighty, atmospheric",
    "promptSuffix": "documentary cinematography, 16:9, film grain, desaturated colour grade, natural available light, no text, no watermarks, no logos",
    "subjectsPrefer": [
      "period-accurate locations and interiors, empty",
      "weathered objects and documents photographed in raking light",
      "aerial and wide establishing shots of real terrain",
      "machinery, infrastructure, and vehicles of the era",
      "weather and time-of-day as mood"
    ],
    "subjectsAvoid": [
      "faces",
      "identifiable real people",
      "re-enactors in costume",
      "modern branding or signage",
      "legible on-screen text"
    ],
    "burnCaptions": false
  },
  {
    "name": "explainer",
    "displayName": "Explainer",
    "description": "Answers one question thoroughly. The viewer arrives confused about a thing and leaves able to explain it to someone else. Builds understanding in layers: each chapter is only understandable because the previous one landed.",
    "targetMinutes": 10,
    "chapters": 5,
    "sceneSeconds": 9.0,
    "tone": "clear, authoritative, unhurried, never condescending",
    "narrationStyle": "Second person. Short declarative sentences broken up by the occasional long one. Concrete nouns over abstractions. Define a term the first time it is used, then use it freely. Read aloud naturally — this is spoken, not written.",
    "perspective": "a knowledgeable friend explaining over coffee, not a lecturer",
    "arc": {
      "intro": "Cold open on the question itself, phrased so the viewer feels the gap in their own understanding. State plainly what they will be able to explain by the end. Do not introduce yourself or the channel.",
      "early": "Establish the ground floor — the one mechanism everything else rests on. Assume zero prior knowledge here and only here.",
      "middle": "Add the complication. The simple version the viewer now holds is incomplete; show precisely where it breaks.",
      "late": "Resolve the complication into the full picture. This is the payoff the cold open promised.",
      "outro": "Compress the whole explanation into three sentences the viewer could repeat from memory. Then the call to action."
    },
    "openLoop": "Name a specific counterintuitive fact in the first 20 seconds and say it will only make sense by chapter three. Pay it off there, explicitly.",
    "retentionRules": [
      "Open each chapter with a question the previous chapter made the viewer ask.",
      "Never summarise what was just said — move forward instead.",
      "Use a concrete number or named example at least once per chapter.",
      "End each chapter on an unresolved beat so the next one has to start."
    ],
    "hooks": [
      {
        "template": "Almost everything you've been told about {topic} is a simplification. Here's the version that actually holds up.",
        "when": "the popular understanding is a useful lie"
      },
      {
        "template": "{topic} shouldn't work. It does, and the reason is stranger than you'd guess.",
        "when": "the mechanism is counterintuitive"
      },
      {
        "template": "There's one question about {topic} nobody seems to answer directly. So let's answer it directly.",
        "when": "the topic is widely covered but shallowly"
      }
    ],
    "cta": "One sentence, tied to the content — point at the specific next question the video opened. No \"smash that like button\", no begging.",
    "forbiddenPhrases": [
      "in today's video",
      "without further ado",
      "buckle up",
      "let that sink in",
      "hey guys",
      "don't forget to subscribe",
      "we've all been there"
    ],
    "voiceName": "Iapetus",
    "voiceStyle": "Read this as a clear, unhurried explainer narrator — steady pace, warm but not chatty, landing each idea before moving to the next",
    "categoryId": "27",
    "titleStyle": "Specific and concrete. Name the actual subject. Curiosity from precision, not from withholding. No all-caps, no more than one piece of punctuation.",
    "visualStyle": "clean, cinematic, photorealistic, shallow depth of field, natural light",
    "visualMood": "calm, considered, quietly premium",
    "promptSuffix": "cinematic lighting, 16:9 composition, high detail, muted colour grade, no text, no watermarks, no logos",
    "subjectsPrefer": [
      "macro detail shots of the objects being discussed",
      "empty architectural interiors with strong light",
      "hands working with tools or materials, cropped above the wrist",
      "landscapes and infrastructure at golden hour",
      "abstract textures that echo the concept"
    ],
    "subjectsAvoid": [
      "faces",
      "talking-head presenters",
      "stock-photo business handshakes",
      "anything with legible on-screen text"
    ],
    "burnCaptions": false
  },
  {
    "name": "listicle",
    "displayName": "Ranked List / Countdown",
    "description": "A ranked countdown where each entry is a self-contained mini-story. The ranking has to be defensible, because an arbitrary order is what makes these feel cheap. Built for high browse-traffic and strong session time.",
    "targetMinutes": 12,
    "chapters": 10,
    "sceneSeconds": 7.0,
    "tone": "energetic but controlled, opinionated, willing to make a call",
    "narrationStyle": "Second person, present tense. Each entry gets the same shape: name it, show why it earns its rank, land one surprising detail, then move. Vary sentence length so the repeated structure does not become a drone.",
    "perspective": "someone who has actually looked at all of these and ranked them",
    "arc": {
      "intro": "State the ranking criterion explicitly — that is the promise. Tease the number one entry by category without naming it. Say how many entries.",
      "early": "The lower entries. Keep these tight; they exist to establish the format and the standard being applied.",
      "middle": "The entries get more space as the rank climbs. Start comparing entries to each other rather than treating each in isolation.",
      "late": "The top three. The number one entry gets roughly double the words of any other, and must justify the tease from the intro.",
      "outro": "Name the entry that just missed the cut and say why. Then the call to action."
    },
    "openLoop": "Tease number one in the intro by describing it obliquely — a category, a number, a consequence — without naming it. Reference the tease once around the halfway mark.",
    "retentionRules": [
      "Count down, never up. The best entry is last.",
      "Every entry must state its rank number out loud so chapter markers line up.",
      "No two entries may open with the same sentence structure.",
      "Each entry needs one detail a viewer would not find in the first search result.",
      "Never pad an entry to hit a word count — cut instead."
    ],
    "hooks": [
      {
        "template": "We ranked every {category} by {criterion}. The order is going to annoy some people.",
        "when": "the ranking is contestable"
      },
      {
        "template": "Number one on this list is not the one you're thinking of. It's not even in the top five most talked about.",
        "when": "the top entry is a genuine surprise"
      },
      {
        "template": "{count} {category}, ranked by {criterion}. The last one is the only one that actually {payoff}.",
        "when": "the top entry has a unique property"
      }
    ],
    "cta": "Ask for the entry the viewer would have ranked first, framed as a genuine disagreement rather than an engagement prompt.",
    "forbiddenPhrases": [
      "in no particular order",
      "you won't believe number one",
      "let's jump right in",
      "without further ado",
      "coming in at number",
      "honorable mention"
    ],
    "voiceName": "Laomedeia",
    "voiceStyle": "Read this as an energetic countdown host — brisk and confident, lifting into each new entry, without shouting",
    "categoryId": "24",
    "titleStyle": "Lead with the number and the category, then the ranking criterion. Keep it under 60 characters so it does not truncate on mobile.",
    "visualStyle": "bright, high-contrast, punchy commercial photography",
    "visualMood": "energetic, clean, saturated",
    "promptSuffix": "high-key commercial photography, 16:9, saturated colour, crisp detail, no text, no watermarks, no logos",
    "subjectsPrefer": [
      "the specific item or place being ranked, shot cleanly",
      "dramatic wide shots that establish scale",
      "detail shots that support the one surprising fact"
    ],
    "subjectsAvoid": [
      "faces",
      "generic filler unrelated to the entry",
      "legible on-screen text or numbers"
    ],
    "burnCaptions": true
  },
  {
    "name": "story",
    "displayName": "Narrative Story",
    "description": "A single story told in acts, with a protagonist, a want, an obstacle, and a cost. Retention comes from narrative tension rather than information density. The longest-watching of the faceless formats when the story actually lands.",
    "targetMinutes": 18,
    "chapters": 5,
    "sceneSeconds": 10.0,
    "tone": "intimate, propulsive, patient with detail",
    "narrationStyle": "Past tense, close third person. Scene before summary — put the viewer in a specific place at a specific moment before explaining anything. Sensory detail over adjectives. Let dialogue do work where the record supports it.",
    "perspective": "a storyteller who knows how it ends and is not telling you yet",
    "arc": {
      "intro": "Open inside a scene, mid-action, with no setup. The viewer should be disoriented for ten seconds and then oriented by a single clarifying sentence. End the intro on the question the whole story answers.",
      "early": "Act one. Establish the protagonist's ordinary world and the specific thing they want. Make the want concrete and small enough to picture.",
      "middle": "Act two. The obstacle arrives and everything that could go wrong does. Raise the stakes by narrowing the options, not by adding events.",
      "late": "Act three. The decision and its cost. This is where the intro's opening scene finally arrives in sequence and is understood.",
      "outro": "The aftermath, quietly. What the protagonist has that they did not before, and what it cost. Then the call to action."
    },
    "openLoop": "The in-media-res cold open is the loop — the viewer watches to find out how that moment happened. Do not explain it until act three.",
    "retentionRules": [
      "Every act must end on a decision made or a door closed, never on a summary.",
      "Introduce no more than four named people across the entire story.",
      "Give one physical detail per scene the viewer can picture exactly.",
      "Never tell the viewer how to feel about an event.",
      "Withhold the protagonist's motivation until it is dramatised, not stated."
    ],
    "hooks": [
      {
        "template": "{time_marker}, {protagonist} was {specific_action}. Eleven minutes later, nothing about {their} life worked the same way.",
        "when": "there is a single pivotal moment"
      },
      {
        "template": "The last thing {protagonist} said before {event} was so ordinary that nobody wrote it down for years.",
        "when": "the story turns on hindsight"
      },
      {
        "template": "This is a story about {want}. It goes somewhere else entirely.",
        "when": "the story subverts its own premise"
      }
    ],
    "cta": "A quiet single line after the story has landed. Never interrupt the aftermath with a request.",
    "forbiddenPhrases": [
      "little did they know",
      "and that's when everything changed",
      "buckle up",
      "you won't believe what happened next",
      "in today's video",
      "fast forward to"
    ],
    "voiceName": "Sulafat",
    "voiceStyle": "Read this as an intimate storyteller — warm, close to the microphone, patient with pauses, letting scenes breathe",
    "categoryId": "24",
    "titleStyle": "Concrete and slightly withholding. Name the person or place, hint at the turn, resolve nothing. No questions.",
    "visualStyle": "narrative cinematography, warm practical light, shallow focus, 35mm feel",
    "visualMood": "intimate, atmospheric, slightly melancholy",
    "promptSuffix": "cinematic film still, 16:9, 35mm, shallow depth of field, practical lighting, no text, no watermarks, no logos",
    "subjectsPrefer": [
      "the specific rooms, streets, and vehicles the scene takes place in",
      "objects the protagonist touched, shot in close-up",
      "weather and time of day matching the emotional beat",
      "empty spaces just after someone has left them"
    ],
    "subjectsAvoid": [
      "faces",
      "identifiable real people",
      "crowds where an individual could be recognised",
      "legible on-screen text"
    ],
    "burnCaptions": false
  },
  {
    "name": "video_essay",
    "displayName": "Video Essay",
    "description": "An argument, not a summary. Stakes a claim in the first minute and spends the rest earning it, including the part where the strongest objection gets taken seriously. Attracts comments and long watch times when the thesis is real.",
    "targetMinutes": 15,
    "chapters": 5,
    "sceneSeconds": 10.0,
    "tone": "thoughtful, precise, willing to be wrong in public",
    "narrationStyle": "First person singular, used sparingly and only for the argument itself. Long-form sentences with real clauses. Name the thing being criticised exactly. No hedging stacks — say the claim, then defend it.",
    "perspective": "someone who has thought about this longer than the viewer has",
    "arc": {
      "intro": "State the thesis in one sentence, early and without hedging. Say what would have to be true for it to be wrong. That is the contract.",
      "early": "Steelman the position being argued against. Make it as strong as its best advocate would, and say plainly what it gets right.",
      "middle": "The evidence. Build the case in escalating order — weakest supporting point first, strongest last, so the argument gains rather than leaks.",
      "late": "The objection you cannot fully answer. Concede it honestly, then show why the thesis survives it anyway. This is what separates an essay from a rant.",
      "outro": "Restate the thesis in its now-earned form — sharper and more qualified than the opening version. Then the call to action."
    },
    "openLoop": "Name the strongest counterargument in the intro and promise to address it directly. Viewers who disagree stay to see whether you actually do.",
    "retentionRules": [
      "Never argue against a position nobody holds.",
      "Every chapter must move the argument, not restate it in new words.",
      "Cite the specific example rather than gesturing at a category.",
      "Concede at least one real point to the other side, unironically.",
      "The conclusion must be narrower than the opening claim, not broader."
    ],
    "hooks": [
      {
        "template": "The standard defence of {subject} rests on one assumption. I think that assumption is false, and here is what follows if it is.",
        "when": "the thesis attacks a premise"
      },
      {
        "template": "I've changed my mind about {subject}. What follows is the argument that changed it, including the part I still can't answer.",
        "when": "the essay is a genuine reversal"
      },
      {
        "template": "{claim}. That's the whole thesis. The next {duration} is me trying to earn it.",
        "when": "the claim is strong enough to stand unadorned"
      }
    ],
    "cta": "Invite the specific disagreement the essay left open, naming the objection you most expect. Genuine, not an engagement prompt.",
    "forbiddenPhrases": [
      "let's unpack that",
      "the discourse",
      "hot take",
      "at the end of the day",
      "in today's video",
      "and that's a problem",
      "let that sink in"
    ],
    "voiceName": "Algieba",
    "voiceStyle": "Read this as a thoughtful essayist — reflective and unhurried, with natural pauses where the argument turns",
    "categoryId": "27",
    "titleStyle": "State the claim. A title that argues something outperforms a title that describes something. No questions unless the essay genuinely answers one.",
    "visualStyle": "contemplative editorial photography, natural light, unhurried framing",
    "visualMood": "reflective, restrained, textural",
    "promptSuffix": "editorial photography, 16:9, natural light, film grain, muted palette, negative space, no text, no watermarks, no logos",
    "subjectsPrefer": [
      "objects and spaces that embody the idea rather than illustrate it",
      "urban and domestic details shot with negative space",
      "textures, materials, and surfaces in close-up",
      "horizons, thresholds, and empty transitional spaces"
    ],
    "subjectsAvoid": [
      "faces",
      "literal one-to-one illustrations of the narration",
      "legible on-screen text",
      "anything that reads as stock footage"
    ],
    "burnCaptions": false
  }
];

export const FORMAT_NAMES = FORMATS.map((f) => f.name);

export function getFormat(name: string): FormatProfile {
  return FORMATS.find((f) => f.name === name) ?? FORMATS[0];
}
