# NHS Clinical Coding AI Agent

An AI-powered clinical coding assistant for NHS Trusts. The agent reads patient episode data from approved `.xlsm` workbooks, assigns ICD-10 (5th Edition) and OPCS-4 codes using Claude, validates them against NHS standards, and routes cases through a human-in-the-loop review workflow via a web application.

> **Pilot specialty:** Endoscopy  
> **Status:** Prototype / active development

---

## Overview

NHS clinical coding is a high-stakes, time-intensive process. Coded episodes underpin national data submissions (SUS), financial reimbursement (HRG tariff), and trust-level reporting. This agent automates routine coding while preserving qualified coder oversight for complex or low-confidence cases.

### Key capabilities

- Parses structured endoscopy report fields (Indication, Procedure, Findings, Pathology, etc.) from `.xlsm` workbooks
- Assigns ICD-10 diagnostic codes and OPCS-4 procedure codes following NHS Clinical Coding Standards (NCCS)
- Validates codes live against the [NHS Classifications Browser](https://classbrowser.nhs.uk/)
- RAG-enhanced coding: retrieves relevant guidance from a local vector knowledge base before calling Claude
- Confidence scoring and structured rationale for every coded episode
- Human review queue for sub-threshold or ambiguous cases
- Coder feedback loop — coders can accept, amend, or reject agent suggestions
- Role-based web interface for Clinical Coders and Coding Managers
- Full audit trail exported as CSV and JSON

---

## Architecture

```text
nhs_clinical_coder_web_app.py     Web application (Python stdlib HTTP server)
nhs_clinical_coder_agent_sim.py   Deterministic baseline coder (no LLM)
rag_coder.py                      RAG + Claude API coder (primary AI path)
rag_knowledge_base.py             Builds and queries the local vector index
classbrowser_tool.py              Live NHS Classifications Browser lookup tool
mcp_server.py                     MCP server (FastMCP) for IDE / agent integration
eval_coder.py                     Offline evaluation harness
```

### Process flow

```text
.xlsm workbook
      │
      ▼
Episode extraction (nhs_clinical_coder_agent_sim.py)
      │  extracts: Indication, Procedure, Findings, Pathology, etc.
      ▼
RAG retrieval (rag_knowledge_base.py)
      │  retrieves relevant ICD-10 / OPCS-4 guidance chunks
      ▼
Claude (rag_coder.py)
      │  assigns ICD-10 + OPCS-4 codes with confidence + rationale
      │  calls classbrowser_tool for live code validation
      ▼
Confidence routing
      ├── HIGH  → auto-approved, written to CSV output
      └── LOW   → queued for human review in web app
            │
            ▼
       Coder review (web app)
            │  accept / amend / reject
            ▼
       Feedback stored → CSV audit trail
```

---

## Installation

### Prerequisites

- Python 3.11+
- An [Anthropic API key](https://console.anthropic.com/)

### Setup

```bash
git clone <repo-url>
cd <repo-dir>

python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

pip install anthropic fastmcp python-dotenv
```

Create a `.env` file in the project root:

```env
ANTHROPIC_API_KEY=sk-ant-...
```

---

## Usage

### Run the web application

```bash
python nhs_clinical_coder_web_app.py
```

Open [http://127.0.0.1:8080](http://127.0.0.1:8080) in your browser.

**Default accounts (development only):**

| Username | Password | Role |
| -------- | -------- | ---- |
| `coder1` | `coding1` | Clinical Coder |
| `coder2` | `coding2` | Clinical Coder |
| `manager` | `manage1` | Coding Manager |

### Upload and code a workbook

1. Sign in as a Clinical Coder
2. Upload an approved `.xlsm` patient episode workbook
3. Choose coding mode: **Agent (RAG + Claude)** or **Simulation (deterministic baseline)**
4. The agent processes each episode and displays results with ICD-10 and OPCS-4 codes, confidence scores, and rationale
5. Review and amend any codes before accepting
6. Download the coded output as CSV

### Build the RAG knowledge base

```bash
python rag_knowledge_base.py
```

Place ICD-10 / OPCS-4 coding guidance documents (PDF or text) in the `knowledge_base/` directory before running.

### Run the MCP server

```bash
python mcp_server.py
```

The MCP server exposes `search_nhs_classbrowser` as a tool, enabling Claude in Claude Code or other MCP-compatible agents to perform live NHS Classifications Browser lookups during coding sessions.

### Evaluate coding accuracy

```bash
python eval_coder.py
```

Compares agent output against a gold-standard coded dataset and generates `eval_report.html`.

---

## Standards and compliance

| Standard | Detail |
| -------- | ------ |
| Diagnostic coding | ICD-10 5th Edition (NHS England version) |
| Procedure coding | OPCS-4.11 (NHS England current version) |
| Coding rules | NHS Clinical Coding Standards (NCCS) |
| Code validation | NHS England Classifications Browser (classbrowser.nhs.uk) |
| Data governance | GDPR, NHS Data Security and Protection Toolkit |
| Workbook handling | Macros disabled; workbook / worksheet / row provenance recorded per episode |

---

## Coding standards applied

- Primary diagnosis sequenced per NCCS (condition chiefly responsible for the episode)
- Dagger/asterisk (†/★) dual coding applied for underlying disease with organ manifestation
- Symptom codes only assigned when no definitive diagnosis is established
- Presumed / probable diagnoses coded as confirmed when documented by the responsible clinician
- Episode date used to select the correct classification version

---

## Project structure

```text
├── nhs_clinical_coder_web_app.py       Main web app
├── nhs_clinical_coder_agent_sim.py     Deterministic coder / workbook parser
├── rag_coder.py                        Claude API + RAG coder
├── rag_knowledge_base.py               Vector index builder and retriever
├── classbrowser_tool.py                NHS Classifications Browser tool
├── mcp_server.py                       FastMCP server
├── eval_coder.py                       Evaluation harness
├── eval_report.html                    Latest evaluation report
├── web_outputs/                        Coded output CSV and JSON (git-ignored)
├── web_uploads/                        Uploaded workbooks (git-ignored)
├── knowledge_base/                     RAG source documents (git-ignored)
├── PRD_NHS_Clinical_Coding_Agent.md    Product requirements document
├── nhs_clinical_coder_context.md       Operational and organisational context
├── nhs_clinical_coder_agent.md         Agent workflow documentation
└── CONTRIBUTING.md                     Contribution guidelines
```

---

## Roadmap

- Real-time PAS/EPR integration (trigger on patient discharge)
- Direct SUS submission
- Additional specialty modules beyond endoscopy
- Manager dashboard with coding throughput and accuracy metrics
- Multi-episode batch progress tracking via WebSocket

---

## Licence

This project is developed for NHS use. Not licensed for commercial use or deployment outside an NHS governance framework without prior approval.
