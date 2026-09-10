"""
Script to generate the synthetic piping progress spreadsheet (XLSX).
Run with: uv run python scripts/generate_xlsx.py
"""
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def main():
    try:
        import openpyxl
        from openpyxl.styles import Alignment, Font, PatternFill
    except ImportError:
        print("openpyxl not installed. Run: uv add openpyxl")
        sys.exit(1)

    wb = openpyxl.Workbook()

    # ── Tab 1: Spool Tracker ────────────────────────────────────────────────
    ws1 = wb.active
    ws1.title = "Piping Spool Tracker"

    header_fill = PatternFill("solid", fgColor="1F4E79")
    header_font = Font(color="FFFFFF", bold=True)
    alt_fill = PatternFill("solid", fgColor="D6E4F0")

    headers_tab1 = [
        "Spool No.", "ISO Ref", "Line No.", "Size (inch)",
        "Material", "Fab Status", "Erection Status", "Weld Joints Total",
        "Joints Done", "Joints Pending", "Erection %", "Hydro Test",
        "Date Erected", "Remarks"
    ]
    ws1.append(headers_tab1)
    for cell in ws1[1]:
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", wrap_text=True)

    spool_data = [
        ["SP-101-001", "ISO-24HO-101-001", "24-HO-101", 6, "CS A106 Gr.B", "COMPLETE", "COMPLETE", 3, 3, 0, 100, "PENDING", "10-Feb-2024", ""],
        ["SP-101-002", "ISO-24HO-101-002", "24-HO-101", 6, "CS A106 Gr.B", "COMPLETE", "COMPLETE", 4, 4, 0, 100, "PENDING", "11-Feb-2024", ""],
        ["SP-101-003", "ISO-24HO-101-003", "24-HO-101", 6, "CS A106 Gr.B", "COMPLETE", "IN PROGRESS", 3, 2, 1, 67, "NOT STARTED", "12-Feb-2024", "1 joint pending - alignment"],
        ["SP-101-004", "ISO-24HO-101-004", "24-HO-101", 6, "CS A106 Gr.B", "COMPLETE", "IN PROGRESS", 4, 0, 4, 0, "NOT STARTED", "", "Waiting for SP-101-003"],
        ["SP-101-005", "ISO-24HO-101-005", "24-HO-101", 6, "CS A106 Gr.B", "COMPLETE", "NOT STARTED", 3, 0, 3, 0, "NOT STARTED", "", ""],
        ["SP-101-006", "ISO-24HO-101-006", "24-HO-101", 6, "CS A106 Gr.B", "COMPLETE", "NOT STARTED", 2, 0, 2, 0, "NOT STARTED", "", ""],
        ["SP-101-007", "ISO-24HO-101-007", "24-HO-101", 6, "CS A106 Gr.B", "IN PROGRESS", "NOT STARTED", 4, 0, 4, 0, "NOT STARTED", "", "Fab 80% done"],
        ["SP-201-001", "ISO-24WI-201-001", "24-WI-201", 3, "SS 316L", "COMPLETE", "COMPLETE", 2, 2, 0, 100, "COMPLETE", "05-Feb-2024", ""],
        ["SP-201-002", "ISO-24WI-201-002", "24-WI-201", 3, "SS 316L", "COMPLETE", "COMPLETE", 2, 2, 0, 100, "COMPLETE", "06-Feb-2024", ""],
        ["SP-201-003", "ISO-24WI-201-003", "24-WI-201", 3, "SS 316L", "COMPLETE", "IN PROGRESS", 3, 2, 1, 67, "NOT STARTED", "12-Feb-2024", "SS wire shortage"],
        ["SP-201-004", "ISO-24WI-201-004", "24-WI-201", 3, "SS 316L", "COMPLETE", "NOT STARTED", 2, 0, 2, 0, "NOT STARTED", "", "Waiting consumables PR-2024-089"],
        ["SP-201-005", "ISO-24WI-201-005", "24-WI-201", 3, "SS 316L", "COMPLETE", "NOT STARTED", 3, 0, 3, 0, "NOT STARTED", "", ""],
        ["SP-201-006", "ISO-24WI-201-006", "24-WI-201", 3, "SS 316L", "COMPLETE", "NOT STARTED", 2, 0, 2, 0, "NOT STARTED", "", ""],
        ["SP-201-007", "ISO-24WI-201-007", "24-WI-201", 3, "SS 316L", "IN PROGRESS", "NOT STARTED", 2, 0, 2, 0, "NOT STARTED", "", ""],
        ["SP-201-008", "ISO-24WI-201-008", "24-WI-201", 3, "SS 316L", "NOT STARTED", "NOT STARTED", 2, 0, 2, 0, "NOT STARTED", "", ""],
    ]

    for i, row in enumerate(spool_data, start=2):
        ws1.append(row)
        if i % 2 == 0:
            for cell in ws1[i]:
                cell.fill = alt_fill

    # Set column widths
    col_widths = [12, 20, 14, 10, 16, 14, 16, 14, 12, 14, 12, 12, 16, 30]
    for col_idx, width in enumerate(col_widths, start=1):
        ws1.column_dimensions[openpyxl.utils.get_column_letter(col_idx)].width = width

    # ── Tab 2: Weld Summary ─────────────────────────────────────────────────
    ws2 = wb.create_sheet("Weld Log Summary")
    weld_headers = ["Date", "Line No.", "Spool", "Joint No.", "Welder ID",
                    "WPS No.", "Weld Type", "Joint Dia (mm)", "Status", "RT/UT Result"]
    ws2.append(weld_headers)
    for cell in ws2[1]:
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center")

    weld_data = [
        ["10-Feb-2024", "24-HO-101", "SP-101-001", "J-001", "WLD-04", "WPS-CS-01", "BW", 168.3, "ACCEPTED", "RT-PASS"],
        ["10-Feb-2024", "24-HO-101", "SP-101-001", "J-002", "WLD-04", "WPS-CS-01", "BW", 168.3, "ACCEPTED", "RT-PASS"],
        ["11-Feb-2024", "24-HO-101", "SP-101-001", "J-003", "WLD-06", "WPS-CS-01", "BW", 168.3, "ACCEPTED", "RT-PASS"],
        ["11-Feb-2024", "24-HO-101", "SP-101-002", "J-004", "WLD-04", "WPS-CS-01", "BW", 168.3, "ACCEPTED", "RT-PASS"],
        ["11-Feb-2024", "24-HO-101", "SP-101-002", "J-005", "WLD-06", "WPS-CS-01", "BW", 168.3, "ACCEPTED", "RT-PASS"],
        ["12-Feb-2024", "24-HO-101", "SP-101-002", "J-006", "WLD-04", "WPS-CS-01", "BW", 168.3, "ACCEPTED", "PENDING"],
        ["12-Feb-2024", "24-HO-101", "SP-101-002", "J-007", "WLD-06", "WPS-CS-01", "BW", 168.3, "ACCEPTED", "PENDING"],
        ["13-Feb-2024", "24-HO-101", "SP-101-003", "J-008", "WLD-04", "WPS-CS-01", "BW", 168.3, "ACCEPTED", "PENDING"],
        ["14-Feb-2024", "24-HO-101", "SP-101-003", "J-009", "WLD-06", "WPS-CS-01", "BW", 168.3, "IN PROGRESS", "NA"],
        ["05-Feb-2024", "24-WI-201", "SP-201-001", "J-101", "WLD-08", "WPS-SS-01", "BW", 88.9, "ACCEPTED", "RT-PASS"],
        ["06-Feb-2024", "24-WI-201", "SP-201-001", "J-102", "WLD-08", "WPS-SS-01", "BW", 88.9, "ACCEPTED", "RT-PASS"],
        ["07-Feb-2024", "24-WI-201", "SP-201-002", "J-103", "WLD-09", "WPS-SS-01", "BW", 88.9, "ACCEPTED", "RT-PASS"],
        ["08-Feb-2024", "24-WI-201", "SP-201-002", "J-104", "WLD-09", "WPS-SS-01", "BW", 88.9, "ACCEPTED", "RT-PASS"],
        ["12-Feb-2024", "24-WI-201", "SP-201-003", "J-105", "WLD-08", "WPS-SS-01", "BW", 88.9, "ACCEPTED", "PENDING"],
        ["13-Feb-2024", "24-WI-201", "SP-201-003", "J-106", "WLD-08", "WPS-SS-01", "BW", 88.9, "IN PROGRESS", "NA"],
    ]
    for row in weld_data:
        ws2.append(row)

    # ── Tab 3: Daily Manpower & Progress ────────────────────────────────────
    ws3 = wb.create_sheet("Daily Manpower")
    mp_headers = ["Date", "Discipline", "Supervisor", "Fitters", "Welders",
                  "Helpers", "Total", "Target Joints", "Achieved Joints", "Remarks"]
    ws3.append(mp_headers)
    for cell in ws3[1]:
        cell.fill = header_fill
        cell.font = header_font

    mp_data = [
        ["10-Feb-2024", "Piping", "R. Mishra", 8, 6, 10, 24, 4, 3, "Good progress"],
        ["11-Feb-2024", "Piping", "R. Mishra", 8, 6, 10, 24, 4, 4, "Target met"],
        ["12-Feb-2024", "Piping", "R. Mishra", 8, 6, 12, 26, 4, 2, "Alignment issue NE flange"],
        ["13-Feb-2024", "Piping", "R. Mishra", 8, 5, 12, 25, 4, 1, "1 welder absent"],
        ["14-Feb-2024", "Piping", "R. Mishra", 8, 6, 12, 26, 4, 3, "SS consumable shortage PM"],
    ]
    for row in mp_data:
        ws3.append(row)

    # Save
    out_path = Path(__file__).parent.parent / "data" / "piping_progress.xlsx"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(str(out_path))
    print(f"✅ Generated: {out_path}")


if __name__ == "__main__":
    main()
