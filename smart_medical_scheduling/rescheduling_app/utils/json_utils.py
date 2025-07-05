import pandas as pd
import numpy as np
import json

def add_json_markdown(df: pd.DataFrame) -> pd.DataFrame:
    """
    For the specified columns in df, if the cell value is not empty or null,
    ensure it starts with "```json" and ends with "```". Otherwise, leave it unchanged.
    """
    cols = [
        "initial_recommended_slots", 
        "message_category_Response", 
        "appointment_response", 
        "future_rescheduling_response"
    ]
    
    for col in cols:
        if col in df.columns:
            df[col] = df[col].apply(
                lambda x: x if pd.isnull(x) or not str(x).strip() 
                else (x if (str(x).startswith("```json") and str(x).endswith("```")) 
                      else f"```json{x}```")
            )
    return df

def escape_sql_string(val):
    """
    Escapes single quotes in the value by doubling them.
    If val is None or empty, returns "NULL" (without quotes).
    """
    if val is None or (isinstance(val, str) and not val.strip()) or val == "None":
        return "NULL"
    return val.replace("'", "''")


