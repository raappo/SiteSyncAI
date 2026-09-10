import tomllib
import os

path = "pyproject.toml"
with open(path, "rb") as f:
    data = tomllib.load(f)

deps = data["project"]["dependencies"]
new_deps = [
    "rapidfuzz>=3.0.0",
    "plotly>=5.18.0",
    "pandas>=2.1.0",
    "typer>=0.9.0",
    "faster-whisper>=1.0.0",
    "SpeechRecognition>=3.10.0",
    "openpyxl>=3.1.2",
    "pdfplumber>=0.10.3",
    "python-multipart>=0.0.6",
]
for d in new_deps:
    dep_name = d.split(">=")[0]
    if not any(dep_name in existing for existing in deps):
        deps.append(d)

# basic rewrite using string replace instead of tomli_w to avoid adding new dependency
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

import re
# Find dependencies list in toml
deps_str = "[\n" + ",\n".join(f'    "{d}"' for d in deps) + "\n]"
content = re.sub(r"dependencies = \[.*?\]", f"dependencies = {deps_str}", content, flags=re.DOTALL)

with open(path, "w", encoding="utf-8") as f:
    f.write(content)
