# build-irresistible-offer Skill Design

## Summary

Single-file Claude Code skill that builds high-converting offers using the Irresistible Offer Formula. Brand-agnostic — works for any product/service. Pairs with brand-voice-router for voice and humanize-ai-writing for output quality.

## Decisions

- **Scope:** Brand-agnostic (not Unstuck-specific)
- **Output:** Structured markdown document (7 sections)
- **Input:** 8 Offer Clarity Questions asked one at a time, with collaborative help if user gets stuck
- **DM scripts:** Separate future skill (not included)
- **Architecture:** Single SKILL.md file, no reference files
- **Voice:** Delegates to brand-voice-router + humanize-ai-writing

## Trigger Conditions

Activate when user:
- Wants to create, rebuild, or improve a paid offer
- Mentions low conversion rates or pricing strategy
- Says "make my offer better," "value stack," "guarantee structure"
- Is launching a new product/service
- Shares an existing offer for evaluation

## Process

### Phase 1: Offer Clarity Questions (collaborative)

Ask these one at a time. If user is stuck, help them work through it with suggestions, examples, or reframed questions. Never leave a question blank — note gaps in Section 7.

1. What specific transformation does the client achieve?
2. How fast do they get there?
3. What makes them certain it'll work?
4. What risk are they taking?
5. Why should they act now vs later?
6. What proof exists?
7. Who is this NOT for?
8. What's the price and what tier does this sit in?

### Phase 2: Generate Blueprint

Produce a structured document with 7 sections:

1. **Offer Formula Score** — (Dream Outcome x Speed x Certainty) / Risk. Rate each 1-10, show the math, identify weakest lever.
2. **Value Stack** — Table: component, market-rate value with justification, total. Target 3-5x ratio to price.
3. **Named IP** — Transform generic components into named intellectual property. "The [Name] + TM," memorable, implies mechanism.
4. **Guarantee + Anti-Guarantee** — Positive outcome promise + 3-7 binary, trackable conditions. State consequence if conditions met but outcome not achieved.
5. **Urgency Mechanics** — Fast action bonus (high value, low fulfillment cost) + decision window + real scarcity only.
6. **Selling Statements** — 3-5 one-paragraph descriptions for: sales page hero, email pitch, DM intro, ad copy, conversation explanation.
7. **Offer Gaps & Recommendations** — Missing proof, ladder gaps, weak levers, enforcement concerns.

## Guardrails

- Never fabricate proof, testimonials, or results
- Value stack amounts must have market-rate justification
- Anti-guarantee conditions must be binary and trackable
- If brand-voice-router active, apply voice to selling statements
- All text output run through humanize-ai-writing
- Don't include DM scripts or sales page design

## Source Knowledge

Extracted from conversations:
- "Creating an irresistible offer" (765d975b) — primary source
- "Finding your niche" — 4-layer objection structure, forbidden words
- "Decide Already tripwire product launch" — offer ladder, Kit Commerce
- "Reviewing an 18-month growth plan" — product ladder gaps
- "Building a $10 million digital product launch" — value stacking at scale

Key frameworks: Irresistible Offer Formula, Value Stack Architecture, Guarantee + Anti-Guarantee Structure, Named IP Transformation, Fast Action Bonus pattern.
