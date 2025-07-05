import json, re
from rescheduling_app.db_operations import BusinessLogic
from rescheduling_app.utils.logging_utils import log, log_request
import traceback

def extract_json_from_response(raw_response):
    """Extract and parse JSON from the raw response string."""
    # Extract text content using regex
    pattern = r"```json\\n(.*?)\\n```"
    match = re.search(pattern, raw_response, re.DOTALL)
    
    if match:
        json_string = match.group(1)  # Extract JSON string part
        json_string = json_string.replace('\\n', '').replace('\\"', '"')  # Clean up escape characters
        try:
            parsed_json = json.loads(json_string)  # Convert to proper JSON object
            print("Parsed JSON:", parsed_json)  # For debugging
            return parsed_json
        except json.JSONDecodeError as e:
            traceback.print_exc()
            log('error', 'unknown_uid', str(e))  # Assuming log function exists
            print("Error decoding JSON:", e)
            return None
    else:
        log('info', 'unknown_uid', "Invalid JSON found in response")  # Assuming log function exists
        print("Invalid JSON found in response")
        return None

def get_all_previous_slots(current_uid, patient_account):
    """Retrieve all previous recommended slots from Rescheduling_Logs and Future_Rescheduling_Logs."""
    all_slots = []
    while current_uid:
        # Check Future_Rescheduling_Logs first
        status, result = BusinessLogic.getFutureReschedulingLog(current_uid, patient_account)
        if status:
            # Extract slots from future_rescheduling_response
            raw_response = result['future_rescheduling_response']
            parsed_json = extract_json_from_response(raw_response)
            if parsed_json:
                slots = parsed_json.get("Recommended_Slots", [])
                all_slots.append(slots if slots else [])
            # Move to the previous interaction
            current_uid = result['previous_uid']
        else:
            # Check Rescheduling_Logs if not found in Future_Rescheduling_Logs
            status, result = BusinessLogic.getLastSessionHistory(None, current_uid, patient_account)
            if status:
                # Extract slots from response (assuming it's a DataFrame with one row)
                raw_response = result['response'].iloc[0]
                parsed_json = extract_json_from_response(raw_response)
                if parsed_json:
                    slots = parsed_json.get("Recommended_Slots", [])
                    all_slots.append(slots if slots else [])
                # Initial record has no previous_uid, so stop
                current_uid = None
            else:
                log('error', current_uid, f"UID {current_uid} not found in either table")
                print(f"UID {current_uid} not found in either table")
                break
    return all_slots

# Example usage (for testing purposes)
# Assume BusinessLogic methods are defined elsewhere
# current_uid = "some_uid"
# patient_account = "some_account"
# slots = get_all_previous_slots(current_uid, patient_account)
# print("All previous slots:", slots)

# if __name__ == "__main__":
#     result = get_all_previous_slots("f018b823", "101116353910067")
#     print(result)