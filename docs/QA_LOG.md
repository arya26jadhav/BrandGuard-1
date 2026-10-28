# QA Log: Content & Image Validation Samples

> **Tester:** Alok (Member 3)  
> **Date:** 2026-10-28  
> **Branch:** `feature/member3-qa-log`  
> **Validator:** `backend/services/image_validator.py`  
> **Python:** 3.12.10 (`backend/venv`)  

---

## Summary Table

| Sample | Check | Expected | Actual | Flag | Matches expected? |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `violation_sample.txt` | Prohibited word detection: `"miracle"` | Flagged as critical (`prohibited_word`) | Not implemented | N/A | No |
| `violation_sample.txt` | Prohibited word detection: `"CURE"` | Flagged as critical (`prohibited_word`) | Not implemented | N/A | No |
| `violation_sample.txt` | Prohibited claim detection: `"100% effective"` | Flagged as critical (`prohibited_claim`) | Not implemented | N/A | No |
| `violation_sample.txt` | Unsupported claim detection: `"dermatologist recommended"` | Flagged as warning (`unsupported_claim`) | Not implemented | N/A | No |
| `violation_sample.txt` | Missing disclaimer detection: `"Results may vary..."` | Flagged as warning (`missing_disclaimer`) | Not implemented | N/A | No |
| `low_contrast_ad.png` | Text contrast ratio compliance (WCAG AA min 4.5:1) | Fail WCAG AA (< 2.0:1) | Fail — ratio **1.50:1** (text `#D3D2D2`, bg `#FEFEFE`); Status: `fail`, Severity: `critical` | TP | Yes |
| `low_contrast_ad.png` | Logo variant match (pHash vs `approved_logo_v3.2.png`) | Flagged as mismatch | Mismatch — pHash distance **24** (> max distance 8); Status: `mismatch`, Severity: `warning` | TP | Yes |
| `low_contrast_ad.png` | Brand colour adherence check | Pass (neutral background/text allowed) | Pass — no off-brand colours detected | TN | Yes |
| `approved_logo_v3.2.png` | Logo variant match (**self-comparison**) | Approved (distance <= 8) | Approved — pHash distance **0** (*Note: Self-comparison proves the function runs; it does not prove it detects variants*) | TN | Yes |
| `approved_logo_v3.2.png` | Brand colour adherence check | Pass (within approved palette `#2D5F3F`, `#B8E6D5` or neutral) | Pass — dominant colours match brand palette | TN | Yes |
| (computed: #2D5F3F on #FFFFFF) | Text contrast WCAG AA: Primary Green `#2D5F3F` on White `#FFFFFF` | Pass WCAG AA (>= 4.5:1) | Pass — calculated ratio **7.45:1**; Status: `pass` | TN | Yes |

---

## Detailed Check Verification

### Text Checks (`violation_sample.txt`)
- **Status:** **Not implemented** in Member 3's service (`backend/services/image_validator.py`).
- **Owner:** Arya (Member 1 - Rules engine & AI Layer).
- **Notes:** The 5 planted violations in `test_data/content_samples/violation_sample.txt` are documented in `test_data/expected_outputs/violation_sample_findings.json` as test specifications. There is no automated test runner in Member 3's scope currently executing text checks against this file.

### Image Checks (`backend/services/image_validator.py`)
Ran with:
```powershell
python -c "from backend.services.image_validator import ImageValidator, measure_text_contrast; v = ImageValidator(); ..."
```

1. **`measure_text_contrast('test_data/images/low_contrast_ad.png')`**
   - **File / Function:** `backend/services/image_validator.py` -> `measure_text_contrast()`
   - **Output:** `{'text': '#D3D2D2', 'background': '#FEFEFE', 'ratio': 1.5, 'status': 'fail', 'severity': 'critical'}`
   - **Classification:** **TP** (True Positive: defect present and successfully caught).

2. **`check_logo_match('test_data/images/low_contrast_ad.png')`**
   - **File / Function:** `backend/services/image_validator.py` -> `ImageValidator.check_logo_match()`
   - **Output:** `[{'type': 'logo_version_check', 'status': 'mismatch', 'distance': 24, 'severity': 'warning', 'suggested_fix': 'Replace with the approved logo v3.2 from the asset library'}]`
   - **Classification:** **TP** (True Positive: non-matching image flagged).

3. **`check_brand_colours('test_data/images/low_contrast_ad.png')`**
   - **File / Function:** `backend/services/image_validator.py` -> `ImageValidator.check_brand_colours()`
   - **Output:** `[{'type': 'colour_check', 'status': 'pass', 'off_brand_colours': [], 'severity': None, 'suggested_fix': None}]`
   - **Classification:** **TN** (True Negative: white/light grey ad passed without false off-brand flags).

4. **`check_logo_match('test_data/images/approved_logo_v3.2.png')`**
   - **File / Function:** `backend/services/image_validator.py` -> `ImageValidator.check_logo_match()`
   - **Output:** `[{'type': 'logo_version_check', 'status': 'approved', 'distance': 0, 'severity': None, 'suggested_fix': None}]`
   - **Classification:** **TN** (True Negative: approved logo passed).
   - **Self-comparison note:** Comparing the approved logo file against itself confirms that the perceptual hashing calculation runs and outputs distance 0. It does not evaluate detection of real subtle logo variants (such as outdated subtext, slight color shifts, or minor re-arrangements).

5. **`check_brand_colours('test_data/images/approved_logo_v3.2.png')`**
   - **File / Function:** `backend/services/image_validator.py` -> `ImageValidator.check_brand_colours()`
   - **Output:** `[{'type': 'colour_check', 'status': 'pass', 'off_brand_colours': [], 'severity': None, 'suggested_fix': None}]`
   - **Classification:** **TN** (True Negative: approved logo uses Primary Green `#2D5F3F`).

6. **`check_text_contrast('#2D5F3F', '#FFFFFF')`**
   - **File / Function:** `backend/services/image_validator.py` -> `ImageValidator.check_text_contrast()`
   - **Output:** `[{'type': 'contrast_check', 'status': 'pass', 'ratio': 7.45, 'severity': None, 'suggested_fix': None}]`
   - **Classification:** **TN** (True Negative: compliant ratio meets WCAG AA 4.5:1 threshold).

---

## Known Gaps

1. **Unsupported-Claim Detection:**
   - Determining whether a claim (e.g., *"dermatologist recommended"*) is backed by approved brand facts requires integration with the facts database and AI evaluation layer (`backend/app/services/ai_check.py`). It cannot be checked deterministically with local visual rules.

2. **Missing-Disclaimer Detection:**
   - Content-aware checks for mandatory disclaimers (e.g., skincare disclaimer for product ads) require guideline parsing and context matching in the text rules engine, which is not yet linked to the QA sample runner.

3. **Distorted-Logo Detection:**
   - Perceptual hashing (`imagehash.phash`) can distinguish completely different images (distance 24) or identical files (distance 0), but is brittle or unreliable for aspect-ratio distortions, rotations, cropping, or subtle background changes. OpenCLIP visual embedding similarity is planned to address this gap.
