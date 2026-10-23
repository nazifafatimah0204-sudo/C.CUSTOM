"""All tools the agents can call. Tools are plain Python: they never call an LLM."""
import json
import re
from difflib import SequenceMatcher

from crewai.tools import tool

CURRENCY = r"(?:USD|EUR|GBP|PKR|CNY|RMB|AED|JPY|INR|\$|€|£)"


def _uniq(items, limit=8):
    seen, out = set(), []
    for x in items:
        x = x.strip()
        if x and x not in seen:
            seen.add(x)
            out.append(x)
    return out[:limit]


def detect_fields(text: str) -> dict:
    """Find easy-to-spot fields with regular expressions (helps the extractor agent)."""
    hs = []
    for m in re.finditer(r"\b\d{4}[. ]\d{2}(?:[. ]\d{2,4})?\b", text):
        before = text[max(0, m.start() - 6):m.start()]
        after = text[m.end():m.end() + 6].lower()
        if re.search(CURRENCY, before, re.I) or re.match(r"\s*(kg|cbm|%)", after):
            continue
        hs.append(m.group())
    ids = re.findall(
        r"(?i)\b(?:invoice|inv|b/l|bl|awb|ref(?:erence)?|po)\b\s*(?:no\.?|number|#)?\s*[:#]?\s*"
        r"((?=[A-Z0-9\-/]*\d)[A-Z0-9][A-Z0-9\-/]{4,})", text)
    return {
        "reference_numbers": _uniq(ids),
        "dates": _uniq(re.findall(
            r"\b\d{4}-\d{2}-\d{2}\b|\b\d{1,2}[ /\-](?:[A-Za-z]{3,9}|\d{1,2})[ /,\-]*\d{2,4}\b", text)),
        "possible_hs_codes": _uniq(hs),
        "amounts": _uniq(re.findall(CURRENCY + r"\s?\d[\d,]*(?:\.\d+)?", text)),
        "weights": _uniq(re.findall(
            r"(?i)\b\d[\d,]*(?:\.\d+)?\s?(?:kgs?|kilograms?|lbs?|mt|tonnes?|tons?)\b", text)),
        "package_counts": _uniq(re.findall(
            r"(?i)\b\d[\d,]*\s?(?:cartons?|ctns?|pallets?|packages?|pkgs?|boxes|crates?|bags?|drums?|pcs|pieces)\b", text)),
        "incoterms": _uniq(re.findall(r"\b(?:EXW|FCA|FAS|FOB|CFR|CIF|CPT|CIP|DAP|DPU|DDP)\b", text)),
        "container_numbers": _uniq(re.findall(r"\b[A-Z]{4}\d{7}\b", text)),
    }


def _norm(v) -> str:
    s = re.sub(r"[^a-z0-9.\s]", " ", str(v).lower())
    return re.sub(r"\s+", " ", s).strip()


def _num(v):
    m = re.search(r"-?\d[\d,]*\.?\d*", str(v))
    if not m:
        return None
    try:
        return float(m.group().replace(",", ""))
    except ValueError:
        return None


RESTRICTED = {
    "battery": "Lithium/other batteries are dangerous goods (class 9): need UN number, labels and a DG declaration. See [DG-001].",
    "lithium": "Lithium batteries are class 9 dangerous goods (UN3480/3481/3090/3091). See [DG-001].",
    "power bank": "Power banks contain lithium batteries: dangerous goods rules apply. See [DG-001].",
    "firearm": "Weapons and ammunition are restricted/prohibited: licence needed. See [RES-001].",
    "ammunition": "Ammunition is restricted/prohibited: licence needed. See [RES-001].",
    "explosive": "Explosives are restricted/prohibited: licence needed. See [RES-001].",
    "drug": "Medicines/narcotics need health-authority approval or are prohibited. See [RES-001].",
    "pharmaceutical": "Medicines need health-authority approval. See [RES-001].",
    "medicine": "Medicines need health-authority approval. See [RES-001].",
    "chemical": "Chemicals may need permits and safety data sheets. See [RES-001].",
    "ivory": "Wildlife products need CITES permits or are prohibited. See [RES-001].",
    "fur": "Wildlife products may need CITES permits. See [RES-001].",
    "meat": "Food/animal products need sanitary certificates. See [RES-001].",
    "seed": "Plants and seeds need phytosanitary certificates. See [RES-001].",
    "plant": "Plants need phytosanitary certificates. See [RES-001].",
    "food": "Food products need sanitary/health certificates. See [RES-001].",
    "alcohol": "Alcohol is restricted in many countries: licence/permit may be needed. See [RES-001].",
    "wireless": "Radio/telecom equipment often needs type approval. See [RES-001].",
    "drone": "Drones/radio equipment often need type approval or a permit. See [RES-001].",
    "counterfeit": "Counterfeit goods are prohibited. See [RES-001].",
}


def build_tools(docs: dict, kb, state, max_chars: int) -> dict:
    """Create all tools. They share the uploaded documents, the knowledge base and the run state."""

    @tool("Inspect Documents")
    def inspect_documents(document_name: str = "all") -> str:
        """Read the uploaded customs documents. Use document_name='all' to read every document in one call.
        Returns each document's text plus fields detected automatically (reference numbers, dates, HS codes,
        amounts, weights, package counts, Incoterms, container numbers)."""
        state.log("🔧 Document Extractor used tool: Inspect Documents")
        names = list(docs) if document_name.strip().lower() in ("all", "") else [document_name]
        out = []
        for n in names:
            if n not in docs:
                out.append({"document": n, "error": f"not found. Available: {list(docs)}"})
                continue
            text = docs[n]
            out.append({
                "document": n,
                "characters": len(text),
                "truncated": len(text) > max_chars,
                "text": text[:max_chars],
                "detected": detect_fields(text),
            })
        return json.dumps(out, ensure_ascii=False)

    @tool("Compare Field Across Documents")
    def compare_field(field_name: str, values_json: str) -> str:
        """Compare one field across documents. values_json must be a JSON object that maps each document name to
        the value found there, e.g. {"invoice": "612 kg", "bill_of_lading": "689 kg"}. Use "MISSING" if a document
        has no value. Returns MATCH, MINOR_DIFFERENCE or MISMATCH with details."""
        state.log(f"🔧 Cross-Document Validator used tool: Compare Field ({field_name})")
        try:
            values = json.loads(values_json)
            assert isinstance(values, dict) and len(values) >= 2
        except Exception:
            return 'ERROR: values_json must be a JSON object with at least 2 entries, e.g. {"invoice": "A", "packing_list": "B"}'
        missing = [k for k, v in values.items() if str(v).strip().lower() in ("", "missing", "null", "none", "not found")]
        present = {k: v for k, v in values.items() if k not in missing}
        note = f" Missing in: {missing}." if missing else ""
        if len(present) < 2:
            return f"{field_name}: cannot compare, value present in fewer than 2 documents.{note}"
        nums = {k: _num(v) for k, v in present.items()}
        if all(n is not None for n in nums.values()):
            lo, hi = min(nums.values()), max(nums.values())
            diff_pct = 0.0 if hi == 0 else (hi - lo) / hi * 100
            status = "MATCH" if diff_pct < 0.5 else ("MINOR_DIFFERENCE" if diff_pct < 3 else "MISMATCH")
            return f"{field_name}: {status}. Values {nums}. Difference {diff_pct:.1f}%.{note}"
        norm = {k: _norm(v) for k, v in present.items()}
        if len(set(norm.values())) == 1:
            return f"{field_name}: MATCH.{note}"
        vals = list(norm.values())
        worst = min(SequenceMatcher(None, a, b).ratio() for i, a in enumerate(vals) for b in vals[i + 1:])
        status = "MINOR_DIFFERENCE (likely formatting)" if worst >= 0.85 else "MISMATCH"
        return f"{field_name}: {status}. Text similarity {worst:.0%}. Values {dict(present)}.{note}"

    @tool("Check Line Arithmetic")
    def check_arithmetic(quantity: float, unit_price: float, stated_total: float) -> str:
        """Check one invoice line: quantity x unit_price must equal stated_total."""
        state.log("🔧 Cross-Document Validator used tool: Check Line Arithmetic")
        expected = round(quantity * unit_price, 2)
        diff = round(stated_total - expected, 2)
        if abs(diff) <= 0.01:
            return f"OK: {quantity} x {unit_price} = {expected}, matches stated total {stated_total}."
        return f"ERROR: {quantity} x {unit_price} = {expected} but stated total is {stated_total} (difference {diff})."

    @tool("Search Customs Regulations")
    def search_regulations(query: str) -> str:
        """Search the customs regulations knowledge base (RAG). Give a short, focused query such as
        'incoterm freight consistency' or 'dangerous goods batteries'. Returns the most relevant rules with IDs."""
        state.log(f"🔧 Compliance Reviewer used tool: Search Regulations (RAG) → '{query}'")
        hits = kb.search(query, k=3)
        if not hits:
            return "No relevant rule found."
        return "\n\n".join(f"(relevance {s:.2f}) {c[:650]}" for s, c in hits)

    @tool("Validate HS Code")
    def validate_hs_code(hs_code: str) -> str:
        """Check the FORMAT of an HS (tariff) code: length and chapter. It does not prove the code fits the goods."""
        state.log(f"🔧 Compliance Reviewer used tool: Validate HS Code ({hs_code})")
        digits = re.sub(r"\D", "", hs_code)
        if len(digits) < 6:
            return f"INVALID: {hs_code} has only {len(digits)} digits; at least 6 are required."
        if len(digits) > 10:
            return f"INVALID: {hs_code} has {len(digits)} digits; the longest national codes have 10."
        chapter = int(digits[:2])
        notes = []
        if not 1 <= chapter <= 97:
            notes.append(f"chapter {chapter:02d} is not a normal HS chapter (valid 01-97)")
        if chapter == 77:
            notes.append("chapter 77 is reserved")
        if len(digits) in (7, 9):
            notes.append("unusual length; national codes are usually 8 or 10 digits")
        if notes:
            return f"WARNING: {hs_code}: " + "; ".join(notes) + "."
        return f"FORMAT OK: {hs_code} (chapter {chapter:02d}, heading {digits[:4]}, subheading {digits[:6]}). Confirm it matches the goods description."

    @tool("Screen Restricted Goods")
    def screen_restricted_goods(description: str) -> str:
        """Screen a goods description for keywords linked to restricted, prohibited or dangerous goods."""
        state.log("🔧 Compliance Reviewer used tool: Screen Restricted Goods")
        d = description.lower()
        hits = [msg for key, msg in RESTRICTED.items() if key in d]
        hits = list(dict.fromkeys(hits))
        if not hits:
            return "No restricted-goods keywords found (keyword screening only, not a legal ruling)."
        return "FLAGS:\n- " + "\n- ".join(hits)

    @tool("Calculate Risk Score")
    def calculate_risk_score(critical: int, major: int, minor: int) -> str:
        """Calculate the overall risk score (0-100, higher is safer) from the number of CRITICAL, MAJOR and MINOR issues."""
        state.log("🔧 Report Writer used tool: Calculate Risk Score")
        score = max(0, 100 - 25 * int(critical) - 10 * int(major) - 3 * int(minor))
        if score >= 85:
            level = "LOW RISK - ready to proceed"
        elif score >= 60:
            level = "MEDIUM RISK - corrections needed"
        elif score >= 35:
            level = "HIGH RISK - do not file until fixed"
        else:
            level = "CRITICAL RISK - serious problems"
        state.risk = {"score": score, "level": level, "critical": int(critical), "major": int(major), "minor": int(minor)}
        return f"Risk score: {score}/100. Level: {level}."

    return {
        "inspect_documents": inspect_documents,
        "compare_field": compare_field,
        "check_arithmetic": check_arithmetic,
        "search_regulations": search_regulations,
        "validate_hs_code": validate_hs_code,
        "screen_restricted_goods": screen_restricted_goods,
        "calculate_risk_score": calculate_risk_score,
    }
