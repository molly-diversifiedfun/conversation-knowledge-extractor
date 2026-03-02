# funnel-ad-creator Skill Design

## Summary

Single-file Claude Code skill that generates complete ad script bibles for any product funnel. Uses Hormozi Value Equation, Persona x Pain Point matrices, 8 hook categories, and TOFU/MOFU/BOFU/Retargeting architecture. Three-phase workflow: gather context, build persona matrix, generate full storyboarded ad bible with testing protocol. Brand-agnostic; delegates voice to brand-voice-router and humanize-ai-writing.

## Decisions

- **Scope:** Ads only (landing pages are a separate future skill)
- **Architecture:** Single SKILL.md file, no reference files
- **Output:** Full ad bible (12-16 ads) with production-ready storyboards
- **Workflow:** Three-phase (Discovery -> Persona Matrix -> Full Bible)
- **Testing protocol:** Included in output (not separate skill)
- **Voice:** Delegates to brand-voice-router + humanize-ai-writing
- **Product-agnostic:** Works for any product/service

## Trigger Conditions

Activate when user:
- Needs ad scripts for a funnel
- Wants to create video ads (short-form, social)
- Mentions low ad performance or ad fatigue
- Says "ad bible," "hook variations," "funnel ads," "TOFU ads"
- Is launching a product and needs ad creative
- Shares existing ads for improvement

## Process

### Phase 1: Product & Audience Discovery (5 questions, one at a time)

Ask collaboratively with "if stuck" guidance for each:

1. What does your product/service do and what transformation does it deliver?
2. Who are your 2-3 core audience personas? (demographics, psychographics, situation)
3. What are the top 3 pain points for each persona?
4. What proof/results do you have? (testimonials, data, credentials)
5. What's your price point and funnel structure? (what comes before/after)

**Phase 1 Output:** Present a Persona x Pain Point Matrix table for user review:

| Persona | Pain Point | Desired Outcome | Proof Available |
|---------|-----------|-----------------|-----------------|
| [Name] | [Specific pain] | [Transformation] | [Yes/No + type] |

User reviews, edits, approves before Phase 2.

### Phase 2: Hook Bank Generation

Using approved persona matrix, generate 3 hook variations per ad using 8 hook categories:

1. **Callout** — "Hey [persona]..."
2. **Contrast** — "Most [personas] do X. Here's why that's wrong."
3. **Question** — "What if [pain point] wasn't inevitable?"
4. **Myth-Bust** — "You've been told [common belief]. That's a lie."
5. **Story** — "I was [relatable situation]..."
6. **Data** — "[Specific number] of [personas] [surprising stat]."
7. **Identity** — "This is for the [persona] who [specific behavior]."
8. **Absurdist** — Pattern interrupt / unexpected visual or statement.

Present hook selections organized by funnel stage. User reviews and approves.

### Phase 3: Full Ad Bible Generation

Generate 12-16 ads across 4 funnel stages:

**TOFU (4 ads):**
- Goal: Stop scroll, create awareness, identify with pain
- Kill metric: < 25% hook rate
- Structure: Hook (3s) -> Pain agitation (10s) -> Hint at solution (5s) -> Soft CTA
- Length: 15-30 seconds

**MOFU (3 ads):**
- Goal: Build trust, reveal mechanism, show proof
- Kill metric: < 1% CTR
- Structure: Hook (3s) -> Mechanism reveal (15s) -> Proof/testimonial (10s) -> CTA with value
- Length: 30-60 seconds

**BOFU (3 ads):**
- Goal: Overcome final objections, drive purchase
- Kill metric: < 2% conversion
- Structure: Hook (3s) -> Value stack (15s) -> Guarantee (10s) -> Urgency + CTA (5s)
- Length: 30-45 seconds

**Retargeting (3 ads):**
- Goal: Re-engage viewers who didn't convert
- Kill metric: < 3% conversion
- Structure: Hook acknowledging previous touch (3s) -> New angle/proof (15s) -> Time-limited CTA (5s)
- Length: 15-30 seconds

**Each ad includes full storyboard:**

| Time | Visual | Script | Text Overlay |
|------|--------|--------|-------------|
| 0-3s | [Camera/B-roll] | "[Hook line]" | [On-screen text] |
| 3-13s | [Visual direction] | "[Body copy]" | [Key phrase] |

Plus caption/post copy for each ad (hook + body + CTA + hashtags).

**Testing Protocol (4-Week):**
- Week 1: Launch — Deploy 3-4 TOFU ads, test hooks, $5-10/day per ad
- Week 2: Optimize — Kill underperformers, scale winners, launch MOFU
- Week 3: Scale — Full funnel active, optimize by persona
- Week 4: Refresh — Replace fatigued creatives, test new hooks

## Guardrails

- Never fabricate testimonials or results in ad scripts
- Value claims must match user's actual proof
- Each ad targets ONE persona x ONE pain point (no multi-targeting)
- Hook variations must use different hook categories (no 3 callout hooks)
- Storyboard timing must be realistic for platform (15-60 seconds)
- Kill metrics are guidelines, not absolute rules
- Apply brand voice when available (brand-voice-router)
- Humanize all text output (humanize-ai-writing)
- Don't design landing pages (separate skill)
- Don't write email sequences or build funnels

## What This Skill Does NOT Do

- Design landing pages (separate future skill)
- Write email sequences or automations
- Set up ad platform campaigns (Meta, TikTok, YouTube)
- Create the video content itself
- Build payment/checkout flows

## Source Knowledge

Extracted from conversations:
- "Viral sales funnel ads with AI avatars" (94e201ee) — primary source

Key frameworks: Hormozi Value Equation, Hook-Story-Offer (HSO), Persona x Pain Matrix, Funnel Stage Architecture (TOFU/MOFU/BOFU/Retargeting), Visual Intensity Escalation, Hook Bank Categories (8 types), 4-Week Testing Protocol, Contrast Accessibility Rules.
