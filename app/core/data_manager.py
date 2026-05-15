from pathlib import Path
import csv
import pandas as pd
import shutil
import datetime
from app.models.valid_file import file_model, df_to_pydantic, mappings_to_pydantic_header, validate_pydantic_model, required_aliases

input_docs = Path("input_docs")
approved_docs = Path("approved_docs")
output_docs = Path("output_docs")
mismatch_reports = output_docs / Path("mismatch_reports")


def validate_file(file_name, df, mappings=None, row_correction=None, new_file_name=None):
    if new_file_name:
        file_name = new_file_name

    team, month, year = extract_team_month_year(file_name)
    if not team or not month or not year:
        return {
            "status": "requires valid team_month_year",
            "error": "Filename must be in the format team_month_year.ext (e.g., sales_january_2024.csv)."
        }

    try: 
        valid_month = datetime.strptime(month, "%B").month
    except (ValueError, TypeError):
        return {
            "status": "requires valid month",
            "error": f"Invalid month '{month}' in filename. Month should be a full month name (e.g., January)."
        }

    try: 
        valid_year = datetime.strptime(year, "%Y").year
    except (ValueError, TypeError):
        return {
            "status": "requires valid year",
            "error": f"Invalid year '{year}' in filename. Year should be a 4-digit year (e.g., 2023)."
        }

    if valid_year < 2000 or valid_year > datetime.now().year + 1:
        return {
            "status": "requires valid year",
            "error": f"Year '{year}' in filename is out of valid range. Year should be between 2000 and {datetime.now().year + 1}."
        }

    header, rows = df_to_pydantic(df)
    actual_header = header
    if mappings:
        actual_header = [mappings[col] if col in mappings else col for col in header]
        rows = mappings_to_pydantic_header(mappings, rows)

    if not header:
        return {
            "status": "error",
            "error": "Missing header row."
        }

    missing = [f for f in required_aliases if f not in actual_header]
    if missing:
        return {
            "status": "requires_mappings",
            "missing_fields": missing,
            "actual_fields": actual_header
        }

    corrections = row_correction.get("corrections", {}) if row_correction else {}
    for index, row in enumerate(rows):
        if row_correction and index == row_correction.get("index"):
            for col, new_val in corrections.items():
                row[col] = new_val

    invalid_rows = validate_pydantic_model(rows)

    if invalid_rows:
        return {
            "status": "requires_row_fixes",
            "invalid_rows": invalid_rows
        }

    return {
        "status": "success",
        "message": "File is valid and has been moved to approved documents.",
        "file_name": file_name,
        "file_month": valid_month,
        "file_year": valid_year,
        "file_team": team,
        "header": actual_header,
        "rows": rows
    }


def extract_team_month_year(file_name):
    parts = file_name.split("_")
    if len(parts) >= 3:
        team = parts[0].strip()
        month = parts[1].strip()
        year = parts[2].split(".")[0].strip()
    else:
        team = None
        month = None
        year = None

    return team, month, year


def process_file(file_path):
    path_obj = Path(file_path)
    if path_obj.suffix.lower() in [".csv", ".txt"]:
        df = pd.read_csv(path_obj, sep=None, engine="python")
    elif path_obj.suffix.lower() in [".xlsx", ".xls"]:
        df = pd.read_excel(path_obj)
    else:
        raise ValueError(f"Unsupported file format for file {path_obj.name}.")

    return df


def load_data():
    files = list(approved_docs.glob("*"))
    if not files:
        print("No approved files found. Please validate and clean your files first.")
        return pd.DataFrame()
    return pd.concat([pd.read_csv(file) if file.suffix.lower() in [".csv", ".txt"] else pd.read_excel(file) for file in files], ignore_index=True)


def gen_mismatch_report(groupBy):
    mismatch_reports.mkdir(parents=True, exist_ok=True)
    df = load_data()

    if df.empty:
        print("No data available to generate mismatch report.")
        return

    df['delta'] = df['Expected Records Deleted'] - df['Actual Records Deleted']
    mismatches = df[df['delta'] != 0]

    for group_value, group in mismatches.groupby(groupBy):
        output_file = mismatch_reports / f"mismatch_report_{group_value}.csv"
        group.to_csv(output_file, index=False)