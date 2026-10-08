#!/usr/bin/env python3
"""Extract reviewable cell evidence from an Excel .xlsx workbook."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path, PurePosixPath
from xml.etree import ElementTree
from zipfile import BadZipFile, ZipFile

MAIN_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
OFFICE_REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PACKAGE_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
NS = {"m": MAIN_NS, "r": OFFICE_REL_NS, "p": PACKAGE_REL_NS}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Extract non-empty cells from an .xlsx workbook without uploading it "
            "or requiring third-party Python packages."
        )
    )
    parser.add_argument("workbook", type=Path)
    parser.add_argument(
        "--format",
        choices=("markdown", "json"),
        default="markdown",
        help="Output format. Defaults to markdown.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Write to this file instead of standard output.",
    )
    parser.add_argument(
        "--max-rows-per-sheet",
        type=int,
        default=0,
        help="Limit emitted non-empty rows per sheet. Zero emits every row.",
    )
    return parser.parse_args()


def xml_root(archive: ZipFile, name: str) -> ElementTree.Element:
    return ElementTree.fromstring(archive.read(name))


def load_shared_strings(archive: ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in archive.namelist():
        return []

    root = xml_root(archive, "xl/sharedStrings.xml")
    return [
        "".join(text.text or "" for text in item.iterfind(".//m:t", NS))
        for item in root.findall("m:si", NS)
    ]


def normalize_part_path(base: str, target: str) -> str:
    if target.startswith("/"):
        return target.lstrip("/")
    return str(PurePosixPath(base, target))


def relationship_targets(
    archive: ZipFile, relationship_path: str, base: str
) -> dict[str, str]:
    root = xml_root(archive, relationship_path)
    return {
        relationship.attrib["Id"]: normalize_part_path(base, relationship.attrib["Target"])
        for relationship in root
    }


def column_index(cell_reference: str) -> int:
    letters = re.match(r"[A-Z]+", cell_reference)
    if not letters:
        return 0

    result = 0
    for letter in letters.group(0):
        result = result * 26 + ord(letter) - ord("A") + 1
    return result


def cell_value(cell: ElementTree.Element, shared_strings: list[str]) -> str:
    cell_type = cell.attrib.get("t")
    value_element = cell.find("m:v", NS)
    formula_element = cell.find("m:f", NS)

    if cell_type == "s" and value_element is not None:
        value = shared_strings[int(value_element.text or "0")]
    elif cell_type == "inlineStr":
        value = "".join(
            text.text or "" for text in cell.iterfind(".//m:is//m:t", NS)
        )
    elif cell_type == "b" and value_element is not None:
        value = "true" if value_element.text == "1" else "false"
    elif value_element is not None:
        value = value_element.text or ""
    else:
        value = ""

    if formula_element is None:
        return value

    formula = f"={formula_element.text or ''}"
    return f"{formula} -> {value}" if value else formula


def extract_workbook(path: Path, max_rows_per_sheet: int) -> dict[str, object]:
    if max_rows_per_sheet < 0:
        raise ValueError("--max-rows-per-sheet cannot be negative")

    with ZipFile(path) as archive:
        shared_strings = load_shared_strings(archive)
        workbook = xml_root(archive, "xl/workbook.xml")
        relationships = relationship_targets(
            archive, "xl/_rels/workbook.xml.rels", "xl"
        )
        media = sorted(
            name for name in archive.namelist() if name.startswith("xl/media/")
        )
        sheets: list[dict[str, object]] = []

        sheet_collection = workbook.find("m:sheets", NS)
        if sheet_collection is None:
            raise ValueError("Workbook does not contain a sheets collection")

        for sheet in sheet_collection:
            relationship_id = sheet.attrib[f"{{{OFFICE_REL_NS}}}id"]
            worksheet_path = relationships[relationship_id]
            worksheet = xml_root(archive, worksheet_path)
            extracted_rows: list[dict[str, object]] = []
            total_nonempty_rows = 0

            for row in worksheet.findall(".//m:sheetData/m:row", NS):
                cells = []
                for cell in row.findall("m:c", NS):
                    value = cell_value(cell, shared_strings)
                    if value == "":
                        continue
                    reference = cell.attrib.get("r", "")
                    cells.append(
                        {
                            "reference": reference,
                            "column": column_index(reference),
                            "value": value,
                        }
                    )

                if not cells:
                    continue

                total_nonempty_rows += 1
                if max_rows_per_sheet == 0 or len(extracted_rows) < max_rows_per_sheet:
                    extracted_rows.append(
                        {"row": int(row.attrib.get("r", "0")), "cells": cells}
                    )

            sheets.append(
                {
                    "name": sheet.attrib["name"],
                    "totalNonemptyRows": total_nonempty_rows,
                    "emittedNonemptyRows": len(extracted_rows),
                    "rows": extracted_rows,
                }
            )

    return {
        "workbook": path.name,
        "sourcePath": str(path),
        "embeddedMedia": media,
        "sheets": sheets,
    }


def escape_markdown(value: str) -> str:
    return value.replace("\\", "\\\\").replace("|", "\\|").replace("\n", "<br>")


def to_markdown(extraction: dict[str, object]) -> str:
    lines = [
        f"# Workbook evidence: {extraction['workbook']}",
        "",
        "> Generated locally from the workbook. Review for sensitive data before "
        "committing or sharing.",
        "",
    ]

    media = extraction["embeddedMedia"]
    if media:
        lines.extend(
            [
                "## Embedded media",
                "",
                "Embedded images are listed but not interpreted by this extractor:",
                "",
                *[f"- `{name}`" for name in media],
                "",
            ]
        )

    for sheet in extraction["sheets"]:
        lines.extend(
            [
                f"## Sheet: {sheet['name']}",
                "",
                f"Non-empty rows: {sheet['totalNonemptyRows']}; emitted: "
                f"{sheet['emittedNonemptyRows']}.",
                "",
            ]
        )
        rows = sheet["rows"]
        if not rows:
            lines.extend(["_No cell values found._", ""])
            continue

        lines.extend(["| Row | Cell | Value |", "|---:|---|---|"])
        for row in rows:
            first = True
            for cell in row["cells"]:
                row_number = str(row["row"]) if first else ""
                lines.append(
                    f"| {row_number} | `{cell['reference']}` | "
                    f"{escape_markdown(cell['value'])} |"
                )
                first = False
        lines.append("")

    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    try:
        extraction = extract_workbook(args.workbook, args.max_rows_per_sheet)
    except FileNotFoundError:
        raise SystemExit(f"Workbook not found: {args.workbook}")
    except BadZipFile:
        raise SystemExit(f"Not a valid .xlsx file: {args.workbook}")
    except (KeyError, ElementTree.ParseError, ValueError) as error:
        raise SystemExit(f"Could not extract workbook: {error}")

    if args.format == "json":
        rendered = json.dumps(extraction, indent=2, ensure_ascii=False) + "\n"
    else:
        rendered = to_markdown(extraction) + "\n"

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
