import re, sqlite3, hashlib
from pathlib import Path
import fitz
from PIL import Image
import pytesseract

ROOT = Path(__file__).parent
SRC = ROOT / "data" / "sources"
DB = ROOT / "data" / "knowledge.db"

SUPPORTED = {".pdf", ".png", ".jpg", ".jpeg", ".webp", ".txt"}

def clean(s):
    return re.sub(r"\s+", " ", s or "").strip()

def chunk_text(text, size=1400, overlap=220):
    text = clean(text)
    if not text: return []
    out=[]; start=0
    while start < len(text):
        end=min(len(text), start+size)
        if end < len(text):
            cut=text.rfind(" ", start, end)
            if cut > start+600: end=cut
        out.append(text[start:end])
        if end == len(text): break
        start=max(end-overlap, start+1)
    return out

def extract(path):
    ext=path.suffix.lower()
    if ext==".pdf":
        doc=fitz.open(path)
        for pno,page in enumerate(doc,1):
            txt=clean(page.get_text("text"))
            if txt:
                for ch in chunk_text(txt): yield pno,ch
            # OCR pages where parsed text is weak; useful for tables/screenshots.
            if len(txt) < 120:
                pix=page.get_pixmap(matrix=fitz.Matrix(1.5,1.5), alpha=False)
                img=Image.frombytes("RGB", [pix.width,pix.height], pix.samples)
                ocr=clean(pytesseract.image_to_string(img))
                for ch in chunk_text(ocr): yield pno,ch
    elif ext in {".png",".jpg",".jpeg",".webp"}:
        img=Image.open(path)
        txt=clean(pytesseract.image_to_string(img))
        for ch in chunk_text(txt): yield None,ch
    elif ext==".txt":
        for ch in chunk_text(path.read_text(errors="ignore")): yield None,ch

def main():
    SRC.mkdir(parents=True,exist_ok=True)
    con=sqlite3.connect(DB)
    con.executescript("""
    DROP TABLE IF EXISTS chunks;
    DROP TABLE IF EXISTS chunks_fts;
    CREATE TABLE chunks(id INTEGER PRIMARY KEY, source TEXT, page INTEGER, chunk INTEGER, text TEXT, hash TEXT UNIQUE);
    CREATE VIRTUAL TABLE chunks_fts USING fts5(text, content='chunks', content_rowid='id');
    """)
    n=0
    for path in sorted(SRC.iterdir()):
        if path.suffix.lower() not in SUPPORTED: continue
        for idx,(page,text) in enumerate(extract(path)):
            h=hashlib.sha256(f"{path.name}|{page}|{text}".encode()).hexdigest()
            con.execute("INSERT OR IGNORE INTO chunks(source,page,chunk,text,hash) VALUES(?,?,?,?,?)",(path.name,page,idx,text,h))
            n+=1
    con.execute("INSERT INTO chunks_fts(rowid,text) SELECT id,text FROM chunks")
    con.commit(); con.close()
    print(f"Indexed {n} chunks from {len(list(SRC.iterdir()))} files into {DB}")

if __name__ == "__main__": main()
