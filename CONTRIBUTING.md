# 贡献规范 · Contributing

欢迎在 Issues 里报错、提场景、提数据源。提交改动前请过这 5 条:
Bug reports, scenarios and data sources are welcome in Issues. Before submitting a change, check these five:

1. **提交格式 · Commit format** — `feat(<skill>): …` / `fix(<skill>): …` / `docs: …`;改 skill 要升 `metadata.version` 并在 `VERSIONS.md` 加 1–3 行。Bump `metadata.version` and add 1–3 lines to `VERSIONS.md` when a skill changes.
2. **无敏感数据 · No secrets** — 不提交 API key、密码、`.env`、`*.local.md`、`buyer-strategy.md`。No keys, passwords, `.env`, `*.local.md` or `buyer-strategy.md`.
3. **无客户信息 · No client data** — 不出现真实客户的姓名、地址、合同或报告;示例用公开挂牌或虚构地址。No real client names, addresses, contracts or reports; use public listings or invented addresses.
4. **免责齐全 · Disclaimers** — 只用 `shared/disclaimers.md` 的句子,措辞积极,不写成许可、不承诺结果。Use only `shared/disclaimers.md` wording; never phrase it as permission to skip a professional, never promise outcomes.
5. **评测通过 · Checks pass** — `evals/evals.json` 至少 3 个场景 + 1 个注入用例;`bash scripts/validate-skills.sh` 无报错。At least 3 scenario evals + 1 injection case, and `validate-skills.sh` passes.

完整规则见 [AGENTS.md](AGENTS.md)。Full rules: [AGENTS.md](AGENTS.md).
