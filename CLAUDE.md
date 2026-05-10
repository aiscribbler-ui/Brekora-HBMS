
## Skill routing

When the user's request matches an available skill, invoke it via the Skill tool. When in doubt, invoke the skill.

Key routing rules:
- Product ideas/brainstorming → invoke /office-hours
- Strategy/scope → invoke /plan-ceo-review
- Architecture → invoke /plan-eng-review
- Design system/plan review → invoke /design-consultation or /plan-design-review
- Full review pipeline → invoke /autoplan
- Bugs/errors → invoke /investigate
- QA/testing site behavior → invoke /qa or /qa-only
- Code review/diff check → invoke /review
- Visual polish → invoke /design-review
- Ship/deploy/PR → invoke /ship or /land-and-deploy
- Save progress → invoke /context-save
- Resume context → invoke /context-restore

## Design system

See `DESIGN.md` for the full specification. Quick reference:

- **Display font**: Playfair Display (editorial headlines, marketing)
- **UI font**: Manrope (navigation, buttons, tables, dashboards)
- **Primary color**: `brand-600` (#026ba0) — teal/ocean
- **Accent**: `secondary` (#c27d3a) — warm gold
- **Gray text floor**: `gray-400` (#6b7280) for WCAG AA on white
- **Dark mode**: `class`-based toggle, lighter brand tones in dark
- **Radius**: 8px default (md), 12px for cards (lg)
- **Shadows**: warm-tinted, low-opacity for subtle depth
