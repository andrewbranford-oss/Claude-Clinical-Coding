# Product Requirements Document: NHS Clinical Coding AI Agent

**Version:** 1.0  
**Date:** 2026-05-02  
**Status:** Draft

---

## 1. Overview

### 1.1 Purpose

This document defines the requirements for an AI-powered clinical coding agent that automates and assists the clinical coding function within an NHS Trust. The agent assigns ICD-10 diagnostic codes and OPCS-4 procedure codes to patient episodes, validates them against NHS standards, and routes cases through a human-in-the-loop review workflow.

### 1.2 Background

NHS clinical coding is a high-stakes, time-intensive process. Coded episodes underpin national data submissions (SUS), financial reimbursement (HRG tariff), and trust-level reporting. Manual coding is constrained by workforce supply, complexity of guidelines, and the volume of episodes. An AI coding agent can accelerate routine coding while preserving qualified coder oversight for complex cases.

### 1.3 Scope

The initial scope covers:

- Inpatient, outpatient, and day-case episodes
- Endoscopy as the first specialty supported (pilot)
- Batch coding from approved `.xlsm` workbooks (current primary workflow)
- Web application interface for coders and managers
- Simulation tooling for agent testing

Out of scope for v1: real-time PAS/EPR integration, direct SUS submission, specialty modules beyond endoscopy.

---

## 2. Goals & Success Metrics

| Goal | Metric | Target |
| ---- | ------ | ------ |
| Reduce manual coding time | Average time per coded episode | ≥ 40% reduction vs. baseline |
| Maintain coding accuracy | Code accuracy rate vs. qualified coder benchmark | ≥ 95% on auto-approved cases |
| Ensure safe escalation | % of sub-threshold cases correctly routed to human review | 100% |
| Audit completeness | % of episodes with full 20-field audit trail | 100% |
| Coder adoption | % of coding team using the web app weekly | ≥ 80% within 3 months |

---

## 3. Users & Stakeholders

| Role | Interaction |
| ---- | ----------- |
| Clinical Coder | Reviews agent suggestions, amends codes, approves episodes |
| Coding Manager | Monitors workflow queue, manages escalations, views reporting |
| Senior Coder | Signs off complex or escalated cases |
| Clinician | Receives and responds to clinical queries raised by the agent |
| Information Governance / Audit | Reviews audit trail and compliance reporting |
| NHS Digital | Receives national data submissions via SUS |

---

## 4. Functional Requirements

### 4.1 Episode Intake

- **FR-01** The agent must accept patient episode data from approved `.xlsm` workbooks; macros must never be executed.
- **FR-02** The agent must be triggerable by patient discharge or episode closure events (future: real-time PAS/EPR feed).
- **FR-03** Workbook provenance — workbook name, worksheet, row number, and column headings — must be recorded for every extracted field.

### 4.2 Clinical Document Processing

- **FR-04** The agent must parse and structure free-text clinical documentation: discharge summaries, operation notes, clinic letters, pathology and radiology reports.
- **FR-05** For endoscopy episodes, the agent must extract and interpret the following report sections: Indication for Exam, Procedure Performed, Extent of Exam, Findings, NED Procedure Diagnosis, NED Biopsy/Pathology, Complications, ENR Anticoagulants, and Custom2. Sections flagged as "not used" (Medications, OPCS4 Codes, Sedation Score, etc.) must be ignored for coding purposes.
- **FR-06** The agent must identify: principal diagnosis, secondary diagnoses, comorbidities, procedures performed, and laterality where applicable.

### 4.3 Code Assignment

- **FR-07** Diagnostic codes must be assigned using ICD-10 5th Edition (NHS England version).
- **FR-08** Procedure codes must be assigned using OPCS-4.11 (current NHS England version).
- **FR-09** Primary diagnosis sequencing must follow NHS Clinical Coding Standards (NCCS): the condition chiefly responsible for the episode is first.
- **FR-10** Dagger/asterisk (†/+) dual coding must be applied where the underlying disease manifests in a specific organ.
- **FR-11** Symptom codes must only be assigned when no definitive diagnosis has been established.
- **FR-12** 'Presumed', 'probable', or 'treat as' diagnoses documented by the responsible clinician must be coded as confirmed.
- **FR-13** Anticoagulant use (Warfarin, Rivaroxaban, Dabigatran, Apixaban, Edoxaban, Heparin) must always be coded to **Z92.1**.
- **FR-14** All proposed ICD-10 and OPCS-4 codes must be verified against the NHS England Classifications Browser (https://classbrowser.nhs.uk/) using the classification version appropriate to the episode date.

#### Endoscopy-Specific Code Assignment

- **FR-15** When a diagnostic procedure proceeds to a therapeutic procedure on the same site, only the therapeutic code is assigned (PGCS2).
- **FR-16** For diagnostic endoscopy with biopsy at multiple sites, only the site of biopsy (or furthest point biopsied) requires a site code.
- **FR-17** For therapeutic endoscopy with concurrent biopsy, sequencing must follow: (1) therapeutic code, (2) Chapter Z site code, (3) Y20 biopsy code, (4) biopsy site code.
- **FR-18** Y codes must never be assigned in the primary position.
- **FR-19** Multiple simultaneous therapeutic techniques require a body system code for each method.
- **FR-20** Hot snare resection must be coded as snare resection + Y13.1; hot biopsy must be coded as cauterisation of lesion (H20.2 + site code); cold biopsy/resection must be coded according to whether the lesion was removed or merely sampled.
- **FR-21** Screening colonoscopy due to family history of CRC must be coded Z12.1 + Z80.0 unless carcinoma is found, in which case Z12.1 is dropped and the neoplasm becomes primary.
- **FR-22** Failed intubation must not be coded unless the scope advanced beyond the mouth; if abandonment point is undocumented, a clinical query must be raised.

### 4.4 Validation

- **FR-23** All coded episodes must be validated against NHS Data Dictionary rules.
- **FR-24** HRG grouper logic must be applied to validate tariff assignment.
- **FR-25** Local trust coding rules and specialty-specific guidelines must be applied.
- **FR-26** Each coded episode must receive a **confidence score** (0.0–1.0) reflecting documentation quality, code mapping certainty, and rule compliance.

### 4.5 Human Review Routing

- **FR-27** Any episode with a confidence score **below 0.8** must be routed for human coder review.
- **FR-28** The following case types must always be routed for human review regardless of confidence score:
  - Oncology
  - Neurology
  - Paediatrics
  - Mental Health
  - Rare diseases
  - Cases with ambiguous, conflicting, or incomplete documentation
- **FR-29** The agent must never submit coded episodes for complex or flagged cases without human sign-off.
- **FR-30** A qualified coder must be able to accept, amend, or reject agent-suggested codes; all amendments must be logged.
- **FR-31** The agent must never override a qualified coder's manual amendment.

### 4.6 Exception Handling

- **FR-32** Incomplete documentation must trigger a clinical query to the responsible clinician within 1 business day.
- **FR-33** Unresolvable code conflicts must be escalated to a Senior Coder or Coding Manager within 2 business days.
- **FR-34** Submission failures must trigger retry logic (up to 3 attempts); if unresolved, an alert must be raised to the workflow administrator.

### 4.7 Submission

- **FR-35** Finalised coded episodes must be submitted to SUS (Secondary Uses Service) or the local data warehouse.
- **FR-36** A confirmation and audit record must be written back to the source system on submission.
- **FR-37** The episode must be marked as complete in the workflow queue.

### 4.8 Audit Trail

- **FR-38** Every coding action must be logged with a minimum of 20 fields:

| Field | Field |
| ----- | ----- |
| Patient ID | Episode ID |
| Agent / Coder ID | Timestamp |
| Action taken | Confidence score |
| Evidence reference | Reason for amendment or escalation |
| Specialty | Case type |
| ICD-10 codes assigned | OPCS-4 codes assigned |
| Code version | Documentation source(s) |
| Audit trail ID | Submission status |
| Review status | Amendment history |
| Escalation status | Data source system |
| Workflow queue status | Additional relevant metadata |

### 4.9 Feedback Loop

- **FR-39** Coder amendments must be captured and fed back to refine the agent's code suggestion algorithms over time.

---

## 5. Non-Functional Requirements

| ID | Requirement |
| -- | ----------- |
| NFR-01 | All processing of patient data must comply with GDPR, the Data Security and Protection Toolkit, and NHS data minimisation principles |
| NFR-02 | Only data necessary for coding and audit purposes may be retained |
| NFR-03 | All outputs must be auditable and traceable to source documentation |
| NFR-04 | The system must support batch processing of multi-row `.xlsm` workbooks without performance degradation |
| NFR-05 | The web application must be accessible on NHS-standard browsers and devices |
| NFR-06 | Code suggestions must be explainable: the agent must cite the source passage(s) supporting each assigned code |

---

## 6. System Integrations

| System | Purpose | Integration Type |
| ------ | ------- | ---------------- |
| PAS (Patient Administration System) | Episode demographics, admission/discharge dates | API / HL7 feed (future) |
| EPR (Electronic Patient Record) | Clinical documentation | API / document retrieval (future) |
| Digital Transcription | Operation notes, clinic letters | Document ingestion |
| Pathology & Radiology | Supporting diagnostic evidence | HL7 / FHIR API (future) |
| NHS England Classifications Browser | ICD-10 and OPCS-4 code verification | Controlled web reference |
| NHS Digital ICD-10 / OPCS-4 Reference Data | Code lookup and validation | Local reference data / API |
| HRG Grouper (NHS Digital) | Healthcare Resource Group assignment | Local grouper tool / API |
| SUS (Secondary Uses Service) | National data submission | NHS Spine / SUS+ API (future) |
| Local Data Warehouse | Trust-level reporting and audit | ETL / database write |
| Workflow Queue / Case Management | Task routing, status tracking, human review | Internal orchestration layer |
| `.xlsm` workbook input | Batch episode data (current primary channel) | File ingestion |

---

## 7. Web Application

### 7.1 Coder Interface

- Episode queue showing pending, in-review, and completed cases
- Side-by-side view of source clinical documentation and agent-suggested codes
- Ability to accept, amend, or reject each suggested code with a mandatory reason field for amendments
- Confidence score displayed per episode
- Clinical query workflow: raise, track, and resolve queries with clinicians
- Audit trail viewer per episode

### 7.2 Manager Interface

- Workflow dashboard: queue volumes, throughput, escalation counts
- Coder productivity and amendment rate reporting
- Escalation management view
- Export of audit data

### 7.3 Design Principles

The web application must be production-grade, accessible, and appropriate for a clinical NHS environment. Interface design must follow NHS Design System guidelines (plain language, high contrast, keyboard navigability). See [Front_End_Design_Skill.md](Front_End_Design_Skill.md) for frontend implementation guidance.

---

## 8. Coding Standards Reference

| Standard | Version | Usage |
| -------- | ------- | ----- |
| ICD-10 | 5th Edition (NHS England) | Diagnostic coding |
| OPCS-4 | Version 4.11 | Procedure coding |
| NHS Clinical Coding Standards (NCCS) | Current financial year | Sequencing, rules |
| NHS Data Dictionary | Current | Validation |
| NHS England Classifications Browser | classbrowser.nhs.uk | Code verification |

---

## 9. Agent Constraints & Guardrails

- The agent must not submit coded episodes without human sign-off for complex or flagged cases.
- The agent must log every coding decision with a confidence score and supporting evidence reference.
- The agent must not override a qualified coder's manual amendment.
- The agent must escalate any case where clinical documentation is insufficient, within the defined timeframes.
- All outputs must be auditable and traceable to source documentation.
- The agent must comply with NHS data minimisation and retention policies.

---

## 10. Glossary

| Term | Definition |
| ---- | ---------- |
| ICD-10 | International Classification of Diseases, 10th Revision — diagnostic coding |
| OPCS-4 | Classification of Interventions and Procedures — procedure coding |
| HRG | Healthcare Resource Group — NHS tariff and payment |
| SUS | Secondary Uses Service — national data submission platform |
| PAS | Patient Administration System |
| EPR | Electronic Patient Record |
| NCCS | NHS Clinical Coding Standards |
| Episode | A single period of care under a responsible clinician |
| Confidence Score | Numeric value (0.0–1.0) representing certainty of code assignment; below 0.8 triggers human review |
| Dagger/Asterisk | ICD-10 dual-coding convention: underlying disease (†) manifesting in a specific organ (+) |
| OGD | Oesophagogastroduodenoscopy |
| RFA | Radiofrequency ablation |
| CRC | Colorectal cancer |
| ICV | Ileocaecal valve |
| Data Minimisation | Collecting and retaining only the minimum data necessary for the task |
| Audit Trail | Record of all actions, amendments, and decisions for traceability |
| Feedback Loop | Mechanism for learning from coder amendments to improve agent performance |

---

## 11. Related Documents

| Document | Description |
| -------- | ----------- |
| [nhs_clinical_coder_context.md](nhs_clinical_coder_context.md) | Organisational and technical context |
| [nhs_clinical_coder_agent.md](nhs_clinical_coder_agent.md) | Workflow orchestration agent specification |
| [nhs_clinical_coder_skills.md](nhs_clinical_coder_skills.md) | Required coder skills and competencies |
| [Endoscopy_Automation_Guidance.md](Endoscopy_Automation_Guidance.md) | Endoscopy ICD-10 and OPCS-4 coding rules |
| [Endoscopy_Report_breakdown.md](Endoscopy_Report_breakdown.md) | How to interpret endoscopy report sections |
| [nhs_classifications_browser_user_guide.md](nhs_classifications_browser_user_guide.md) | NHS Classifications Browser usage guide |
| [nhs_clinical_coder_agent_sim.py](nhs_clinical_coder_agent_sim.py) | Agent simulation for testing |
| [nhs_clinical_coder_web_app.py](nhs_clinical_coder_web_app.py) | Web application backend |

---

*This document should be reviewed and updated at the start of each financial year to reflect changes to ICD-10/OPCS-4 editions, NCCS updates, and NHS Digital submission requirements.*
