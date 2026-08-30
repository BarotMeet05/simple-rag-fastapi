"""Quick parser smoke test."""
from app.services.parser_service import parse_txt, parse_pdf
import fitz

# Test TXT
txt_result = parse_txt(b"The coverage limit is $2 million. The deductible is $25,000.")
print(f"TXT: pages={txt_result.total_pages} chars={txt_result.total_chars}")
print(f"     text: {txt_result.full_text[:60]!r}")

# Test PDF
doc = fitz.open()
page = doc.new_page()
page.insert_text((72, 100), "Coverage limit is $2 million.", fontsize=12)
page.insert_text((72, 130), "The deductible is $25,000.", fontsize=12)
pdf_bytes = doc.tobytes()
doc.close()

pdf_result = parse_pdf(pdf_bytes)
print(f"PDF: pages={pdf_result.total_pages} chars={pdf_result.total_chars}")
print(f"     text: {pdf_result.full_text[:80]!r}")

# Test real TXT files
from pathlib import Path
for fname in ["company_handbook.txt", "engineering_policy.txt", "product_documentation.txt"]:
    p = Path("data/documents") / fname
    if p.exists():
        result = parse_txt(p.read_bytes())
        print(f"{fname}: chars={result.total_chars}")
    else:
        print(f"MISSING: {fname}")

print("Parser smoke test PASSED")
