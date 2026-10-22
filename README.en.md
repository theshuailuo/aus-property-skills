# Australian Property AI Skills · aus-property-skills

[中文](README.md) | **English**

The checks and calculations a buyer's agent actually uses, packaged as AI skills you can run on your own computer. One skill per step: before buying, choosing a suburb, due diligence, making an offer, settlement, holding, and selling.

**Made by** Shuai Luo, a Sydney buyer's agent (Avocado Wealth), YouTube 「澳洲罗帅」 <YouTube link TBC>. Each skill comes with a 10–20 minute video explaining how the step is done and the reasoning behind it.

> Have at least A$0.5–1M in cash and planning to buy in Australia? If you'd like our team to run the process for you, [book a free consultation](https://avocadowealth.com.au/free-consultation-team?ref=aus-property-skills).

## The property journey

```mermaid
flowchart LR
  A[Before buying<br/>strategy & money] --> B[Choosing where<br/>& finding property]
  B --> C[Due diligence, valuation, offer<br/>contract, inspection, settlement]
  C --> D[Holding<br/>loans, tax, renting]
  D --> E[Development]
  D --> F[Selling, retirement, estate]
  E --> F
```

## Skills

| Stage | Skill | What it does | Status | Video |
|---|---|---|---|---|
| Due diligence | `auspptdd` | From one address: facts, hazards, planning, comparable sales, price range, red flags | 🔨 in verification | coming |
| Holding | `holiday-home` | Holiday home: buy or book, keep or sell, tax on mixed private and rental use | 🔨 in progress | coming |
| Holding | `hold-or-sell` | Check-up on a property you own: keep or sell, given purchase date, tax changes, loan and cash flow | 🗓 next batch | — |
| Before buying | `family-funding` | Family help: gift, loan, guarantor or joint purchase — terms checklist and risks | 🗓 next batch | — |
| Choosing where | `suburb-owner` / `suburb-investor` | Suburb selection for owner-occupiers / investors | 🗓 next batch | — |
| Offer | `price-guide-offer` | Read the price guide, spot underquoting, set your opening offer and limit | 🗓 next batch | — |

The full plan of 57 skills, in journey order, is in [ROADMAP.md](ROADMAP.md). Skills ship one at a time.

## Install

You need a **coding agent that can run code and reach the internet**, such as Claude Code or Codex CLI. Web chat products (claude.ai, ChatGPT, Gemini) cannot run these skills — we tested: their sandboxes can't fetch official data.

**Option 1: one command**

```bash
npx skills add theshuailuo/aus-property-skills -a claude-code
```

To install one skill, add `--skill holiday-home`. Keep `-a claude-code`: when run inside an agent session without it, the command may install to a folder Claude Code doesn't read.

**Option 2: Claude Code plugin marketplace**

```
/plugin marketplace add theshuailuo/aus-property-skills
/plugin install aus-property-skills@aus-property-skills
```

**Option 3: copy by hand**

```bash
git clone https://github.com/theshuailuo/aus-property-skills.git
cp -r aus-property-skills/skills/holiday-home ~/.claude/skills/
```

On Windows PowerShell: `Copy-Item -Recurse aus-property-skills\skills\holiday-home $HOME\.claude\skills\`. Other agents: copy into the folder that agent reads skills from.

**Updating**: check [VERSIONS.md](VERSIONS.md) and reinstall any skill that is behind. Skills never go online to check for updates during your session.

## Using a skill

Just ask in English or Chinese, for example:

- "Do due diligence on 12 Example St, Newtown NSW 2042"
- "I saw a place in Mudgee — does buying it as a holiday home make sense?"

Reports follow the language you ask in. Only free official public data is used; anything that needs a paid subscription is left blank with the reason — no invented numbers.

**Buyer profile (optional)**: create `.agents/buyer-strategy.md` in your project with your budget, purpose, ownership structure and so on, and skills will tailor their advice; without it they give a neutral view. The file is git-ignored.

**Local extras (optional)**: a `private.local.md` inside a skill folder holds your own extra rules (for example, data sources you subscribe to). The skill reads it first. It is git-ignored too.

## Disclaimer

This is a tool we use in our own property purchases, provided for reference only. Everything here is general information and does not take your personal circumstances into account. For contracts, lending and tax, we recommend consulting a licensed professional; if you decide without professional review, you accept the consequences of that decision. Full wording by topic: [shared/disclaimers.md](shared/disclaimers.md).

## License & feedback

Code and method text are [MIT](LICENSE). The names "Avocado Wealth" and 「澳洲罗帅」 are not covered by MIT — see [TRADEMARK.md](TRADEMARK.md).

Found a problem or want a scenario sooner? Tell us in [Issues](https://github.com/theshuailuo/aus-property-skills/issues) or in the video comments. To contribute, read [CONTRIBUTING.md](CONTRIBUTING.md).
