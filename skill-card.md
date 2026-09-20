## Description

**WCAG Accessibility** guides AI agents and developers to build, audit, and repair web content against WCAG 2.2, including AAA-oriented evidence collection and mandatory human testing.

This skill is ready for commercial and non-commercial use when its documented validation and human-review requirements are followed.

## Owner

[Turbolego](https://github.com/turbolego) is accountable for maintenance and release review.

## License/Terms of Use

[MIT License](LICENSE).

## Use Case

Use this skill when creating accessible HTML/CSS/JavaScript, remediating accessibility defects, running reproducible audits, preparing WCAG 2.2 AAA evidence, or running the optional AI-WCAG-Gauntlet benchmark. It is intended for developers, accessibility practitioners, and AI coding agents working on web content.

## Deployment Geography for Use

Global. Review local accessibility, privacy, procurement, and regulatory requirements before deployment.

## Requirements / Dependencies

**Requires API Key or External Credential:** No, for the published skill.  
**Credential Type(s):** None. `CLAWHUB_TOKEN` is used only by this repository's own release tooling (`scripts/publish-web.py`), which is excluded from the published skill bundle via `.clawhubignore` and is never installed alongside the skill.

The reproducible automated audit route requires Node.js, npm, Python 3, curl, Java, a Chromium-family browser with matching Chromedriver, and the declared `@axe-core/cli`, `pa11y`, `@qualweb/cli`, and `vnu-jar` packages. Do not include secrets in prompts, reports, commits, or other output. Use least-privilege credentials and rotate them as appropriate.

## Known Risks and Mitigations

| Risk | Mitigation |
|---|---|
| Automated accessibility tools can miss defects or return findings that require judgement; clean reports do not prove WCAG conformance. | Treat automated output as evidence only. Review every warning, `incomplete`, and `cantTell` result, then complete the evidence matrix and mandatory human-test protocol before claiming AA or AAA conformance. |
| Browser-based audits fetch target pages and may write page content or audit data into local report artifacts. | Run audits only against intended targets, write reports to approved locations, and review report contents before sharing or publishing them. |
| Suggested remediation can change application source and may be incorrect for the product, framework, or user workflow. | Review code diffs, exercise affected states with users and assistive technology, and deploy only through the organization’s normal change-control process. |
| `scripts/publish-web.py` (repository release tooling, not part of the published skill) can upload this repository to ClawHub when supplied with a deployment credential. | The file is excluded from the published skill bundle via `.clawhubignore`. Maintainers only: run it with `--dry-run` first, safeguard `CLAWHUB_TOKEN`, and review the package manifest before uploading. |

## References

- [Project source and release history](https://github.com/turbolego/wcag-skill)
- [WCAG 2.2 Quick Reference](https://www.w3.org/WAI/WCAG22/quickref/)
- [W3C WCAG 2.2 Recommendation](https://www.w3.org/TR/WCAG22/)
- [NVIDIA: Write Skill Cards People Can Trust](https://docs.nvidia.com/skills/skill-cards)
- [Repository smoke-test workflow](https://github.com/turbolego/wcag-skill/actions/workflows/smoke-test.yml)
- [`references/validator-workflow.md`](references/validator-workflow.md)
- [`references/aaa-evidence-matrix.md`](references/aaa-evidence-matrix.md)
- [`references/manual-test-protocol.md`](references/manual-test-protocol.md)

## Skill Output

**Output Type(s):** Accessibility guidance, remediation recommendations and code, audit reports, evidence records, and benchmark results when explicitly requested.  
**Output Format:** Markdown, source files, shell commands, JSON reports from axe/Pa11y/QualWeb/Nu, and an evidence-matrix table.  
**Output Parameters:** Target route or HTTP URL, report directory, requested WCAG conformance level, relevant application states, and applicable success-criterion scope.  
**Other Properties Related to Output:** The audit wrapper writes `axe_report.json`, `pa11y_report.json`, `qualweb_report.json`, `w3c_source_html_report.json` (raw-HTTP-response scope only, not the rendered DOM), and a fetched HTML snapshot to the chosen report directory. Agents must describe actual tested scope and residual limitations rather than make unsupported conformance claims.

## Skill Version

2.0.5 (source: `SKILL.md` metadata; release evidence is maintained in the source repository and its CI workflows).

## Ethical Considerations

Accessibility guidance should support disabled people without overstating certainty. Human review is required for conformance claims, complex interaction patterns, media, authentication, third-party components, and real-world usability. Users remain responsible for legal, contractual, privacy, security, and accessibility obligations in their deployment context.
