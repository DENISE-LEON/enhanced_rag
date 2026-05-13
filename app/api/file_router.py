from fastapi import FastAPI, UploadFile, File, Form, HTTPException  # for handling file uploads and form data
from fastapi.middleware.cors import CORSMiddleware  # cross origin resource sharing
import json
import shutil
from pathlib import Path
import pandas as pd
from app.core.data_manager import validate_file, input_docs, approved_docs, output_docs, process_file
# import valid_file class
from app.models.valid_file import file_model, df_to_pydantic


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],  # allow all HTTP methods (GET, POST, etc.)
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {"message": "Welcome to the File Validation API!"}  # what is returned to the user


@app.post("/validate")
async def validate_endpoint(
    input_file: UploadFile = File(...),
    mappings: str = Form(None),
    row_correction: str = Form(None),
    new_file_name: str = Form(None)
):
    # Parse optional JSON form fields and fail as a client error, not an internal server error.
    try:
        parsed_mappings = json.loads(mappings) if mappings else None
        parsed_corrections = json.loads(row_correction) if row_correction else None
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON in form fields: {str(e)}")

    file_name = new_file_name if new_file_name else input_file.filename

    input_docs.mkdir(parents=True, exist_ok=True)
    old_file_path = input_docs / input_file.filename
    file_path = input_docs / file_name
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(input_file.file, buffer)

    try:
        df = process_file(file_path)  # read file and convert to pydantic model
    except Exception as e:
        return {"status": "error", "error": f"Failed to read file: {str(e)}"}

    try:
        result_dict = validate_file(file_name, df, parsed_mappings, parsed_corrections, new_file_name)
    except (AttributeError, TypeError, KeyError) as e:
        raise HTTPException(status_code=400, detail=f"Invalid mappings or row_correction structure: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected validation failure: {str(e)}")

    if result_dict.get("status") == "success":
        approved_docs.mkdir(parents=True, exist_ok=True)
        final_file_name = result_dict.get("file_name", file_name)
        try:
            cleaned_df = pd.DataFrame(result_dict["rows"], columns=result_dict["header"])
            cleaned_df.to_csv(approved_docs / final_file_name, index=False)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed while writing approved file: {str(e)}")

        if final_file_name != new_file_name or final_file_name != input_file.filename:
            try:
                file_path.unlink(missing_ok=True)
                old_file_path.unlink(missing_ok=True)
            except PermissionError as e:
                raise HTTPException(status_code=500, detail=f"Failed to delete input file because it is in use: {str(e)}")
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Failed to delete input file: {str(e)}")

    return result_dict