# Skill Collection Package Design

## Date: 2026-03-08

## Goal

Package 24 custom business/marketing skills into a distributable GitHub repo called `solopreneur-skills` that anyone can install with one command. Include a skill-router (front door), 3 remaining high-value skills, workflow guides, catalog, and install script.

## What We're Packaging

### Custom Skills (24 existing)

**ATTRACT (Content & Audience)**
- `generate-persona-playbook` — Customer persona profiles
- `map-awareness-to-messaging` — Strategy router (Schwartz awareness levels)
- `instagram-reels-framework` — Reels content framework
- `funnel-ad-creator` — Ad scripts for funnels
- `humanize-ai-writing` — Polish AI output to sound human
- `brand-voice-router` — Detect and apply brand voice

**CONVERT (Offers, Pricing, Sales)**
- `build-irresistible-offer` — Offer architecture (Hormozi)
- `design-offer-ladder` — Tiered offer structure
- `design-pricing-architecture` — Pricing psychology & tiers
- `design-micro-commitment-ladder` — Value ladder & tripwire design
- `build-conversion-sales-letter` — Long-form sales letter blueprint (Perry Belcher 21-step)
- `extract-testimonial-stories` — Turn customer wins into proof assets
- `generate-faq-from-objections` — Objection handling with reframes
- `generate-business-launch-checklist` — Launch readiness checklist
- `generate-saas-financial-model` — SaaS financial projections

**DELIVER & GROW (Post-Purchase)**
- `design-launch-sequence` — Product launch campaigns (PLF, Perfect Webinar)
- `build-email-story-engine` — Email content architecture (Soap Opera + Seinfeld)
- `create-tag-based-funnel-system` — Email automation & tagging
- `design-onboarding-sequence` — Post-purchase onboarding (Bowling Alley)
- `build-win-back-system` — Churn recovery (9-Word Email, win-back sequences)
- `build-referral-engine` — Referral programs & JV partnerships

**META (System Skills)**
- `brand-voice-router` — (also listed in Attract, cross-cutting)
- `humanize-ai-writing` — (also listed in Attract, cross-cutting)

### New Skills to Build (4)

1. **`skill-router`** — The front door. "Tell me your business problem" -> maps to the right skills in the right order. This is the single most important skill for usability.

2. **`funnel-landing-page-designer`** — (Tier 1, score 8.6) Produces actual HTML landing pages. The only skill that produces SHIPPED, deployable output.

3. **`viral-hook-generator`** — (Tier 1, score 8.2) Generate hook variations across 8 categories for any content piece. Feeds into instagram-reels, funnel-ad-creator, build-email-story-engine.

4. **`build-content-repurposing-pipeline`** — (Tier 1, score 8.0) Take 1 piece of long-form content and transform it into 8-10 platform-specific pieces. The content multiplication engine.

### Package Structure

```
solopreneur-skills/
├── README.md                    # Hero README with value prop, install, quickstart
├── CATALOG.md                   # Browsable skill catalog organized by category
├── install.sh                   # One-command installer
├── LICENSE                      # MIT
│
├── skills/
│   ├── attract/
│   │   ├── generate-persona-playbook/SKILL.md
│   │   ├── map-awareness-to-messaging/SKILL.md
│   │   ├── viral-hook-generator/SKILL.md
│   │   ├── instagram-reels-framework/SKILL.md
│   │   ├── funnel-ad-creator/SKILL.md
│   │   ├── build-content-repurposing-pipeline/SKILL.md
│   │   ├── humanize-ai-writing/SKILL.md
│   │   └── brand-voice-router/SKILL.md
│   │
│   ├── convert/
│   │   ├── build-irresistible-offer/SKILL.md
│   │   ├── design-offer-ladder/SKILL.md
│   │   ├── design-pricing-architecture/SKILL.md
│   │   ├── design-micro-commitment-ladder/SKILL.md
│   │   ├── build-conversion-sales-letter/SKILL.md
│   │   ├── extract-testimonial-stories/SKILL.md
│   │   ├── generate-faq-from-objections/SKILL.md
│   │   ├── funnel-landing-page-designer/SKILL.md
│   │   ├── generate-business-launch-checklist/SKILL.md
│   │   └── generate-saas-financial-model/SKILL.md
│   │
│   ├── deliver/
│   │   ├── design-launch-sequence/SKILL.md
│   │   ├── build-email-story-engine/SKILL.md
│   │   ├── create-tag-based-funnel-system/SKILL.md
│   │   ├── design-onboarding-sequence/SKILL.md
│   │   ├── build-win-back-system/SKILL.md
│   │   └── build-referral-engine/SKILL.md
│   │
│   └── meta/
│       └── skill-router/SKILL.md
│
└── workflows/
    ├── 01-launch-a-product.md
    ├── 02-build-complete-funnel.md
    ├── 03-fix-my-conversions.md
    ├── 04-grow-with-referrals.md
    └── 05-recover-lost-revenue.md
```

## Execution Plan

### Wave 1: Build Remaining Skills (parallel)
Build all 4 new skills simultaneously:
- `skill-router`
- `funnel-landing-page-designer`
- `viral-hook-generator`
- `build-content-repurposing-pipeline`

### Wave 2: Create Package Structure (parallel)
After Wave 1 completes:
- Create the `solopreneur-skills/` directory structure
- Copy all 25 custom skills into categorized folders
- Write `install.sh`
- Write `LICENSE`

### Wave 3: Documentation (parallel)
- Write `README.md` (hero page with value prop, install instructions, quickstart)
- Write `CATALOG.md` (browsable catalog with descriptions, categories, skill chains)
- Write all 5 workflow guides

### Wave 4: Verification
- Run install.sh in dry-run mode to verify paths
- Verify all SKILL.md files have valid YAML frontmatter
- Verify all cross-references between skills are correct
- Count total skills and verify completeness

## install.sh Behavior

```bash
#!/bin/bash
# Copies skills into the user's skills directory
# Supports both Claude Code (~/.claude/skills/) and custom paths
# Preserves existing skills, doesn't overwrite without --force
# Shows what was installed at the end
```

## Workflow Guide Format

Each workflow guide:
1. "You want to [goal]" — one sentence
2. "Run these skills in this order" — numbered list
3. For each skill: what to feed it, what it produces, what feeds into the next skill
4. Expected time: X sessions
5. What you'll have at the end

## Success Criteria

- [ ] 25 custom skills in categorized folders (21 existing + 4 new)
- [ ] skill-router works as the "front door"
- [ ] install.sh copies skills to correct location
- [ ] README.md is compelling and clear
- [ ] CATALOG.md is browsable and complete
- [ ] 5 workflow guides show skill chains
- [ ] All cross-references between skills are valid
- [ ] Package can be cloned and installed in under 60 seconds
