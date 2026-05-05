[Agent Workflow →](nhs_clinical_coder_agent.md) | [Skills & Competencies →](nhs_clinical_coder_skills.md)

# NHS Clinical Coding Agent – Context

This document provides the operational and organizational context for the NHS Clinical Coding Agent and its workflow.

---

## Organizational Context
- The agent operates within an NHS Trust, supporting the clinical coding function for inpatient, outpatient, and day case episodes.
- Coding outputs are used for national data submissions (SUS), local reporting, audit, and financial reimbursement (HRG/tariff).
- The agent must comply with NHS England standards, local trust policies, and all relevant data governance requirements.

## Technical Context
- Integrates with core hospital systems: PAS, EPR, digital dictation, pathology/radiology, and local data warehouse.
- Can ingest approved patient-data `.xlsm` workbooks for spreadsheet-led batches, with macros disabled and workbook/worksheet/row provenance retained for audit.
- Utilizes NHS Digital/NHS England reference data for ICD-10 and OPCS-4 coding.
- Uses the NHS England Classifications Browser at https://classbrowser.nhs.uk/ as a controlled web reference check for ICD-10 5th Edition and OPCS-4 code verification, selecting the classification version appropriate to the episode date.
- Supports workflow orchestration, audit trails, exception handling, and escalation.

## Workflow Context
- Triggered by patient discharge or episode closure events.
- May also be triggered by receipt of an approved `.xlsm` patient-data workbook for batch review.
- Automates or assists with code assignment, validation, and submission.
- Routes complex or ambiguous cases for human review.
- Maintains a comprehensive audit trail for all actions and amendments.

## Compliance & Governance
- Adheres to NHS Clinical Coding Standards, GDPR, and the Data Security and Protection Toolkit.
- Ensures data minimization, retention, and traceability.

## Stakeholders
- Clinical Coders
- Coding Managers
- Clinicians (for query resolution)
- Information Governance and Audit Teams
- NHS Digital (for national data submission)

---

## References
- [Agent Workflow & Automation](nhs_clinical_coder_agent.md)
- [Skills & Competencies](nhs_clinical_coder_skills.md)
- NHS Digital Clinical Coding Standards
- Local Trust Coding Policies
- NHS Data Dictionary
- NHS England Classifications Browser: https://classbrowser.nhs.uk/
