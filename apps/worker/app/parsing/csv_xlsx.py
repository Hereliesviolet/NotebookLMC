"""CSV/XLSX parsing via pandas.

Tables are emitted as their own chunks in Markdown format (architecture doc
§14.5), split into row batches so a single huge spreadsheet doesn't become
one unusably large chunk.
"""

import io

import pandas as pd

from app.parsing.sanitize import sanitize_text
from app.parsing.types import ParsedSection

_ROWS_PER_CHUNK = 50


def _dataframe_to_sections(
    df: "pd.DataFrame", sheet_name: str | None = None
) -> list[ParsedSection]:
    sections: list[ParsedSection] = []
    total_rows = len(df)
    for start in range(0, total_rows, _ROWS_PER_CHUNK):
        batch = df.iloc[start : start + _ROWS_PER_CHUNK]
        heading = sanitize_text(sheet_name) if sheet_name else None
        sections.append(
            ParsedSection(
                text=sanitize_text(batch.to_markdown(index=False)),
                heading=heading,
                chunk_type="table",
                metadata={
                    "row_start": start,
                    "row_end": min(start + _ROWS_PER_CHUNK, total_rows) - 1,
                },
            )
        )
    return sections


def parse_csv(data: bytes) -> list[ParsedSection]:
    df = pd.read_csv(io.BytesIO(data))
    return _dataframe_to_sections(df)


def parse_xlsx(data: bytes) -> list[ParsedSection]:
    sheets = pd.read_excel(io.BytesIO(data), sheet_name=None)
    sections: list[ParsedSection] = []
    for sheet_name, df in sheets.items():
        sections.extend(_dataframe_to_sections(df, sheet_name=sheet_name))
    return sections
