# Endoscopy Guidance for Xerox

---

## Input and Code Verification

Patient and episode data may be supplied as an approved `.xlsm` workbook for batch endoscopy coding. Treat the workbook as patient-identifiable clinical data, do not execute embedded macros, and retain workbook name, worksheet, row number, and relevant column headings as evidence provenance.

All proposed ICD-10 and OPCS-4 codes must be checked against the [NHS England Classifications Browser](https://classbrowser.nhs.uk/) using the classification version appropriate to the episode date before coder review or submission.

---

## Abbreviations

- **D1, D2 etc** – refers to the duodenum
- **Bx** = biopsy
- **OGD** = Oesophagogastroduodenoscopy
- **RFA** = radiofrequency ablation
- **CRC** = colorectal cancer
- **ICV** = ileocaecal valve
- **GOJ** = Gastroesophageal Junction

---

## ICD-10 Diagnosis Coding

### DGCS.1: Primary Diagnosis

The primary diagnosis definition must always be applied when assigning ICD-10 codes on the coded clinical record:

i) The first diagnosis field(s) of the coded clinical record (the primary diagnosis) will contain the main condition treated or investigated during the relevant episode of healthcare.

ii) Where a definitive diagnosis has not been made by the responsible clinician, the main symptom, abnormal findings, or problem should be recorded in the first diagnosis field of the coded clinical record.

All other relevant diagnoses must be coded in addition to the primary diagnosis.

#### Specificity

Where the diagnosis recorded as the main condition describes a condition in general terms, and a term that provides more precise information about the site or nature of the condition is recorded elsewhere, reselect the latter as the main condition.

### Absence of Definitive Diagnosis

It is not always possible for the responsible consultant to provide a definitive (confirmed) diagnosis in the medical record for an episode but they may be treating or investigating the patient's condition based on a 'presumed' or 'probable' diagnosis.

- Code 'presumed', 'probable' or 'treat as' as a definitive diagnosis.

### Screening Colonoscopy due to Family History of CRC

**ICD-10 Diagnosis Coding:**

```
Z12.1  Special screening examination for neoplasm of intestinal tract
Z80.0  Family history of malignant neoplasm of digestive organs
```

> **N.B.** Code any incidental findings; anything treated will become the primary diagnosis. If Ca is found, Z12.1 is no longer required.

### Anticoagulant Use

Patients on long-term anti-coagulants/history of long-term anticoagulants must always be coded to ICD-10 code **Z92.1**.

**Commonly prescribed anticoagulants:**

- Warfarin
- Rivaroxaban (Xarelto)
- Dabigatran (Pradaxa)
- Apixaban (Eliquis)
- Edoxaban (Lixiana)
- Heparin

---

## OPCS Procedure Coding

### PGCS2: Diagnostic versus Therapeutic Procedures

If a diagnostic procedure proceeds to, or is performed at the same time as, a therapeutic procedure on the same site then only the code for the therapeutic procedure is required. This includes:

- Diagnostic endoscopies performed prior to a therapeutic endoscopic procedure (as indicated by the instructional notes at all therapeutic endoscopic codes).

### PGCS10: Coding Endoscopic Procedures

There are two types of endoscopic procedures:

- **Diagnostic** – the endoscope is used to examine the organ in order to determine the nature of the disease.
- **Therapeutic** – the endoscope is used to administer some form of treatment for the disease.

The 'endoscopy NEC' default in OPCS-4 is fibreoptic (flexible) as this accurately reflects clinical practice, i.e. where the type of endoscope has not been stated, the classification defaults the coder to a fibreoptic category.

#### Diagnostic Endoscopic Procedures

Where multiple sites are examined during a diagnostic endoscopy, a site code must be added to identify the furthest site examined.

During a diagnostic endoscopy, if a biopsy is taken at the same time as multiple sites are examined, the site of the biopsy is the only site code required. This includes where the site of biopsy is not the furthest site examined. Where multiple biopsies are taken, it is only necessary to assign a site code for the furthest point biopsied.

#### Therapeutic Endoscopic Procedures

When a therapeutic endoscopic procedure is performed and a biopsy is taken at the same time, the following codes and sequencing must be applied:

1. Therapeutic endoscopy code
2. Chapter Z site code(s) (if the therapeutic endoscopy code does not state the specific site of the procedure and where the specific site of the biopsy is different to the therapeutic endoscopy)
3. Y20 Biopsy of organ NOC\*
4. Chapter Z site code (for the site of the biopsy)

\* When an endoscopic excision is performed and a biopsy is taken at the same time, the biopsy must only be coded if it is taken from a different site (with different site code) to the excision.

Where multiple excisions, using the same method, have been performed, site codes must be assigned for each site of excision.

> **\*Y codes cannot be assigned in the primary position\***

#### Multiple Simultaneous Therapeutic Endoscopic Procedures

Where multiple therapeutic methods/techniques are used during an endoscopic procedure (e.g. laser destruction and snare resection), a body system code for each method must be assigned followed by the relevant site code(s).

Additional codes from Chapter Y may be assigned where this adds further information.

Where multiple therapeutic methods/techniques are classified using multiple body system codes, and a biopsy is taken at the same time, a code from Y20 Biopsy of organ NOC is assigned following any of the body system codes. Where one of these procedures is an excision, the biopsy must only be coded if performed on a different site to the excision.

### Examples

**Endoscopic examination of gastrointestinal tract to pylorus**
```
G45.9  Unspecified diagnostic fibreoptic endoscopic examination of upper gastrointestinal tract
Z27.3  Pylorus
```

**Fibreoptic endoscopic examination of upper gastrointestinal tract with biopsies of oesophagus and stomach**
```
G45.1  Fibreoptic endoscopic examination of upper gastrointestinal tract and biopsy of lesion of upper gastrointestinal tract
Z27.2  Stomach
```

**Fibreoptic endoscopy to stomach with removal of foreign body from oesophagus and biopsy of oesophagus**
```
G44.2  Fibreoptic removal of foreign body from upper gastrointestinal tract
Y20.9  Unspecified biopsy of organ NOC
Z27.1  Oesophagus
```

**Colonoscopy with snare excision of lesions of caecum, and biopsy of transverse colon**
```
H20.1  Fibreoptic endoscopic snare resection of lesion of colon
Z28.2  Caecum
Y20.9  Unspecified biopsy of organ NOC
Z28.4  Transverse colon
```

**Sigmoidoscopy with snare resection of lesion of sigmoid colon and biopsy of lesion of sigmoid colon**
```
H23.1  Endoscopic snare resection of lesion of lower bowel using fibreoptic sigmoidoscope
Z28.6  Sigmoid colon
```

**Fibreoptic endoscopic cauterisation of lesion of the pylorus (oesophagus and stomach examined en route)**
```
G43.3  Fibreoptic endoscopic cauterisation of lesion of upper gastrointestinal tract
Z27.3  Pylorus
```

**Colonoscopy with snare excision of lesions from caecum, transverse and sigmoid colon**
```
H20.1  Fibreoptic endoscopic snare resection of lesion of colon
Z28.2  Caecum
Z28.4  Transverse colon
Z28.6  Sigmoid colon
```

**Endoscopic fibreoptic submucosal resection and cauterisation of lesions of transverse colon performed at the same time**
```
H20.5  Fibreoptic endoscopic submucosal resection of lesion of colon
Z28.4  Transverse colon
H20.2  Fibreoptic endoscopic cauterisation of lesion of colon
Z28.4  Transverse colon
```

**Colonoscopy with Argon Plasma Coagulation (APC) of lesion of transverse colon, submucosal resection (SMR) of descending colon and transverse colon polyps, and biopsy of lesions of ascending colon**
```
H20.2  Fibreoptic endoscopic cauterisation of lesion of colon
Y17.1  Electrocauterisation of lesion of organ NOC
Z28.4  Transverse colon
H20.5  Fibreoptic endoscopic submucosal resection of lesion of colon
Z28.5  Descending colon
Z28.4  Transverse colon
Y20.3  Biopsy of lesion of organ NOC
Z28.3  Ascending colon
```

> Where multiple therapeutic methods/techniques are classified using multiple body system codes, and a biopsy is taken at the same time, a code from Y20 Biopsy of organ NOC can be assigned following any of the body system codes.

---

## Oesophagogastroduodenoscopies (OGD)

A CLO test is a biopsy of the stomach.

**OGD with CLO test:**
```
G45.1  Fibreoptic endoscopic examination of upper gastrointestinal tract and biopsy of lesion of upper gastrointestinal tract
Z27.2  Stomach
```

**OGD with CLO test and duodenal biopsy:**
```
G45.1  Fibreoptic endoscopic examination of upper gastrointestinal tract and biopsy of lesion of upper gastrointestinal tract
Z27.4  Duodenum
```

> **N.B.** This will change if a therapeutic procedure is performed (PGCS10).

### Radiofrequency Ablation of Oesophagus – RFA/HALO Treatment

**With full OGD:**
```
G43.5  Fibreoptic endoscopic destruction of lesion of upper gastrointestinal tract NEC
Y13.4  Radiofrequency controlled thermal destruction of lesion of organ NOC
Z27.1  Oesophagus
```

**With flexi oesophagoscopy only:**
```
G14.5  Fibreoptic endoscopic destruction of lesion of oesophagus NEC
Y13.4  Radiofrequency controlled thermal destruction of lesion of organ NOC
```

**With rigid oesophagoscopy only:**
```
G17.8  Other specified endoscopic extirpation of lesion of oesophagus using rigid oesophagoscope
Y13.4  Radiofrequency controlled thermal destruction of lesion of organ NOC
```

Code any biopsies as appropriate.

---

## Colonoscopies and Sigmoidoscopies

### Hot Snare Resection

Code as a snare resection + `Y13.1 Cauterisation of lesion of organ NOC`

### Hot Biopsy / Hot Biopsy of Polyp or Lesion

Code as a cauterisation of lesion:
```
H20.2  Fibreoptic endoscopic cauterisation of lesion of colon
+ site code
```

**Examples:**

**Colonoscopy with hot biopsy of sigmoid polyp:**
```
H20.2  Fibreoptic endoscopic cauterisation of lesion of colon
Z28.6  Sigmoid colon
```

**Colonoscopy with hot biopsy of sigmoid polyp with biopsy of sigmoid colon:**
```
H20.2  Fibreoptic endoscopic cauterisation of lesion of colon
Y20.9  Unspecified biopsy of organ NOC
Z28.6  Sigmoid colon
```

**Colonoscopy with hot biopsy of sigmoid polyp with biopsy of caecum:**
```
H20.2  Fibreoptic endoscopic cauterisation of lesion of colon
Z28.6  Sigmoid colon
Y20.9  Unspecified biopsy of organ NOC
Z28.2  Caecum
```

### Cold Biopsy

Code as a biopsy unless 'removed/resected/excised' with cold biopsy — then code as an excision/resection.

**Colonoscopy with cold biopsy of ascending colon polyp:**
```
H22.1  Diagnostic fibreoptic endoscopic examination of colon and biopsy of lesion of colon
Z28.3  Ascending colon
```

**Colonoscopy, ascending colon polyp removed with cold biopsy:**
```
H20.6  Fibreoptic endoscopic resection of lesion of colon NEC
Z28.3  Ascending colon
```

### Serial Biopsy

Biopsies are taken from each part of the colon, so generally the furthest point biopsied will be the furthest point examined.

### Random Biopsy

If the site of the biopsy is not known, do not assign Z28.7 Colon NEC in addition, as this does not add further information.

### Failed Intubation at Upper Gastrointestinal Tract Endoscopy

When a patient is admitted for a gastrointestinal tract endoscopy and is unable to tolerate the scope, and statements such as 'failed intubation' are documented in the medical record, the procedure must not be coded unless the point of abandonment is beyond the mouth.

If the point of abandonment is no further than the mouth, or if it has not been identified, this cannot be coded using OPCS-4. However, the coder must clarify the point of abandonment with the responsible consultant if this information has not been documented in the medical record.

The appropriate ICD-10 code(s) for the condition(s) which prompted the endoscopy (e.g. gastric ulcer, epigastric pain, gastrointestinal bleed) are assigned.

### Incomplete, Unfinished, Abandoned and Failed Procedures

Abandoned, failed or incomplete procedures must be coded to the stage reached at the abandonment of the procedure; the intention must not be coded. However, if the intervention/procedure reaches the final stage and has been unsuccessful, it must be coded as if the whole procedure has been carried out.

---

## OPCS Site Codes

| Code    | Site                         |
|---------|------------------------------|
| Z27.1   | Oesophagus                   |
| Z27.2   | Stomach                      |
| Z27.3   | Pylorus                      |
| Z27.4   | Duodenum                     |
| Z27.5   | Jejunum                      |
| Z27.6   | Ileum                        |
| Z27.7   | Small intestine              |
| O11.1   | Gastro-oesophageal junction  |
| Z28.2   | Caecum                       |
| Z28.3   | Ascending colon              |
| Z28.4   | Transverse colon             |
| Z28.5   | Descending colon             |
| Z28.6   | Sigmoid colon                |
| Z29.1   | Rectum                       |
| Z29.2   | Anus                         |
| Z29.3   | Perianal tissue              |
| Z29.4   | Colorectal/Rectosigmoid      |
| O30.1   | Hepatic flexure              |
| O30.2   | Splenic flexure              |
