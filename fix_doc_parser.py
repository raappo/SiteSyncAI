from pathlib import Path

# Fix test_doc_parser.py
test_file = Path("tests/test_doc_parser.py")
content = test_file.read_text()
content = content.replace("result = parse_file(str(txt_file))", 'result = parse_file(txt_file.read_bytes(), txt_file.name)')
content = content.replace("result = parse_file(str(xlsx_path))", 'result = parse_file(xlsx_path.read_bytes(), xlsx_path.name)')
content = content.replace("result = parse_file(str(img_path))", 'result = parse_file(img_path.read_bytes(), img_path.name)')
content = content.replace('result = parse_file("/nonexistent/path/file.txt")', 'result = parse_file(b"", "file.txt")')
test_file.write_text(content)

# Fix 1_time_agent.py
agent_file = Path("frontend/pages/1_time_agent.py")
content = agent_file.read_text(encoding="utf-8")
content = content.replace("parsed_doc = parse_file(tmp_path)", "parsed_doc = parse_file(Path(tmp_path).read_bytes(), uploaded_file.name)")
agent_file.write_text(content, encoding="utf-8")

print("Fixed doc_parser usages.")
