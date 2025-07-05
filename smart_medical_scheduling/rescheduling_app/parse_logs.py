import re
import pandas as pd
from rescheduling_app.utils.json_utils import add_json_markdown





def parse_logs_to_dataframe(log_file_path, output_csv_path=None):
    # Regex pattern for extracting log structure
    # log_pattern = r'INFO \| ([\d\-:, ]+) \| \[(.*?)\] \| (.*)'
    log_pattern = r'INFO \| (\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}) \| \[([a-fA-F0-9]+)\] \| (.+)'

    # Initialize a list to store parsed data
    parsed_data = []

    # Open and parse the log file
    with open(log_file_path, "r") as file:
        lines = file.readlines()  # Read all lines in the log file

    i = 0
    while i < len(lines):
        line = lines[i]
        match = re.match(log_pattern, line)
        if match:
            # Extract main parts of the log
            timestamp = match.group(1)  # Datetime
            uid = match.group(2)  # Unique ID
            message = match.group(3)  # Log message

            # Initialize extracted values
            patient_id = None
            practice_code = None
            provider_code = None
            patient_status = None
            response = None
            chief_complaint = None
            visit_type = None
            recommended_specialists = None

            # Check for specific fields in the log message
            if "Patient ID" in message:
                patient_id = re.search(r"Patient ID: (\d+)", message).group(1)
            if "Practice Code" in message:
                practice_code = re.search(r"Practice Code: (\d+)", message).group(1)
            if "Provider Code" in message:
                provider_code = re.search(r"Provider Code: (\d+)", message).group(1)
            if "Patient status" in message:
                patient_status = re.search(r"Patient status: (\w+)", message).group(1)
            if "Chief Complaint" in message:
                chief_complaint = re.search(r"Chief Complaint: (.+)", message).group(1)
            if "Visit Type" in message:
                visit_type = re.search(r"Visit Type: (.+)", message).group(1)
            if "All Recommended Specialists" in message:
                recommended_specialists = re.search(r"All Recommended Specialists: (.+)", message).group(1)
            if "Response:" in message:
                # Start capturing the JSON block
                response_lines = []
                i += 1  # Move to the next line
                while i < len(lines) and not lines[i].strip().startswith("INFO"):
                    response_lines.append(lines[i].strip())
                    if lines[i].strip().endswith("}"):  # Stop if JSON closes
                        break
                    i += 1
                response = "\n".join(response_lines)  # Combine JSON lines into a single string
            else:
                i += 1

            # Append to the parsed data list
            parsed_data.append({
                "timestamp": timestamp,
                "uid": uid,
                "patient_id": patient_id,
                "practice_code": practice_code,
                "provider_code": provider_code,
                "patient_status": patient_status,
                "chief_complaint": chief_complaint,
                "visit_type": visit_type,
                "recommended_specialists": recommended_specialists,
                "response": response,
            })
        else:
            i += 1

    # Convert parsed data to a DataFrame
    df = pd.DataFrame(parsed_data)

    # Convert timestamp to date only    
    df["creation_date"] = pd.to_datetime(df["timestamp"], format="%Y-%m-%d %H:%M:%S,%f").dt.date        
 

    # Group by 'uid' and aggregate to get one row per uid
    df_grouped = df.groupby("uid").agg({
        "creation_date": "first",  # Take the first date (should be the same for all rows of a uid)
        "patient_id": "first",  # Take the first non-NaN value
        "practice_code": "first",
        "provider_code": "first",
        "patient_status": "first",
        "chief_complaint": "first",
        "visit_type": "first",
        "recommended_specialists": "first",
        "response": "first",
    }).reset_index()
    
    if output_csv_path:
        df_grouped.to_csv(output_csv_path, index=False)

    return df_grouped


def parse_logs_for_user_response(log_file_path, output_csv_path=None):
    # log_pattern = r'INFO \| ([\d\-:, ]+) \| \[(.*?)\] \| (.*)'
    log_pattern = r'INFO \| (\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}) \| \[([a-fA-F0-9]+)\] \| (.+)'
    parsed_data = []
    
    with open(log_file_path, "r") as file:
        lines = file.readlines()

    i = 0
    while i < len(lines):
        line = lines[i].strip()
        match = re.match(log_pattern, line)
        if match:
            timestamp = match.group(1)
            uid = match.group(2)
            message = match.group(3)

            log_entry = {
                "timestamp": timestamp,
                "uid": uid,
                "previous_uid": None,
                "patient_account": None,
                "location_code": None,
                "user_followup_msg": None,
                "initial_recommended_slots": None,
                "message_category_Response": None,
                "appointment_response": None,
                "future_rescheduling_response": None,
            }

            if "previous_uid" in message:
                result = re.search(r"previous_uid: (\w+)", message)
                log_entry["previous_uid"] = result.group(1) if result else None

            if "patient_account" in message:
                result = re.search(r"patient_account: (\d+)", message)
                log_entry["patient_account"] = result.group(1) if result else None

            if "location_code" in message:
                result = re.search(r"location_code: (\d+)", message)
                log_entry["location_code"] = result.group(1) if result else None

            if "user_followup_msg" in message:
                result = re.search(r"user_followup_msg: (.+)", message)
                log_entry["user_followup_msg"] = result.group(1) if result else None

            if "initial_recommended_slots" in message:
                result = re.search(r"initial_recommended_slots: (.+)", message)
                log_entry["initial_recommended_slots"] = result.group(1) if result else None

            if "message_category_Response" in message:
                result = re.search(r"message_category_Response: (.+)", message)
                log_entry["message_category_Response"] = result.group(1) if result else None
            
            # Extract JSON content for appointment_response
            if "appointment_response:" in message:
                response_lines = []
                while i + 1 < len(lines) and not lines[i + 1].startswith("INFO"):
                    i += 1
                    response_lines.append(lines[i].strip())

                log_entry["appointment_response"] = "\n".join(response_lines)

            # Extract JSON content for Future_Rescheduling_Request_Response
            if "Future_Rescheduling_Request_Response:" in message:
                log_entry["future_rescheduling_response"] = re.search(r"Future_Rescheduling_Request_Response: (.+)", message).group(1)

            parsed_data.append(log_entry)

        i += 1  # Move to next line
    
    df = pd.DataFrame(parsed_data)

    # Convert timestamp column to datetime format
    df["creation_date"] = pd.to_datetime(df["timestamp"], errors="coerce").dt.date    

    # Group by 'uid' and aggregate
    df_grouped = df.groupby("uid").agg({
        "creation_date": "first",
        "previous_uid": "first",
        "patient_account": "first",
        "location_code": "first",
        "user_followup_msg": "first",
        "initial_recommended_slots": "first",
        "message_category_Response": "first",
        "appointment_response": "first",
        "future_rescheduling_response": "first",
    }).reset_index()
    
    df_grouped = add_json_markdown(df_grouped)

    if output_csv_path:
        df_grouped.to_csv(output_csv_path, index=False)

    return df_grouped



def make_dataframe(uid, CURRENT_DATE, patient_ID, practice_code=None,
                   provider_Code=None, patient_status=None,
                   response=None, chief_Complaint=None,
                   visit_Type=None, recommended_specialists=None):
    data = {
        "creation_date": [CURRENT_DATE],
        "uid": [uid],
        "patient_id": [patient_ID],
        "practice_code": [practice_code],
        "provider_code": [provider_Code],
        "patient_status": [patient_status],
        "chief_complaint": [chief_Complaint],
        "visit_type": [visit_Type],
        "recommended_specialists": [recommended_specialists],
        "response": [response],
    }

    df = pd.DataFrame(data)
    return df

def make_dataframe_user_response(uid, previous_uid, CURRENT_DATE, patient_account,
                                  location_code, user_message, initial_recommended_slots,
                                  ai_response, final_response, appointment_response=None):
    data = {
        "uid": [uid],
        "creation_date": [CURRENT_DATE],
        "previous_uid": [previous_uid],
        "patient_account": [patient_account],
        "location_code": [location_code],
        "user_followup_msg": [user_message],
        "initial_recommended_slots": [initial_recommended_slots],
        "message_category_Response": [ai_response],
        "appointment_response": [appointment_response],
        "future_rescheduling_response": [final_response]
    }

    df = pd.DataFrame(data)
    return df