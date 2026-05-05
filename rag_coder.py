"""
RAG-enhanced clinical coder for the NHS Clinical Coding Agent.

For each patient episode, retrieves relevant coding guidance from the
vector store and passes it to Claude to assign ICD-10 and OPCS-4 codes.
Outputs the same field structure as the deterministic code_record() so
it is a drop-in replacement in the web app and CSV pipeline.
"""

from __future__ import annotations

import json
import os

import anthropic
from dotenv import load_dotenv

from classbrowser_tool import TOOL_DEFINITION, handle_tool_call
from nhs_clinical_coder_agent_sim import (
    FIELDNAMES,
    ICD10_REFERENCE,
    OPCS4_REFERENCE,
    parse_xlsm_records,
    WORKBOOK_FILE,
    WORKSHEET_NAME,
)
from rag_knowledge_base import build_index, retrieve

load_dotenv(override=True)

_client: anthropic.Anthropic | None = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        api_key = os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("CLAUDE_API_KEY")
        _client = anthropic.Anthropic(api_key=api_key)
    return _client


_SYSTEM_PROMPT = """\
You are an expert NHS Clinical Coding specialist with deep knowledge of \
ICD-10 5th Edition and OPCS-4 coding standards used in English NHS Trusts.

You have access to the NHS Classifications Browser via the search_classbrowser tool. \
Before finalising your codes, use it to verify the primary diagnosis and primary procedure. \
Search by clinical term (e.g. 'colonoscopy', 'haemorrhoids') — not by code number.

Core rules you must always apply:
- The primary diagnosis is the main condition treated or investigated during the episode.
- Code 'presumed', 'probable', or 'treat as' diagnoses as definitive.
- If a diagnostic endoscopy proceeds to a therapeutic procedure on the same site, \
code only the therapeutic procedure (PGCS2).
- Always assign Z92.1 for patients on long-term anticoagulants.
- For screening colonoscopy due to family history of CRC: assign Z12.1 + Z80.0 \
(unless cancer is found, then Z12.1 is dropped).
- Y codes (Chapter Y modifiers) must never appear in the primary procedure position.
- For failed intubation where the point of abandonment is no further than the mouth, \
do not assign a procedure code.

Confidence calibration — set "confidence" using these anchors:
- 0.95–1.00: The retrieved guidance contains a named rule or worked example that \
directly matches this episode (same procedure, same site, same clinical context). \
No interpretation required.
- 0.85–0.94: The guidance clearly covers this procedure type and the codes follow \
directly from applying a stated rule, but the episode has minor details not \
explicitly addressed (e.g. additional secondary diagnosis, minor site variation).
- 0.70–0.84: Coding by analogy — the guidance covers a related procedure or \
condition and you are extrapolating. The correct codes are likely right but a \
senior coder should verify.
- 0.50–0.69: The episode is genuinely ambiguous, the clinical text is incomplete, \
or multiple valid coding approaches exist. Human review is essential.
- Below 0.50: Insufficient information to code with any confidence.

Set "human_review_required" to true whenever confidence is below 0.85.

Respond ONLY with valid JSON — no markdown fences, no prose outside the object.\
"""


def _descriptions(codes: list[str], reference: dict) -> str:
    return "; ".join(
        f"{c} {reference.get(c, 'See NHS Classifications Browser')}"
        for c in codes
    )


def _parse_response(text: str) -> dict:
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end > start:
        return json.loads(text[start:end + 1])
    raise ValueError(f"No JSON object found in model response: {text[:300]}")


def rag_code_record(record: dict) -> dict:
    """
    Code one parsed workbook record using RAG-retrieved guidance and Claude.
    Returns a dict with the same keys as FIELDNAMES.
    """
    fields = record.get("fields", {})
    clinical_text = record.get("finding", "")

    # Build a focused retrieval query from the most signal-rich fields
    query = " ".join(filter(None, [
        fields.get("Indication for Exam", ""),
        fields.get("Procedure Performed", ""),
        fields.get("Findings", ""),
        fields.get("NED Procedure Diagnosis", ""),
        fields.get("NED Biopsy/Pathology", ""),
    ])).strip() or clinical_text

    chunks = retrieve(query, n_results=6)
    guidance_context = "\n\n---\n\n".join(chunks)

    user_message = f"""\
## Retrieved Coding Guidance
{guidance_context}

## Patient Episode Data
{clinical_text}

Assign the correct ICD-10 and OPCS-4 codes for this episode. \
Return this exact JSON structure:
{{
  "icd10_codes": ["CODE1", "CODE2"],
  "opcs4_codes": ["CODE1", "CODE2"],
  "confidence": 0.85,
  "human_review_required": false,
  "rules_applied": ["rule description 1", "rule description 2"],
  "reasoning": "brief rationale citing the guidance and clinical evidence"
}}\
"""

    client = _get_client()
    messages = [{"role": "user", "content": user_message}]
    classbrowser_lookups: list[str] = []

    # Agentic loop — runs until the model stops requesting tool calls
    while True:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2048,
            system=_SYSTEM_PROMPT,
            tools=[TOOL_DEFINITION],
            messages=messages,
        )

        if response.stop_reason == "tool_use":
            # Append the assistant turn with all content blocks
            messages.append({"role": "assistant", "content": response.content})

            # Execute every tool call in this turn
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    result_text = handle_tool_call(block.name, block.input)
                    classbrowser_lookups.append(
                        f"{block.input.get('classification','?')}: "
                        f"{block.input.get('search_term','?')}"
                    )
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result_text,
                    })

            messages.append({"role": "user", "content": tool_results})

        else:
            # stop_reason == "end_turn" — extract the final text response
            final_text = next(
                (b.text for b in response.content if hasattr(b, "text")), ""
            )
            break

    result = _parse_response(final_text)

    icd10_codes: list[str] = result.get("icd10_codes") or []
    opcs4_codes: list[str] = result.get("opcs4_codes") or []
    confidence = float(result.get("confidence", 0.75))
    review_flag = "Yes" if result.get("human_review_required") or confidence < 0.85 else "No"

    classbrowser_summary = (
        "Verified via NHS Classifications Browser: " + "; ".join(classbrowser_lookups)
        if classbrowser_lookups
        else "No Classifications Browser lookup performed"
    )

    return {
        "Sample Number": record.get("sample_number", ""),
        "Finding": clinical_text,
        "ICD-10 Code": "; ".join(icd10_codes),
        "ICD-10 Description": _descriptions(icd10_codes, ICD10_REFERENCE),
        "OPCS-4 Code": "; ".join(opcs4_codes),
        "OPCS-4 Description": _descriptions(opcs4_codes, OPCS4_REFERENCE),
        "Confidence": confidence,
        "Human Review Required": review_flag,
        "Coding Rules Applied": "; ".join(result.get("rules_applied") or []),
        "ClassBrowser Code Check Summary": classbrowser_summary,
        "LLM Reasoning": result.get("reasoning", ""),
        "Source Workbook": record.get("source_workbook", ""),
        "Source Worksheet": record.get("source_worksheet", ""),
        "Source Row": record.get("source_row", ""),
        "Source Columns": record.get("source_columns", ""),
    }


def run_rag_coding_process(
    workbook_path=WORKBOOK_FILE,
    output_file="rag_agent_output.csv",
    worksheet_name=WORKSHEET_NAME,
) -> dict:
    """Run RAG coding over a full workbook and write CSV output."""
    import csv
    from pathlib import Path

    print("Ensuring knowledge base is indexed...")
    build_index()

    records = parse_xlsm_records(Path(workbook_path), worksheet_name)
    output_path = Path(output_file)

    with open(output_path, "w", encoding="utf-8", newline="") as out:
        writer = csv.DictWriter(out, fieldnames=FIELDNAMES)
        writer.writeheader()
        for i, record in enumerate(records, 1):
            print(f"  Coding record {i}/{len(records)}...")
            writer.writerow(rag_code_record(record))

    return {
        "rows_processed": len(records),
        "output_file": str(output_path),
        "workbook_file": str(workbook_path),
        "worksheet_name": worksheet_name,
    }


if __name__ == "__main__":
    result = run_rag_coding_process()
    print(
        f"\nDone. Processed {result['rows_processed']} records. "
        f"Output: {result['output_file']}"
    )
