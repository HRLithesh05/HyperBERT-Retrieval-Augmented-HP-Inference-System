import re
import sys
import zipfile
from pathlib import Path
import xml.etree.ElementTree as ET

NS = {
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
}


def extract_docx_text(docx_path: Path) -> str:
    with zipfile.ZipFile(docx_path, "r") as zf:
        xml_bytes = zf.read("word/document.xml")
    root = ET.fromstring(xml_bytes)
    texts = []
    for node in root.iter():
        if node.tag == f"{{{NS['w']}}}t" and node.text:
            texts.append(node.text)
    return "\n".join(texts)


def extract_pptx_text(pptx_path: Path) -> str:
    with zipfile.ZipFile(pptx_path, "r") as zf:
        slide_names = sorted(
            [name for name in zf.namelist() if name.startswith("ppt/slides/slide") and name.endswith(".xml")]
        )
        texts = []
        for name in slide_names:
            xml_bytes = zf.read(name)
            root = ET.fromstring(xml_bytes)
            for node in root.iter():
                if node.tag == f"{{{NS['a']}}}t" and node.text:
                    texts.append(node.text)
    return "\n".join(texts)


def normalize(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def main() -> int:
    if len(sys.argv) < 3:
        print("Usage: extract_docs.py <input_path> <output_path>")
        return 1
    input_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2])
    if not input_path.exists():
        print(f"Input file not found: {input_path}")
        return 1
    if input_path.suffix.lower() == ".docx":
        text = extract_docx_text(input_path)
    elif input_path.suffix.lower() == ".pptx":
        text = extract_pptx_text(input_path)
    else:
        print("Unsupported file type. Use .docx or .pptx")
        return 1
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(normalize(text), encoding="utf-8")
    print(f"Wrote: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
