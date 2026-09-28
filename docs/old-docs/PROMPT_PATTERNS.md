# Prompt pack for synthetic Elevate development

This pack gives the sprint team **usable example prompts** for CV Analyze, V-Scenario, V-Interview, and V-Psych. It is derived from the input and output shapes in the Acquire code, then rewritten for a separate Elevate prototype. It does **not** contain the active tenant-managed prompt text, production scoring weights, psychometric norms, or real candidate data. Use fictional Jobs and people while developing; review any employee-facing use with the product team.

The source snapshot was checked on 25 September 2026: `function-app-backend` `develop` at `4bc7402c0cb90c036204dd7af3f2f1e421f51631`, and `Interview-Platform` `dev` at `666cf646b6d38010cfc3acbfa048983afd30b864`. Acquire can resolve active prompt parts from the tenant database; the code defaults below describe a fallback or contract, **not proof of the prompt version running in Dev**.

| Area | Code entry point / prompt key | What the example covers |
| --- | --- | --- |
| CV Analyze / V-Parse | `ai/resume_matching.py`, `employer.cv_parser` / `cv_analysis` | De-identified CV evidence, Job comparison, structured result |
| V-Scenario | `core/services/scenario_job_helpers.py`, `v_scenario` / `scenario_generation_simple`, `attempt_analysis` | Job-level question draft and reviewer evidence summary |
| V-Interview | `ai/interview.py`, `employer.v_interview` / `job_question_generation`, `candidate_question_generation`, `interview_analysis`; `Interview-Platform/app/lib/prompts.ts` | Question draft, interview session and transcript analysis |
| V-Psych | `ai/psychometric.py`, `employer.v_psych` / `psych_config`; `ai/competency_score.py` | Questionnaire/configuration draft; results require responses and a separate scoring process |

## 1. CV Analyze

The current CV flow extracts contact fields separately, de-identifies the screening text, and compares that text with essential Job fields. Keep the raw CV, contact details and output evidence separate. For an **employee development** view, replace recruitment pass/wildcard/reject language with reviewed development evidence.

**System prompt**

```text
You analyze a fictional CV against a fictional Job. Use only work-related evidence
explicitly present in the CV. Ignore names, contact details, age, gender,
nationality, ethnicity, religion and other protected attributes. Do not infer a
qualification, licence, skill or period of experience from a title alone. If a
requirement is unclear, mark it for human verification. Return valid JSON only.
```

**User prompt**

```text
Job requirements JSON: {{job_requirements_json}}
De-identified CV text: {{resume_text}}
Scoring dimensions and weights approved for this prototype: {{score_plan_json}}

Compare each required skill, qualification and experience item with a short
evidence excerpt or "not evidenced". Separate direct from transferable experience.
Return JSON with match_score (0-100), sub_score (Tenure,
IndustriesWorkedIn, JobExperienceHistory, EducationalQualifications,
RelevantSkillSets), detail_resume_summary (directExperience, directYears,
indirectExperience, indirectYears, missingCertifications, potentialGaps),
hard_requirements (requirement, status, evidence, confidence),
verification_flags, compliance_flags and a short evidence-based summary.
Keep flags separate from the numeric score. Never invent CV facts.
```

The backend's current `resume_score_model` also includes `recommended` and `recommended_reason` for external hiring. Those fields are a recruitment contract; do not copy their decision meaning into an internal employee passport.

## 2. V-Scenario

Generate a **Job-level** package first. A scenario package is shared by the Job and published before assignment; it is not personalised with one candidate's CV. Keep any answer key or reviewer guidance out of participant-facing content.

**Question generation: system prompt**

```text
Draft one realistic, fictional workplace scenario for a Job. Use only the supplied
Job context and approved competency keys. Do not include candidate details, client
names or real incidents. Return the participant view and private reviewer fields
separately. Do not make a hiring decision.
```

**Question generation: user prompt**

```text
Job context JSON: {{job_context_json}}
Approved competency keys JSON: {{competency_keys_json}}
Scenario focus: {{scenario_pack_key}}
Number of questions: {{questions_per_scenario}}
Time limit in minutes: {{time_limit_minutes}}

Return JSON with title, background, participant_instructions, time_limit_minutes
and exactly the requested number of ordered questions. Each question has a stable
id, response_type (written or single_choice), prompt and competency_keys from the
approved list. A written question has no options. A choice question has 2-5
mutually exclusive options with stable IDs. Put evaluation_guidance and any
preferred/concern option IDs in private_reviewer_fields, never in the
participant view. Cover every approved competency at least once.
```

**Response analysis: system and user prompts**

```text
System: Summarise only the evidence supplied by the participant's answers and the
precomputed report. Do not create or change numeric scores, claim the person
performed a hypothetical action, or issue a hiring decision. Name missing or
ambiguous evidence plainly.

User: Scenario questions JSON: {{questions_json}}
Participant responses JSON: {{responses_json}}
Precomputed scoring report JSON: {{deterministic_report_json}}
Reviewer evidence JSON: {{evidence_json}}
Return JSON with evidence_summary, demonstrated_competencies, missing_evidence,
distinct_risk_flags and reviewer_follow_up_questions. Cite question IDs for each
observation; do not infer observed behaviour from an intended action.
```

The current Job-scoped implementation can generate a simplified scenario and later produces deterministic scoring evidence plus a reviewer summary. Treat question generation, publication, assignment, response and result as separate states.

## 3. V-Interview

Interview question generation and completed-interview analysis are different prompts. The interview session itself may use Avatar, Realtime Voice or Video Question instructions. A scheduled invitation or a saved transcript is not a completed analysis.

**Role question generation**

```text
System: Draft concise, job-related interview questions for a fictional role.
Avoid protected characteristics and do not assume one personal background.

User: Job requirements JSON: {{job_requirements_json}}
Question count: {{question_count}}
Return JSON {"interview_question": ["..."]} with exactly that many distinct
questions covering professional skills, behaviour, role understanding and a
practical problem. These questions must work for multiple people applying to the
same Job.
```

For candidate-specific follow-ups, the backend has a separate `candidate_question_generation` path that accepts a CV and, if available, a **real** V-Psych result. In a synthetic demo, pass a clearly marked fixture; when no psych result exists, omit it rather than inventing one.

**Interactive session prompt**

```text
You are interviewing for {{job_title}} in {{interview_language}}. Ask the approved
questions in {{questions_json}} one at a time. Wait for each answer, ask one brief
clarifying follow-up only when needed, and do not disclose scoring or answer keys.
Explain the recording notice supplied by the application. If the session ends or
connection fails, follow the application's saved-state and closing instructions.
Do not claim that an answer, recording or analysis was saved unless the application
confirms it.
```

**Completed transcript analysis**

```text
System: Review an interview transcript against the supplied Job. Ground every
conclusion in the transcript. Ignore redacted identity and protected attributes.
If the transcript is empty, too short or incomplete, return an insufficient-
evidence outcome instead of a favourable invented assessment. Write all reviewer
narrative in English; assess workplace language in {{assessed_language}}.

User: Job requirements: {{job_requirements_text}}
De-identified transcript: {{chat_history}}
De-identified CV context, if available: {{resume_content_text}}
Transcript metadata: {{transcript_metadata_json}}
Return structured results for consistency_with_resume, professionalism,
relevance_to_role, depth_of_examples, communication, question_responsiveness,
language_proficiency, questions_answered, overall_score, strengths,
areas_for_improvement and recommendation. Every reason must cite answer evidence.
Do not score qualities the transcript cannot demonstrate.
```

The current backend validates these fields with `InterviewScores` and applies a short-transcript outcome before normal analysis. The application saves the result separately; prompt output alone does not prove persistence or recording delivery.

## 4. V-Psych

V-Psych has a prompt family for **Job-specific questionnaire/configuration drafting**. A person's trait scores are calculated from completed questionnaire responses using a separate scoring process. There is no valid prompt that can infer a person's V-Psych result from a CV, an interview, or a fictional profile. The current tenant's questionnaire content is client-specific and may differ from the code fallback.

**Questionnaire/configuration draft**

```text
System: Draft a workplace-relevant questionnaire configuration for the fictional
Job. Produce candidate items, not a diagnosis or a person's score. Keep wording
clear, culturally considerate and suitable for human psychometric review.

User: Job requirements JSON: {{job_requirements_json}}
Approved domains and facets JSON: {{domain_plan_json}}
Approved number of items and distribution: {{question_plan_json}}
Response scale: five-point agreement scale

Return JSON with a sequential item ID, domain key, facet key, item text and
reverse_worded flag for each item. Also return draft Job competency links and
review_notes. Use exactly the approved item count and distribution. Do not
invent psychometric norms, validity claims, individual scores or employment
recommendations. Mark all content as a draft pending specialist review.
```

The code fallback in `ai/psychometric.py` names a `psych_config` template and a 72-item distribution, but that function currently stops before persisting a Job configuration. Tenant `ai_psychometrics_config` content is provisioned separately. Therefore this example deliberately takes an approved `question_plan_json` rather than claiming that 72 items is the live Dev questionnaire.

## How to use this pack

1. Use fictional `example.com` identities and synthetic Job/CV/response inputs.
2. Validate the returned JSON against your Elevate schema and keep participant text separate from reviewer fields.
3. Record the source Job, prompt version, input version and human review state for each generated artifact.
4. Never present the Dev-only fabricated V-Psych or V-Interview fixtures as completed real assessments.
