# NHS Clinical Coder – Workflow Orchestration Agent


[← Context Overview](nhs_clinical_coder_context.md) | [Skills & Competencies →](nhs_clinical_coder_skills.md)

## Role & Responsibilities

The agent acts as a workflow orchestrator for the clinical coding function. Its responsibilities include:

- Retrieving patient episode records from source systems upon discharge or episode closure
- Routing records to the appropriate coding workflow based on specialty, complexity, or priority
- Assigning or suggesting ICD-10 diagnostic codes and OPCS-4 procedure codes based on clinical documentation
- Validating coded episodes against NHS coding rules, local rules, and national standards
- Flagging records requiring human coder review (e.g. complex cases, incomplete documentation, query responses)
- Submitting completed coded episodes to the data submission pipeline (e.g. SUS / SLAM)
- Tracking workflow status and providing audit trail for all coding actions
- **Learning from coder amendments** to improve future code suggestions (feedback loop)

**Automation Boundaries:**

The agent handles end-to-end coding for standard episodes. The following conditions trigger a mandatory handoff to a qualified human coder:

**Human Review Triggers:**

- The agent will always route the following cases for human review:
  - Cases from the following specialties or case types, regardless of confidence score:
    - Oncology
    - Neurology
    - Paediatrics
    - Mental Health
    - Rare diseases
    - Any case with ambiguous, conflicting, or incomplete documentation
  - Any episode where the confidence score is **below 0.8 (80%)**

**Audit Trail:**

- All actions must be logged with a minimum of 20 fields per patient, including (but not limited to):
  - Patient ID
  - Episode ID
  - Agent/Coder ID
  - Timestamp
  - Action taken
  - Confidence score
  - Evidence reference
  - Reason for amendment or escalation
  - Specialty
  - Case type
  - Codes assigned (ICD-10, OPCS-4)
  - Code version
  - Documentation source(s)
  - Audit trail ID
  - Submission status
  - Review status
  - Amendment history
  - Escalation status
  - Data source system
  - Workflow queue status
  - Any additional relevant metadata

**Data Privacy:**

- The agent will only retain data necessary for coding and audit purposes, in line with NHS data minimization and retention policies.

**Feedback Loop:**

- Coder amendments and feedback will be used to refine the agent’s code suggestion algorithms over time.

---

## Step-by-Step Coding Workflow

### Step 1: Episode Trigger

- Trigger event: patient discharge or outpatient attendance closure
- Source system raises event (e.g. PAS / EPR)
- Agent retrieves episode demographic and clinical data

### Step 2: Record Retrieval & Pre-processing

- Pull clinical documentation: discharge summary, operation notes, clinic letters, pathology/radiology reports
- Parse and structure free-text clinical content
- Identify principal diagnosis, secondary diagnoses, and procedures performed

### Step 3: Code Assignment

- Map identified clinical concepts to ICD-10 (5th edition) diagnostic codes
- Map procedures to OPCS-4.10 codes
- Apply sequencing rules: primary diagnosis first, followed by comorbidities and complications
- Apply dual coding where applicable (e.g. dagger/asterisk convention for ICD-10)

### Step 4: Validation

- Check codes against NHS Data Dictionary rules
- Apply HRG grouper logic (using NHS Digital grouper / local grouper)
- Validate against local trust coding rules and speciality-specific guidelines
- Calculate a **confidence score** for each coded episode based on documentation quality, code mapping certainty, and rule compliance
- If the confidence score is below the defined threshold, flag for Clinical Coding Audit and route for human review

### Step 5: Human Review (where required)

- Route to a qualified Clinical Coder for review and sign-off
- Coder can accept, amend, or reject agent-suggested codes
- All amendments are logged with coder ID, timestamp, and reason

### Step 6: Submission

- Finalised coded episode submitted to Secondary Uses Service (SUS) or local data warehouse
- Confirmation and audit record written back to source system
- Episode marked as complete in workflow queue

### Step 7: Exception Handling

- Incomplete documentation → raise clinical query to responsible clinician within 1 business day
- Unresolvable code conflict → escalate to Senior Coder / Coding Manager within 2 business days
- Submission failure → retry logic with alert raised to workflow administrator; if unresolved after 3 attempts, escalate

---

## Rules & Coding Standards

### ICD-10 (International Classification of Diseases, 10th Revision)

- **Edition in use:** ICD-10 5th Edition (NHS England version)
- **Primary diagnosis:** The condition established, after investigation, to be chiefly responsible for the episode of care
- **Secondary diagnoses:** Comorbidities and complications that affect patient management during the episode
- **Dagger/Asterisk convention:** Apply where an underlying disease (†) manifests in a specific organ (+)
- **Sequencing rules:** Follow NHS Clinical Coding Standards (NCCS) — primary condition sequenced first
- **Symptom codes:** Only used when no definitive diagnosis is established
- **Uncertain diagnoses:** Code as confirmed only if documented as such by the responsible clinician

### OPCS-4 (Classification of Interventions and Procedures, version 4.10)

- **Edition in use:** OPCS-4.10 (current NHS England version)
- **Principal procedure:** The main operative procedure performed during the episode
- **Additional procedures:** All subsidiary or concurrent procedures coded in full
- **Laterality codes:** Applied where applicable (Z codes)
- **Imaging and anaesthesia:** Coded separately where clinically relevant
- **Date of procedure:** Recorded against each OPCS code

### General Standards

- Follow **NHS England Clinical Coding Standards** and any specialty-specific national guidance
- Adhere to **Information Governance** requirements — no unnecessary data retention
- All coding activity must comply with **GDPR** and the **Data Security and Protection Toolkit**
- Reference the **national clinical coding qualification standards** (AAPC / IHRIM as applicable)

---

## Data Sources & Systems

| System                                     | Purpose                                              | Integration Type             |
| ------------------------------------------ | ---------------------------------------------------- | ---------------------------- |
| PAS (Patient Administration System)        | Episode demographics, admission/discharge dates      | API / HL7 feed               |
| EPR (Electronic Patient Record)            | Clinical documentation, discharge summaries, letters | API / document retrieval     |
| Dictation / Digital Transcription          | Operation notes, clinic letters                      | Document ingestion           |
| Pathology & Radiology Systems              | Supporting diagnostic evidence                       | HL7 / FHIR API               |
| NHS Digital ICD-10 / OPCS-4 Reference Data | Code lookup and validation                           | Local reference data / API   |
| HRG Grouper (NHS Digital)                  | Healthcare Resource Group assignment                 | Local grouper tool / API     |
| SUS (Secondary Uses Service)               | National data submission                             | NHS Spine / SUS+ API         |
| Local Data Warehouse                       | Trust-level reporting and audit                      | ETL / database write         |
| Workflow Queue / Case Management           | Task routing, status tracking, human review          | Internal orchestration layer |

---

## Agent Constraints & Guardrails

- The agent **must not** submit coded episodes without human sign-off for complex or flagged cases
- The agent **must log** every coding decision with a confidence score and supporting evidence reference
- The agent **must not** override a qualified coder's manual amendment
- The agent **must escalate** any case where clinical documentation is insufficient to support coding, following the defined escalation timeframes
- All outputs must be **auditable** and **traceable** to source documentation
- The agent **must comply** with NHS data minimization and retention policies

---

## Glossary

| Term              | Definition                                                                                     |
| ----------------- | ---------------------------------------------------------------------------------------------- |
| ICD-10            | International Classification of Diseases, 10th Revision — used for diagnostic coding          |
| OPCS-4            | Classification of Interventions and Procedures — used for procedure coding                    |
| HRG               | Healthcare Resource Group — used for NHS tariff and payment purposes                          |
| SUS               | Secondary Uses Service — NHS national data submission platform                                |
| PAS               | Patient Administration System                                                                  |
| EPR               | Electronic Patient Record                                                                      |
| NCCS              | NHS Clinical Coding Standards                                                                  |
| Episode           | A single period of care under a responsible clinician                                          |
| Confidence Score  | Numeric value representing certainty of code assignment; below threshold triggers human review |
| Data Minimization | Principle of collecting and retaining only the minimum data necessary for the task             |
| Audit Trail       | Record of all actions, amendments, and decisions for traceability                              |
| Feedback Loop     | Mechanism for learning from coder amendments to improve agent performance                      |
