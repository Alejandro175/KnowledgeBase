from pathlib import Path
from langchain_text_splitters import RecursiveCharacterTextSplitter

class FileReader:
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separators = ["\n\n"]

    def _read(self, file_path: str) -> str:
        p = Path(file_path)
        if not p.exists():
            raise FileNotFoundError(f"File non trovato: {p.resolve()}")
        return p.read_text(encoding="utf-8")
    
    def _clear_text(self, text: str) -> str:
        return text.replace("[.]", ".").strip()

    def run(self, file_path: str) -> list[str]:
        text = self._read(file_path)
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            separators=self.separators,
        )

        text_clear = self._clear_text(text)
        return splitter.split_text(text_clear)
        
    