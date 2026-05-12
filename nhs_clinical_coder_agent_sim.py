import csv
import re
import time
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

# File paths
WORKBOOK_FILE = Path("/Users/andybranford/Documents/VS Code/Clinical coding 100 patient sample_Trimmed.xlsm")
OUTPUT_FILE = "nhs_clinical_coder_agent_output.csv"
WORKSHEET_NAME = "Sheet1"

NAMESPACES = {
    "main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "rel": "http://schemas.openxmlformats.org/package/2006/relationships",
    "office_rel": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
}
EVIDENCE_COLUMNS = [
    "Indication for Exam",
    "Procedure Performed",
    "Extent of Exam",
    "Findings",
    "NED Procedure Diagnosis",
    "NED Biopsy/Pathology",
    "ENR Anticoagulants",
    "ENR Health History",
]
PROCEDURE_KEYWORDS = [
    "surgery",
    "performed",
    "procedure",
    "operation",
    "resection",
    "excision",
    "repair",
    "ablation",
    "insertion",
    "removal",
    "replacement",
    "release",
    "decompression",
    "craniotomy",
    "endoscopy",
    "biopsy",
    "colonoscopy",
    "ogd",
    "pouchoscopy",
    "sigmoidoscopy",
    "polypectomy",
]

ICD10_REFERENCE = {
    "D50.9": "Iron deficiency anaemia, unspecified",
    "E10": "Type 1 diabetes mellitus",
    "E11": "Type 2 diabetes mellitus",
    "F41.9": "Anxiety disorder, unspecified",
    "I10": "Essential (primary) hypertension",
    "I48.9": "Atrial fibrillation and atrial flutter, unspecified",
    "J44.9": "Chronic obstructive pulmonary disease, unspecified",
    "J45.9": "Asthma, unspecified",
    "K20": "Oesophagitis",
    "K21.9": "Gastro-oesophageal reflux disease without oesophagitis",
    "K22.2": "Oesophageal obstruction",
    "K22.7": "Barrett's oesophagus",
    "K29.7": "Gastritis, unspecified",
    "K44.9": "Diaphragmatic hernia without obstruction or gangrene",
    "K50.9": "Crohn's disease, unspecified",
    "K51.9": "Ulcerative colitis, unspecified",
    "K57.3": "Diverticular disease of large intestine without perforation or abscess",
    "K63.5": "Polyp of colon",
    "K64.9": "Haemorrhoids, unspecified",
    "R10.4": "Other and unspecified abdominal pain",
    "R13": "Dysphagia",
    "R19.5": "Other faecal abnormalities",
    "R93.3": "Abnormal findings on diagnostic imaging of other parts of digestive tract",
    "Z12.1": "Special screening examination for neoplasm of intestinal tract",
    "Z80.0": "Family history of malignant neoplasm of digestive organs",
    "Z92.1": "Personal history of long-term (current) use of anticoagulants",
}

OPCS4_REFERENCE = {
    "G43.3": "Fibreoptic endoscopic cauterisation of lesion of upper gastrointestinal tract",
    "G43.5": "Fibreoptic endoscopic destruction of lesion of upper gastrointestinal tract NEC",
    "G44.2": "Fibreoptic removal of foreign body from upper gastrointestinal tract",
    "G45.1": "Fibreoptic endoscopic examination of upper gastrointestinal tract and biopsy of lesion of upper gastrointestinal tract",
    "G45.9": "Unspecified diagnostic fibreoptic endoscopic examination of upper gastrointestinal tract",
    "G47.1": "Percutaneous endoscopic gastrostomy",
    "H20.1": "Fibreoptic endoscopic snare resection of lesion of colon",
    "H20.2": "Fibreoptic endoscopic cauterisation of lesion of colon",
    "H20.5": "Fibreoptic endoscopic submucosal resection of lesion of colon",
    "H20.6": "Fibreoptic endoscopic resection of lesion of colon NEC",
    "H22.1": "Diagnostic fibreoptic endoscopic examination of colon and biopsy of lesion of colon",
    "H22.9": "Unspecified diagnostic fibreoptic endoscopic examination of colon",
    "H23.1": "Endoscopic snare resection of lesion of lower bowel using fibreoptic sigmoidoscope",
    "H25.1": "Diagnostic fibreoptic endoscopic examination of lower bowel and biopsy of lesion of lower bowel",
    "H25.9": "Unspecified diagnostic fibreoptic endoscopic examination of lower bowel",
    "Y13.1": "Cauterisation of lesion of organ NOC",
    "Y13.4": "Radiofrequency controlled thermal destruction of lesion of organ NOC",
    "Y17.1": "Electrocauterisation of lesion of organ NOC",
    "Y20.3": "Biopsy of lesion of organ NOC",
    "Y20.9": "Unspecified biopsy of organ NOC",
    "O11.1": "Gastro-oesophageal junction",
    "O30.1": "Hepatic flexure",
    "O30.2": "Splenic flexure",
    "Z27.1": "Oesophagus",
    "Z27.2": "Stomach",
    "Z27.3": "Pylorus",
    "Z27.4": "Duodenum",
    "Z27.5": "Jejunum",
    "Z27.6": "Ileum",
    "Z27.7": "Small intestine",
    "Z28.2": "Caecum",
    "Z28.3": "Ascending colon",
    "Z28.4": "Transverse colon",
    "Z28.5": "Descending colon",
    "Z28.6": "Sigmoid colon",
    "Z29.1": "Rectum",
    "Z29.2": "Anus",
    "Z29.3": "Perianal tissue",
    "Z29.4": "Colorectal/rectosigmoid",
}

ANTICOAGULANTS = [
    "warfarin",
    "rivaroxaban",
    "xarelto",
    "dabigatran",
    "pradaxa",
    "apixaban",
    "eliquis",
    "edoxaban",
    "lixiana",
    "heparin",
    "clexane",
    "enoxaparin",
]


def column_index(cell_ref):
    """Return a zero-based column index from an Excel cell reference."""
    match = re.match(r"([A-Z]+)", cell_ref)
    if not match:
        return 0

    index = 0
    for char in match.group(1):
        index = index * 26 + ord(char) - ord("A") + 1
    return index - 1


def read_shared_strings(workbook_zip):
    """Read the workbook shared strings table, if present."""
    if "xl/sharedStrings.xml" not in workbook_zip.namelist():
        return []

    root = ET.fromstring(workbook_zip.read("xl/sharedStrings.xml"))
    strings = []
    for item in root.findall("main:si", NAMESPACES):
        text_parts = [text.text or "" for text in item.findall(".//main:t", NAMESPACES)]
        strings.append("".join(text_parts))
    return strings


def worksheet_path(workbook_zip, worksheet_name):
    """Resolve a worksheet display name to its XML path inside the workbook."""
    workbook = ET.fromstring(workbook_zip.read("xl/workbook.xml"))
    rels = ET.fromstring(workbook_zip.read("xl/_rels/workbook.xml.rels"))

    rel_targets = {
        rel.attrib["Id"]: rel.attrib["Target"]
        for rel in rels.findall("rel:Relationship", NAMESPACES)
    }

    for sheet in workbook.findall(".//main:sheet", NAMESPACES):
        if sheet.attrib.get("name") == worksheet_name:
            rel_id = sheet.attrib[f"{{{NAMESPACES['office_rel']}}}id"]
            target = rel_targets[rel_id]
            return f"xl/{target.lstrip('/')}"

    available = [
        sheet.attrib.get("name", "")
        for sheet in workbook.findall(".//main:sheet", NAMESPACES)
    ]
    raise ValueError(f"Worksheet {worksheet_name!r} not found. Available sheets: {', '.join(available)}")


def cell_value(cell, shared_strings):
    """Extract a scalar value from a worksheet cell."""
    cell_type = cell.attrib.get("t")

    if cell_type == "inlineStr":
        return "".join(text.text or "" for text in cell.findall(".//main:t", NAMESPACES)).strip()

    value_node = cell.find("main:v", NAMESPACES)
    if value_node is None:
        return ""

    value = value_node.text or ""
    if cell_type == "s":
        return shared_strings[int(value)].strip()
    return value.strip()


def parse_xlsm_records(workbook_path, worksheet_name=WORKSHEET_NAME):
    """Read patient episode rows from an xlsm workbook without executing macros."""
    records = []

    with zipfile.ZipFile(workbook_path) as workbook_zip:
        shared_strings = read_shared_strings(workbook_zip)
        sheet_path = worksheet_path(workbook_zip, worksheet_name)
        sheet = ET.fromstring(workbook_zip.read(sheet_path))

        rows = []
        for row in sheet.findall(".//main:sheetData/main:row", NAMESPACES):
            values = {}
            for cell in row.findall("main:c", NAMESPACES):
                values[column_index(cell.attrib.get("r", "A"))] = cell_value(cell, shared_strings)
            if values:
                max_index = max(values)
                rows.append([values.get(index, "") for index in range(max_index + 1)])

    if not rows:
        return records

    headers = rows[0]
    for row_number, row in enumerate(rows[1:], start=2):
        row_values = {
            header: row[index] if index < len(row) else ""
            for index, header in enumerate(headers)
            if header
        }
        if not any(row_values.values()):
            continue

        evidence_parts = []
        populated_columns = []
        for column in EVIDENCE_COLUMNS:
            value = row_values.get(column, "")
            if value:
                evidence_parts.append(f"{column}: {value}")
                populated_columns.append(column)

        records.append(
            {
                "sample_number": row_values.get("sample number", ""),
                "finding": " | ".join(evidence_parts),
                "fields": row_values,
                "source_workbook": str(workbook_path),
                "source_worksheet": worksheet_name,
                "source_row": row_number,
                "source_columns": "; ".join(populated_columns),
            }
        )

    return records

FIELDNAMES = [
    "Sample Number",
    "Finding",
    "ICD-10 Code",
    "ICD-10 Description",
    "OPCS-4 Code",
    "OPCS-4 Description",
    "Confidence",
    "Human Review Required",
    "Coding Rules Applied",
    "ClassBrowser Code Check Summary",
    "LLM Reasoning",
    "Source Workbook",
    "Source Worksheet",
    "Source Row",
    "Source Columns",
    "Coded Timestamp",
    "Specialty",
    "Case Type",
    "ICD-10 Version",
    "OPCS-4 Version",
]


def add_unique(items, code):
    if code and code not in items:
        items.append(code)


def text_contains(text, *terms):
    lowered = text.lower()
    return any(term.lower() in lowered for term in terms)


def normalise_whitespace(value):
    return re.sub(r"\s+", " ", value or "").strip()


def site_code_for_text(text, upper=False):
    lowered = text.lower()
    site_rules = [
        ("gastro-oesophageal junction", "O11.1"),
        ("gastroesophageal junction", "O11.1"),
        ("goj", "O11.1"),
        ("ogj", "O11.1"),
        ("oesophagus", "Z27.1"),
        ("esophagus", "Z27.1"),
        ("stomach", "Z27.2"),
        ("antrum", "Z27.2"),
        ("gastric", "Z27.2"),
        ("pylorus", "Z27.3"),
        ("duodenum", "Z27.4"),
        ("d1", "Z27.4"),
        ("d2", "Z27.4"),
        ("d3", "Z27.4"),
        ("jejunal", "Z27.5"),
        ("jejunum", "Z27.5"),
        ("terminal ileum", "Z27.6"),
        ("ileum", "Z27.6"),
        ("caecum", "Z28.2"),
        ("cecum", "Z28.2"),
        ("ascending", "Z28.3"),
        ("hepatic flexure", "O30.1"),
        ("transverse", "Z28.4"),
        ("splenic flexure", "O30.2"),
        ("descending", "Z28.5"),
        ("sigmoid", "Z28.6"),
        ("rectosigmoid", "Z29.4"),
        ("rectum", "Z29.1"),
        ("anal", "Z29.2"),
        ("anus", "Z29.2"),
        ("perianal", "Z29.3"),
    ]
    for term, code in site_rules:
        if term in lowered:
            return code
    return "Z27.4" if upper else "Z28.2"


def map_icd10(fields):
    indication = fields.get("Indication for Exam", "")
    findings = fields.get("Findings", "")
    diagnosis = fields.get("NED Procedure Diagnosis", "")
    anticoagulants = fields.get("ENR Anticoagulants", "")
    history = fields.get("ENR Health History", "")
    combined = " ".join([indication, findings, diagnosis, anticoagulants, history])
    lowered = combined.lower()
    codes = []
    rules = []

    if text_contains(combined, "strong family hx of crc", "family history of crc", "family hx of crc"):
        add_unique(codes, "Z12.1")
        add_unique(codes, "Z80.0")
        rules.append("Screening colonoscopy due to family history of colorectal cancer")

    diagnostic_text = " ".join([diagnosis, findings, indication])
    if text_contains(diagnostic_text, "barrett"):
        add_unique(codes, "K22.7")
        rules.append("Barrett's oesophagus documented")
    if text_contains(diagnostic_text, "oesophagitis", "esophagitis"):
        add_unique(codes, "K20")
        rules.append("Oesophagitis documented")
    if text_contains(diagnostic_text, "dysphagia"):
        add_unique(codes, "R13")
        rules.append("Dysphagia indication/finding documented")
    if text_contains(diagnostic_text, "hiatus hernia", "hiatal hernia"):
        add_unique(codes, "K44.9")
        rules.append("Hiatus hernia documented")
    if text_contains(diagnostic_text, "gord", "reflux"):
        add_unique(codes, "K21.9")
        rules.append("GORD/reflux documented")
    if text_contains(diagnostic_text, "gastritis"):
        add_unique(codes, "K29.7")
        rules.append("Gastritis documented")
    if text_contains(diagnostic_text, "stricture"):
        add_unique(codes, "K22.2")
        rules.append("Oesophageal/intestinal stricture wording identified")
    if text_contains(diagnostic_text, "diverticulosis", "diverticular disease"):
        add_unique(codes, "K57.3")
        rules.append("Diverticular disease documented")
    if text_contains(diagnostic_text, "haemorrhoid", "hemorrhoid"):
        add_unique(codes, "K64.9")
        rules.append("Haemorrhoids documented")
    if text_contains(diagnostic_text, "polyp"):
        add_unique(codes, "K63.5")
        rules.append("Colon/gastrointestinal polyp documented")
    if text_contains(combined, "crohn"):
        add_unique(codes, "K50.9")
        rules.append("Crohn's disease documented")
    if text_contains(combined, "ulcerative colitis", " uc "):
        add_unique(codes, "K51.9")
        rules.append("Ulcerative colitis documented")
    if text_contains(diagnostic_text, "iron deficiency anaemia", "iron deficient", "ida"):
        add_unique(codes, "D50.9")
        rules.append("Iron deficiency anaemia indication documented")
    if text_contains(diagnostic_text, "abdominal pain"):
        add_unique(codes, "R10.4")
        rules.append("Abdominal pain indication documented")
    if text_contains(diagnostic_text, "fit:", "positive fit", "faecal"):
        add_unique(codes, "R19.5")
        rules.append("FIT/faecal abnormality indication documented")

    if any(term in lowered for term in ANTICOAGULANTS):
        add_unique(codes, "Z92.1")
        rules.append("Long-term anticoagulant use captured per endoscopy guidance")

    if text_contains(history, " af ", "atrial fibrillation"):
        add_unique(codes, "I48.9")
    if text_contains(history, "type 1"):
        add_unique(codes, "E10")
    if text_contains(history, "type 2"):
        add_unique(codes, "E11")
    if text_contains(history, "asthma"):
        add_unique(codes, "J45.9")
    if text_contains(history, "copd", "emphysema"):
        add_unique(codes, "J44.9")
    if text_contains(history, "hypertension", " htn "):
        add_unique(codes, "I10")
    if text_contains(history, "anxiety"):
        add_unique(codes, "F41.9")

    if not codes:
        if text_contains(diagnosis, "normal", "no confirmed diagnosis"):
            rules.append("No definitive diagnosis; primary diagnosis selected from indication")
        if text_contains(indication, "abnormality on imaging", "abnormality on ct"):
            add_unique(codes, "R93.3")
        else:
            add_unique(codes, "R10.4")
        rules.append("Fallback symptom/indication code used because no supported diagnosis term matched")

    return codes, rules


def map_opcs4(fields):
    procedure = fields.get("Procedure Performed", "")
    findings = fields.get("Findings", "")
    pathology = fields.get("NED Biopsy/Pathology", "")
    extent = fields.get("Extent of Exam", "")
    text = " ".join([procedure, findings, pathology, extent])
    lowered = text.lower()
    codes = []
    rules = []
    is_upper = text_contains(procedure, "ogd", "upper gi", "peg")
    is_colon = text_contains(procedure, "colonoscopy")
    is_sigmoid = text_contains(procedure, "sigmoidoscopy")
    has_biopsy = text_contains(text, "biopsy", "biopsies", "clo")
    has_polyp_or_lesion = text_contains(text, "polyp", "lesion", "mucosal change")
    has_resection = text_contains(text, "snare", "emr", "smr", "submucosal", "resect", "resection", "removed", "excised", "polypectomy")

    if text_contains(text, "failed intubation") and not extent:
        rules.append("Failed upper GI intubation without documented point beyond mouth; no OPCS procedure assigned")
        return codes, rules

    if text_contains(procedure, "peg"):
        add_unique(codes, "G47.1")
        rules.append("PEG/PEG-J insertion mapped to percutaneous endoscopic gastrostomy pathway")
        site = site_code_for_text(text, upper=True)
        add_unique(codes, site)
        return codes, rules

    if is_upper:
        if text_contains(text, "rfa", "radiofrequency", "halo"):
            add_unique(codes, "G43.5")
            add_unique(codes, "Y13.4")
            add_unique(codes, "Z27.1")
            rules.append("Upper GI radiofrequency ablation rule applied")
        elif text_contains(text, "foreign body"):
            add_unique(codes, "G44.2")
            add_unique(codes, site_code_for_text(text, upper=True))
            rules.append("Upper GI foreign body removal rule applied")
        elif has_biopsy:
            add_unique(codes, "G45.1")
            add_unique(codes, site_code_for_text(" ".join([pathology, findings, extent]), upper=True))
            rules.append("OGD/upper GI endoscopy with biopsy rule applied")
        else:
            add_unique(codes, "G45.9")
            add_unique(codes, site_code_for_text(extent or text, upper=True))
            rules.append("Diagnostic OGD/upper GI endoscopy rule applied")
        return codes, rules

    if is_colon or is_sigmoid or text_contains(procedure, "pouchoscopy"):
        site = site_code_for_text(" ".join([findings, pathology, extent]))
        if text_contains(text, "apc", "argon plasma", "hot biopsy", "cauter"):
            add_unique(codes, "H20.2")
            if text_contains(text, "apc", "argon plasma"):
                add_unique(codes, "Y17.1")
            add_unique(codes, site)
            rules.append("Colon cauterisation/hot biopsy/APC rule applied")
        elif text_contains(text, "emr", "smr", "submucosal"):
            add_unique(codes, "H20.5")
            add_unique(codes, site)
            rules.append("Colon EMR/SMR/submucosal resection rule applied")
        elif text_contains(text, "snare"):
            add_unique(codes, "H23.1" if is_sigmoid else "H20.1")
            add_unique(codes, site)
            if text_contains(text, "hot snare"):
                add_unique(codes, "Y13.1")
            rules.append("Snare resection rule applied")
        elif has_polyp_or_lesion and has_resection:
            add_unique(codes, "H20.6")
            add_unique(codes, site)
            rules.append("Endoscopic colon lesion resection NEC rule applied")
        elif has_biopsy:
            add_unique(codes, "H25.1" if is_sigmoid else "H22.1")
            add_unique(codes, site)
            rules.append("Diagnostic lower GI endoscopy with biopsy rule applied")
        else:
            add_unique(codes, "H25.9" if is_sigmoid else "H22.9")
            add_unique(codes, site_code_for_text(extent or text))
            rules.append("Diagnostic lower GI endoscopy rule applied")
        return codes, rules

    if text_contains(text, *PROCEDURE_KEYWORDS):
        add_unique(codes, "H22.9")
        add_unique(codes, site_code_for_text(extent or text))
        rules.append("Generic diagnostic endoscopy fallback rule applied")

    return codes, rules


def code_descriptions(codes, reference):
    return "; ".join(f"{code} {reference.get(code, 'Description not in local deterministic reference')}" for code in codes)


def deterministic_reasoning(record, icd10_codes, opcs4_codes, rules, confidence):
    fields = record.get("fields", {})
    summary = []
    for name in ["Indication for Exam", "Procedure Performed", "Extent of Exam", "NED Procedure Diagnosis", "NED Biopsy/Pathology", "ENR Anticoagulants"]:
        value = normalise_whitespace(fields.get(name, ""))
        if value:
            summary.append(f"{name}: {value}")
    return (
        f"Deterministic endoscopy rules selected ICD-10 [{'; '.join(icd10_codes)}] "
        f"and OPCS-4 [{'; '.join(opcs4_codes) if opcs4_codes else 'none'}]. "
        f"Rules applied: {'; '.join(rules)}. Evidence summary: {' | '.join(summary)}. "
        f"Confidence {confidence} reflects rule specificity, evidence completeness, and need for coder review."
    )


def code_record(record):
    """Code one parsed workbook record using deterministic endoscopy rules."""
    fields = record.get("fields", {})
    icd10_codes, icd_rules = map_icd10(fields)
    opcs4_codes, opcs_rules = map_opcs4(fields)
    rules = icd_rules + opcs_rules
    confidence = 0.92
    if any("Fallback" in rule or "no OPCS" in rule for rule in rules):
        confidence -= 0.18
    if len(icd10_codes) > 5:
        confidence -= 0.05
    if not opcs4_codes and any(word in record["finding"].lower() for word in PROCEDURE_KEYWORDS):
        confidence -= 0.12
    confidence = round(max(0.55, min(0.98, confidence)), 2)
    review_flag = "Yes" if confidence < 0.8 or len(icd10_codes) > 6 else "No"
    reasoning = deterministic_reasoning(record, icd10_codes, opcs4_codes, rules, confidence)
    return {
        "Sample Number": record["sample_number"],
        "Finding": record["finding"],
        "ICD-10 Code": "; ".join(icd10_codes),
        "ICD-10 Description": code_descriptions(icd10_codes, ICD10_REFERENCE),
        "OPCS-4 Code": "; ".join(opcs4_codes),
        "OPCS-4 Description": code_descriptions(opcs4_codes, OPCS4_REFERENCE),
        "Confidence": confidence,
        "Human Review Required": review_flag,
        "Coding Rules Applied": "; ".join(rules),
        "ClassBrowser Code Check Summary": "Not checked in command-line run",
        "LLM Reasoning": reasoning,
        "Source Workbook": record["source_workbook"],
        "Source Worksheet": record["source_worksheet"],
        "Source Row": record["source_row"],
        "Source Columns": record["source_columns"],
        "Coded Timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "Specialty": "Endoscopy",
        "Case Type": "Day Case",
        "ICD-10 Version": "ICD-10 5th Edition",
        "OPCS-4 Version": "OPCS-4.11",
    }


def run_coding_process(workbook_path=WORKBOOK_FILE, output_file=OUTPUT_FILE, worksheet_name=WORKSHEET_NAME, seed=None):
    """Run the workbook coding simulation and write a CSV output file."""
    records = parse_xlsm_records(Path(workbook_path), worksheet_name)
    output_path = Path(output_file)
    with open(output_path, "w", encoding="utf-8", newline="") as out:
        writer = csv.DictWriter(out, fieldnames=FIELDNAMES)
        writer.writeheader()

        for record in records:
            writer.writerow(code_record(record))

    return {
        "rows_processed": len(records),
        "output_file": str(output_path),
        "workbook_file": str(workbook_path),
        "worksheet_name": worksheet_name,
    }


def main():
    result = run_coding_process()
    print(f"Processed {result['rows_processed']} workbook rows. Output written to {result['output_file']}.")


if __name__ == "__main__":
    main()
