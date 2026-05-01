from fastapi import FastAPI, UploadFile, File, Form #for handling file uploads and form data
from fastapi.middleware.cors import CORSMiddleware #cross origin resource sharing
import json
import shutil
from pathlib import Path
import pandas as pd
from app.core.dataManager import validate_file, input_docs, approved_docs, output_docs, process_file

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"], #allow all HTTP methods (GET, POST, etc.)
    allow_headers=["*"],

)

@app.get("/")
async def root():
    return {"message": "Welcome to the File Validation API!"}

@app.post("/validate")
async def validate_endpoint(
    file: UploadFile = File(...), 
    mappings: str = Form(None), 
    row_correction: str = Form(None),
    new_file_name: str = Form(None)
):
    parsed_mappings = json.loads(mappings) if mappings else None
    parsed_corrections = json.loads(row_correction) if row_correction else None

    new_name = new_file_name if new_file_name else file.filename
    input_docs.mkdir(parents=True, exist_ok=True)
    file_path = input_docs / new_name
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        header, rows = process_file(file_path)
    except Exception as e:
        return {"status": "error", "error": f"Failed to read file: {str(e)}"}

    result_dict = validate_file(new_name, header, rows, parsed_mappings, parsed_corrections, new_file_name)

    if result_dict.get("status") == "success":
        approved_docs.mkdir(parents=True, exist_ok=True)
        final_file_name = result_dict.get("file_name", new_name)
        
        cleaned_df = pd.DataFrame(result_dict["rows"], columns=result_dict["header"])
        cleaned_df.to_csv(approved_docs / final_file_name, index=False)
        file_path.unlink(missing_ok=True) # Delete the original dirty file from input_docs

    return result_dict
