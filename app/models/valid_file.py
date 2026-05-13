from pydantic import BaseModel, Field
from typing import List

class file_model(BaseModel):
    team_name: str = Field(validation_alias='Table Name')
    records_before: int = Field(validation_alias='No of Records Before')
    records_after: int = Field(validation_alias='No of Records After')
    expected_records_deleted: int = Field(validation_alias='Expected Records Deleted')
    actual_records_deleted: int = Field(validation_alias='Actual Records Deleted')


# def delta_calculation(self):
#     return self.expected_records_deleted - self.actual_records_deleted

def df_to_pydantic(df) #-> List[file_model]:
    pydantic_rows = df.to_dict(orient='records')
    header = list(pydantic_rows[0].keys()) if pydantic_rows else []
    return header, pydantic_rows


def validate_pydantic_model(rows):
    invalid_fields = []
    for row in rows:
        try:
            _file_row = file_model.model_validate(row)
        except Exception as e:
            invalid_fields.append(row)
            continue
    return invalid_fields


def mappings_to_pydantic_header(mappings, rows):
    rows = [{mappings.get(k, k): v for k, v in row.items()} for row in rows]
    return rows


required_aliases = [
    field.validation_alias
    for field in file_model.model_fields.values()
    if isinstance(field.validation_alias, str)
]
 
    






