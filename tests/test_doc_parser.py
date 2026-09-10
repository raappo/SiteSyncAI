"""
Tests for the document parser module.
"""
import pytest
from pathlib import Path

class TestDocParser:
    """Tests for the multimodal document parser."""

    def test_parse_plain_text_passthrough(self, tmp_path):
        """Plain text files should be passed through directly."""
        from sitesync.ingestion.doc_parser import parse_file
        txt_file = tmp_path / "test_report.txt"
        txt_file.write_text("Civil team completed 60% excavation at Zone A today.", encoding="utf-8")
        result = parse_file(txt_file.read_bytes(), txt_file.name)
        assert result.error is None or result.error == ""
        assert "excavation" in result.raw_text.lower()

    def test_parse_xlsx_returns_text(self, tmp_path):
        """Excel files should be parsed into text representation."""
        pytest.importorskip("openpyxl")
        import openpyxl
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Progress"
        ws.append(["Activity", "Progress", "Date"])
        ws.append(["Piping spool weld", "35%", "2026-09-10"])
        xlsx_path = tmp_path / "test.xlsx"
        wb.save(str(xlsx_path))
        
        from sitesync.ingestion.doc_parser import parse_file
        result = parse_file(xlsx_path.read_bytes(), xlsx_path.name)
        assert result.raw_text != ""
        assert result.evidence_type == "spreadsheet"

    def test_parse_image_without_azure_di_returns_error(self, tmp_path):
        """Image files without Azure DI should return an error, not crash."""
        # Create a minimal PNG (1x1 pixel)
        img_path = tmp_path / "test.png"
        # Write minimal valid PNG bytes
        import struct, zlib
        def write_png(path):
            sig = b'\x89PNG\r\n\x1a\n'
            def chunk(name, data):
                c = struct.pack('>I', len(data)) + name + data
                return c + struct.pack('>I', zlib.crc32(name + data) & 0xffffffff)
            ihdr = struct.pack('>IIBBBBB', 1, 1, 8, 2, 0, 0, 0)
            raw = b'\x00\xff\xff\xff'  # 1 pixel, RGB
            idat = zlib.compress(raw)
            path.write_bytes(sig + chunk(b'IHDR', ihdr) + chunk(b'IDAT', idat) + chunk(b'IEND', b''))
        write_png(img_path)
        
        from sitesync.ingestion.doc_parser import parse_file
        result = parse_file(img_path.read_bytes(), img_path.name)
        # Should not crash, should return an error document
        assert result is not None
        # Image without Azure DI should indicate failure gracefully
        assert result.error is not None or result.raw_text == '' or result.raw_text == ""

    def test_parse_nonexistent_file_returns_error(self):
        """Nonexistent files should return an error document."""
        from sitesync.ingestion.doc_parser import parse_file
        result = parse_file(b"", "file.txt")
        assert result.error is not None or result.raw_text == ''
        assert result.raw_text == ""
