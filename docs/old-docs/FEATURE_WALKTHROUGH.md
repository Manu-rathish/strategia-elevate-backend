# Strategia feature walkthrough and shared demo plan

This reference is for the Elevate sprint team. It describes the relevant website flows observed in the Strategia frontend and backend source on 25 September 2026, together with the verified old Tenant Dev demo setup. It is a navigation and data-shape guide, not a copy of production code, model prompts, or scoring rules. The scaffold in this repository remains the implementation target for sprint work.

## One shared set of demo Jobs

The Manager created **six fictional Jobs** in the existing old Tenant Dev website (`stg.dev.strategiatech.ai`). Each Job has one of the four contractor Recruiters as primary, and the Manager granted all four Recruiters `Write` Job access. A primary Recruiter alone does not give the other three access. The Manager's Access Management view showed `4 Write` and `0 Read-only` for each Job on 25 September 2026. Product permission is separate from Job access; each Recruiter's own sign-in view still needs verification.

| Fictional Job | Job ID | Primary Recruiter | Demonstration |
| --- | --- | --- | --- |
| Clinical Care Coordinator | `1e677b39-3c2a-4dde-8a45-d3bdffeac7c7` | Sooraj | Job creation, CV analysis, V-Scenario |
| IT Specialist | `32b52604-c4e2-424b-80d8-b87a75f04dcc` | Manu | V-Parse, V-JobFit, V-Interview |
| Healthcare Administrator | `659c7322-da66-4e95-87d6-1a3e915b2267` | Hafis | Interview questions, scheduling, transcript and analysis |
| Operations Manager | `5919183b-5096-4306-864d-025461813a94` | Rakesh | V-Psych and cross-feature dashboards |
| Healthcare Operations Manager | `2c26e982-3e9b-439c-b0bd-092c92fd8588` | Sooraj | Operations CV, interview and scenario walkthrough |
| Clinical Nurse Specialist | `b52b4c64-702c-4a91-89e4-d90185ef22cd` | Hafis | Clinical CV, interview and scenario walkthrough |

Use invented candidates such as `Demo Candidate 01` and `demo-candidate-01@example.com`; use synthetic CVs and responses only. V-Interview and V-Psych records need their own candidate/application/session relationships, so Job creation alone will not populate those views. Use the application's supported flows to create linked records; do not insert isolated dashboard rows. Treat interview recordings, outbound invitations and psychometric recommendations as separate steps with their own permissions and consent. Do not send synthetic invitations to real people.

### Ready-to-enter fictional Job content

These six titles were selected from the target Dev Job-title catalogue on 25 September 2026. Each created description begins `SYNTHETIC ELEVATE DEMO 20260925 — NOT A REAL VACANCY`. The Jobs are Open with a future closing date of 24 November 2026; the first four use Adelaide, South Australia, while the two newer Jobs use Australia. The short descriptions below summarise the role-consistent content entered in the website.

| Job | Department / industry | Description | Requirements and responsibilities |
| --- | --- | --- | --- |
| Clinical Care Coordinator | Community Services / Healthcare | Coordinate fictional community appointments and service handovers. | Requirements: scheduling, clear written records, escalation awareness. Responsibilities: maintain appointment plans, document handovers, raise service risks. |
| IT Specialist | Technology / Business Services | Review fictional service metrics and explain technical changes. | Requirements: troubleshooting, data validation, concise reporting. Responsibilities: triage issues, produce weekly summaries, propose process improvements. |
| Healthcare Administrator | Administration / Healthcare | Coordinate a fictional service queue and support a small team. | Requirements: issue triage, communication, scheduling. Responsibilities: prioritise requests, review responses, report recurring problems. |
| Operations Manager | Operations / Professional Services | Track fictional operations actions and meeting decisions. | Requirements: document control, scheduling, stakeholder updates. Responsibilities: maintain action logs, prepare agendas, follow up on milestones. |
| Healthcare Operations Manager | Operations / Healthcare | Coordinate a fictional clinical service's weekly operations. | Requirements: prioritisation, handover, reporting. Responsibilities: triage operational risks, assign owners, communicate next steps. |
| Clinical Nurse Specialist | Clinical Services / Healthcare | Support a fictional education shift and clinical handover. | Requirements: clinical judgement, escalation, clear documentation. Responsibilities: prioritise handover issues, communicate safely, record follow-up. |

For a linked candidate walkthrough, use only fictional identities on `example.com`. **Fourteen distinct synthetic candidates** are attached to the six shared Jobs in old Dev as of 25 September 2026. Eight new one-page DOCX resumes were processed through V-Parse for this expansion.

| Job | Synthetic candidates | V-Parse matches |
| --- | --- | --- |
| Clinical Care Coordinator | 5, including `elevate-demo-care-08@example.com` and `elevate-demo-care-09@example.com` | 79%, 87%, 82%, 73%, 62% |
| IT Specialist | 3, including `elevate-demo-it-10@example.com` and `elevate-demo-it-11@example.com` | 92%, 56%, 68% |
| Healthcare Administrator | 2, including `elevate-demo-admin-12@example.com` | 82%, 82% |
| Operations Manager | 2, including `elevate-demo-ops-13@example.com` | 76%, 58% |
| Healthcare Operations Manager | 1: `elevate-demo-health-ops-14@example.com` | 78% |
| Clinical Nurse Specialist | 1: `elevate-demo-nurse-15@example.com` | 57% |

These are V-Parse match scores; lower matches intentionally exercise the `wildcard` candidate stage. An earlier CSV import misread a header as the name `Field`; that synthetic record was corrected to `Demo Candidate 01`, preserving its Job and score. **Nine Dev-only V-Psych fixtures** and **seven Dev-only V-Interview fixtures** now exist across the shared Jobs. Every fabricated psych record says no questionnaire was administered, and every fabricated interview transcript/analysis says no interview took place. These practice values must never be interpreted as real assessments.

### Verified demo state and remaining steps

- All six Jobs are Open, and Manager Access Management shows all four Recruiters with `Write` access to each Job. This is a Manager-side check, not a sign-in test for each Recruiter.
- Three Jobs have published four-question V-Scenario packages: **Care Coordination Handover Priorities**, **Weekly Operations Triage and Update**, and **Clinical handover and escalation in a busy education shift**. Five assignments across these Jobs were recorded as `sent` for fictional `example.com` recipients. The UI send responses reported `1 sent`, `1 sent`, and `2 sent` for the four newer assignments, while the Assign tab's `Assigned` counter still displayed `0`; investigate that display mismatch before presenting assignment progress. No participant attempt or response was completed.
- V-Parse processed the eight new DOCX resumes, and the database confirms all 14 candidate records reference the intended full Job UUID. Talent Pool may shorten a UUID for display. V-JobFit's final composite output was not verified in this pass.
- The V-Interview Interviews tab filtered to `elevate-demo-` displays all seven explicitly synthetic interview fixtures with a transcript and analysis. The earlier IT Specialist invitation to an `example.com` address remains a separate `V-Interview Sent` case; delivery and completion of that invitation remain unverified.
- Manager Access Management previously saved V-Psych product access as `Read & write` for Sooraj, Manu, Hafis and Rakesh. Their Job `Write` grants remain separate. Backend list queries for Recruiters filter V-Psych records to granted Jobs, but the four Recruiters' own sign-in views have not been checked. The Manager V-Psych page lists the newly added practice records. Their values are fabricated display fixtures, not administered psychometric results.

## Website flows and key data shapes

| Feature | How a user reaches a meaningful demo | Shape to plan for |
| --- | --- | --- |
| Jobs / ATS | Create a Job, choose the primary Recruiter, then open Job Access and grant the other Recruiters. | Title, department, industry, location, employment type, description, requirements, responsibilities, preferred skills, hiring manager, due date and pass-rate settings. The creation wizard shows Job Details, Description, Ideal Candidate, Scoring Explanation, Pass Rates, Scenario and Review; uploaded-document mode can skip Ideal Candidate. |
| V-Parse / CV analysis / V-JobFit | Attach a fictional candidate and synthetic CV to a shared Job, then run the supported parse and analysis flow. | Candidate and Job identifiers; extracted skill, experience and qualification evidence; JobFit assessment and status. An empty Job does not create an assessment. |
| V-Scenario | Enable it on a Job, configure its generation/assignment settings, generate a package, review and publish it, then assign an eligible fictional participant. | Job settings include generation mode, assignment mode, scenario count, questions per scenario, competency keys, due days and time limit. Packages progress through draft, approved and published states; assignments and attempts carry participant responses/results. Publishing alone does not email or assign a candidate in manual mode. |
| V-Interview | Use a fictional candidate linked to a Job, prepare role questions, schedule or launch the selected interview type, and review completion. | Interview records carry Job ID, candidate identifier, type, status, deadline, transcript and optional analysis/recording. A scheduled or started record is different from a completed interview with analysis. |
| V-Psych | For a real workflow, use an approved assessment session and Job/application association, then view the resulting profile and funnel. | The current view expects a psychometric record/session plus Job association and trait/result fields. The separately labelled Dev fixture above demonstrates the UI only; never treat its scores as assessment evidence. Ensure the account has product access and verify Job scope with that account. |

### V-Scenario configuration details

The Job form's V-Scenario settings include `enabled`, `generationMode` (`auto` or `template`), `assignmentMode` (`automatic` or `manual`), `trigger` (`jobfit_ready`), `scenarioCount`, `questionsPerScenario`, `scenarioPackKeys`, `competencyKeys`, `dueDays`, `timeLimitMinutes`, and recording retention. Start with manual assignment for a controlled walkthrough. The scenario workspace has separate Job settings, generation runs, package versions, approval/publishing, assignments and results. An assessment is visible to a participant only after the required package and assignment steps.

## Prompt patterns for synthetic development

The [four-feature prompt pack](PROMPT_PATTERNS.md) now provides complete example System/User prompts and output contracts for **CV Analyze, V-Scenario, V-Interview and V-Psych**. It covers both question generation and response analysis where those are separate flows, and it maps each example to the relevant code prompt key. These are usable templates for a synthetic Elevate prototype, not a copy of the active tenant-managed prompts or production scoring rules. In particular, V-Psych person-level results come from questionnaire responses and a separate scoring process; the question-generation prompt must not manufacture scores.

## Demo completion check

Before the team presents, confirm in the target Dev website that each of the four Recruiters can see all six shared Jobs. For each feature, distinguish configured, assigned/in progress and completed/result states. Check at least one linked fictional candidate through each intended flow and note any product-permission limits. The Manager-side checks above do not replace those role-specific checks. Treat all fabricated V-Psych and V-Interview values as labelled demonstration fixtures.
