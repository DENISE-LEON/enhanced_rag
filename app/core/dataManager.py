from pathlib import Path
import csv
import pandas as pd
import shutil

input_docs = Path("input_docs")
approved_docs = Path("approved_docs")
output_docs = Path("output_docs")
mismatch_reports = output_docs / Path("mismatch_reports")

#doc validate + clean -> approved_docs

#helpers
REQUIRED_COLUMNS = [
    "Table Name", 
    "No of Records Before", 
    "No of Records After", 
    "Expected Records Deleted", 
    "Actual Records Deleted"]

#file validation
def validate_file(file_name, header, rows, mappings=None, row_correction=None, new_file_name=None):

    if new_file_name:
            file_name = new_file_name

    team, month, year = extract_team_month_year(file_name)
    if not team or not month or not year:
        return {
        "status": "requires valid _team_month_year", 
        "error": "Filename must be in the format team_month_year.ext (e.g., sales_january_2024.csv)."
        }


    if not header: 
        return {"status": "error", "error": "Missing header row."}
    

    actual_header = header
    if mappings:
        actual_header = [mappings.get(col, col) for col in header]

    missing_columns = [col for col in REQUIRED_COLUMNS if col not in actual_header]    
    if missing_columns:
            return {
                "status": "requires_mappings", 
                "missing_columns": missing_columns,
                "actual_columns": actual_header
            }
    

    invalid_rows = []
    for index, row in enumerate(rows):
        if row_correction and str(index) in row_correction:
            corrections = row_correction[str(index)]
            for col, new_val in corrections.items():
                row[col] = new_val

        try:
            before = int(row["No of Records Before"])
            after = int(row["No of Records After"])
            expected_deleted = int(row["Expected Records Deleted"])
            actual_deleted = int(row["Actual Records Deleted"])

            if row_correction and str(index) in row_correction:
                corrections = row_correction[str(index)]
                for col, new_val in corrections.items():
                    row[col] = new_val

            int(row["No of Records Before"])
            int(row["No of Records After"])
            int(row["Expected Records Deleted"])
            int(row["Actual Records Deleted"])

        except ValueError:
            invalid_rows.append(row)
            # If it fails, capture the row data to send to React
            # If it fails, capture the row data inside a single dictionary for React
            invalid_rows.append({
                "rowIndex": index,
                "rowData": row,
                # For simplicity, we can ask them to check the whole row, or pinpoint columns later
                "column": "Check integer columns" 
            })

    if invalid_rows:
        # Send the invalid rows back to React so it can generate the text boxes
        return {
            "status": "requires_row_fixes",
            "invalid_rows": invalid_rows
        }
    
    return {
        "status": "success", 
        "message": "File is valid and has been moved to approved documents.",
        "file_name": file_name,
        "header": header,
        "rows": rows
    }    
    
    #add a cleaner method for missing columns(incase user used a different name for the column), invalid data types(incase user spelled out integer), or empty cells.

def extract_team_month_year(file_name):
    parts = file_name.split("_")
    if len(parts) >= 3:
        team = parts[0]
        month = parts[1]
        year = parts[2].split(".")[0]
    else:
        team = None
        month = None
        year = None

    return team, month, year



#process + migrate
def process_file(file_path): 
    # Process only the specific file uploaded
    path_obj = Path(file_path)
    if path_obj.suffix.lower() in [".csv", ".txt"]:
        df = pd.read_csv(path_obj, sep=None, engine="python")
    elif path_obj.suffix.lower() in [".xlsx", ".xls"]:
        df = pd.read_excel(path_obj)
    else:
        raise ValueError(f"Unsupported file format for file {path_obj.name}.")

    header = df.columns.tolist()
    rows = df.to_dict("records")
    return header, rows

def load_data():
    files = list(approved_docs.glob("*"))
    if not files:
        print("No approved files found. Please validate and clean your files first.")
        return pd.DataFrame() #return empty dataframe if no approved files
    return pd.concat([pd.read_csv(file) if file.suffix.lower() in [".csv", ".txt"] else pd.read_excel(file) for file in files], ignore_index=True)


#writer functions
def gen_mismatch_report(groupBy):
    mismatch_reports.mkdir(parents=True, exist_ok=True)
    
    df = load_data()

    if df.empty:
        print("No data available to generate mismatch report.")
        return

    df['delta'] = df['Expected Records Deleted'] - df['Actual Records Deleted']
    mismatches = df[df['delta']!=0]

    for group_value, group in mismatches.groupby(groupBy):
        output_file = mismatch_reports/ f"mismatch_report_{group_value}.csv"
        group.to_csv(output_file, index = False)
    
    