import pandas as pd
from datetime import datetime, time, timedelta
import datetime, os
from rescheduling_app.db_operations import BusinessLogic


DEFAULT_APPOINTMENT_UNITS = 1
DEFAULT_APPOINTMENT_DURATION = 10

def calculate_appointment_end_time(row):
    # Parse the start time in 12-hour format with AM/PM
    # start_time = pd.to_datetime(row['APPOINTMENT_TIME_FROM'], format='%I:%M %p')
    start_time = pd.to_datetime(row['APPOINTMENT_TIME_FROM'], format='%H:%M:%S')
    end_time = start_time + pd.Timedelta(minutes=row['Appointment_Units'] * row['APPOINTMENT_DURATION'])    
    return end_time.time()


def get_Provider_Availability_Summary_DF(df: pd.DataFrame) -> pd.DataFrame:
    try:
        # Parse time columns into proper datetime format
        for col in [
            'PROVIDER_TIME_FROM', 'PROVIDER_TIME_TO', 'PROVIDER_BREAK_TIME_FROM', 'PROVIDER_BREAK_TIME_TO',
        ]:
            try:
                df[col] = pd.to_datetime(df[col], format='%H:%M:%S').dt.time
            except Exception as e:
                raise ValueError(f"Error parsing column '{col}' to time format: {e}")

        print(f"\n{df['APPOINTMENT_TIME_FROM'].unique()}\n")

        # Add space between time and AM/PM if missing
        try:
            df['APPOINTMENT_TIME_FROM'] = df['APPOINTMENT_TIME_FROM'].str.replace(
                r'(\d{1,2}:\d{2})(AM|PM)', r'\1 \2', regex=True
            )
            df['APPOINTMENT_TIME_FROM'] = df['APPOINTMENT_TIME_FROM'].str.strip()
        except Exception as e:
            raise ValueError(f"Error processing 'APPOINTMENT_TIME_FROM': {e}")

        # Regex pattern to match 'A M' or 'P M' and replace with 'AM' or 'PM'
        df['APPOINTMENT_TIME_FROM'] = df['APPOINTMENT_TIME_FROM'].str.replace(r'(\d{1,2}:\d{2})\s*A\s*M', r'\1 AM', regex=True)
        df['APPOINTMENT_TIME_FROM'] = df['APPOINTMENT_TIME_FROM'].str.replace(r'(\d{1,2}:\d{2})\s*P\s*M', r'\1 PM', regex=True)
        
        print(f"\n{df['APPOINTMENT_TIME_FROM'].unique()}\n")

        # Convert the time string to a datetime object
        try:                
            df['APPOINTMENT_TIME_FROM'] = pd.to_datetime(df['APPOINTMENT_TIME_FROM'], format='%I:%M %p').dt.time
        except Exception as e:
            raise ValueError(f"Error converting 'APPOINTMENT_TIME_FROM' to time: {e}")

        # Handle missing values
        try:
            df['Appointment_Units'] = df['Appointment_Units'].fillna(DEFAULT_APPOINTMENT_UNITS)
            df['APPOINTMENT_DURATION'] = df['APPOINTMENT_DURATION'].fillna(DEFAULT_APPOINTMENT_DURATION)
        except Exception as e:
            raise ValueError(f"Error filling missing values in 'Appointment_Units' or 'APPOINTMENT_DURATION': {e}")

        # Parse appointment date
        try:
            df['Appointment_Date'] = pd.to_datetime(df['Appointment_Date'], format='%Y-%m-%d')
        except Exception as e:
            raise ValueError(f"Error parsing 'Appointment_Date' to datetime: {e}")

        # Calculate appointment end time
        try:
            df['APPOINTMENT_TIME_TO'] = df.apply(calculate_appointment_end_time, axis=1)
        except Exception as e:
            raise ValueError(f"Error calculating 'APPOINTMENT_TIME_TO': {e}")

        # Group by WEEK_DAY and Appointment_Date
        summary = []
        try:            
            # for (weekday, appointment_date), group in df.groupby(['WEEK_DAY', 'Appointment_Date']):
            for appointment_date, group in df.groupby(['Appointment_Date']):  
                appointment_date = pd.to_datetime(group['Appointment_Date'].iloc[0])  # Ensure it's a single datetime value
                weekday = appointment_date.strftime('%A').upper()  # Get correct weekday name

                try:
                    provider_start = pd.to_datetime(group['PROVIDER_TIME_FROM'].iloc[0], format='%H:%M:%S')
                    provider_end = pd.to_datetime(group['PROVIDER_TIME_TO'].iloc[0], format='%H:%M:%S')
                    break_start = pd.to_datetime(group['PROVIDER_BREAK_TIME_FROM'].iloc[0], format='%H:%M:%S')
                    break_end = pd.to_datetime(group['PROVIDER_BREAK_TIME_TO'].iloc[0], format='%H:%M:%S')

                    # Create unavailable slots
                    unavailable_slots = group[['APPOINTMENT_TIME_FROM', 'APPOINTMENT_TIME_TO']].drop_duplicates().sort_values(
                        by='APPOINTMENT_TIME_FROM'
                    )

                    # print(f"\n{unavailable_slots}\n")

                except Exception as e:
                    raise ValueError(f"Error processing group data for weekday '{weekday}' and date '{appointment_date}': {e}")

                # Consolidate unavailable slots
                consolidated_unavailable = []
                try:
                    for _, row in unavailable_slots.iterrows():
                        start = pd.to_datetime(row['APPOINTMENT_TIME_FROM'], format='%H:%M:%S')
                        end = pd.to_datetime(row['APPOINTMENT_TIME_TO'], format='%H:%M:%S')
                        if not consolidated_unavailable or start > consolidated_unavailable[-1]['END']:
                            consolidated_unavailable.append({'START': start, 'END': end})
                        else:
                            consolidated_unavailable[-1]['END'] = max(consolidated_unavailable[-1]['END'], end)

                    # Add break time
                    consolidated_unavailable.append({'START': break_start, 'END': break_end})
                    consolidated_unavailable = sorted(consolidated_unavailable, key=lambda x: x['START'])
                except Exception as e:
                    raise ValueError(f"Error consolidating unavailable slots: {e}")

                # Calculate available slots
                available_slots = []
                try:
                    previous_end = provider_start
                    for slot in consolidated_unavailable:
                        current_start = slot['START']
                        if current_start > previous_end:
                            available_slots.append({'START': previous_end.time(), 'END': current_start.time()})
                        previous_end = slot['END']

                    if previous_end < provider_end:
                        available_slots.append({'START': previous_end.time(), 'END': provider_end.time()})
                except Exception as e:
                    raise ValueError(f"Error calculating available slots: {e}")

                # Add data to summary
                summary.append({
                    'WEEK_DAY': weekday,
                    'Appointment_Date': appointment_date.date(),
                    'WORK_START': provider_start.time(),
                    'WORK_END': provider_end.time(),
                    'BREAK_START': break_start.time(),
                    'BREAK_END': break_end.time(),
                    'UNAVAILABLE_SLOTS': [
                        {'START': row['START'].time(), 'END': row['END'].time()} for row in consolidated_unavailable
                    ],
                    'AVAILABLE_SLOTS': available_slots,
                })
        except Exception as e:
            raise ValueError(f"Error grouping and summarizing data: {e}")

        # Convert summary into DataFrame
        try:
            summary_df = pd.DataFrame(summary)
        except Exception as e:
            raise ValueError(f"Error converting summary to DataFrame: {e}")

        # summary_df.to_csv("summary_df.csv", index=False)
        return summary_df

    except Exception as e:
        raise ValueError(f"Error in 'get_Provider_Availability_Summary_DF': {e}")


# Function to Parse Time Slots
def parse_time_slots(slot_string):
    if isinstance(slot_string, str):
        try:
            return eval(slot_string, {"time": time, "datetime": datetime})
        except Exception as e:
            print(f"Error parsing: {slot_string} -> {e}")
            return []
    return []


# Generate Patient Prompt with summarized data
def generate_patient_prompt(df):
    prompt = "Patient's Historical Preferences:\n"
    grouped = df.groupby(['WEEKDAY', 'Time_From', 'Appointment_Status_Description']).size()
    for (weekday, time_from, status), count in grouped.items():
        prompt += f"{weekday} at {time_from} ({count} times, Status: {status})\n"

    return prompt

# Generate Provider Prompt with summarized data
def generate_provider_prompt(df):
    prompt = "Provider's Availability:\n"
    for _, row in df.iterrows():
        available_slots = row['AVAILABLE_SLOTS']
        available_text = ", ".join(
            f"{slot['START'].strftime('%I:%M %p')} to {slot['END'].strftime('%I:%M %p')}"
            for slot in available_slots
        )
        prompt += (
            f"On {row['WEEK_DAY']}, {row['Appointment_Date']}, "
            f"the provider is available at: {available_text}\n"
        )

    return prompt

# Generate Final Prompt
def generate_final_prompt(patient_prompt, provider_prompt):
    final_prompt = (
        f"{patient_prompt}\n\n{provider_prompt}\n"        
    )
    return final_prompt


# Entry point for creating final summarized data for prompt
def getSummarizedDataForPrompt(providerDF: pd.DataFrame, patientHistoryDF: pd.DataFrame = None) -> str:
    
    provider_summary_df = get_Provider_Availability_Summary_DF(providerDF)
    provider_prompt = generate_provider_prompt(provider_summary_df)
    
    # print(providerDF['PROVIDER_CODE'].iloc[0])

    status, schedule = BusinessLogic.getProviderWeeklySchedule(providerDF['PROVIDER_CODE'].iloc[0])
    # print("Schedule:\n", schedule)
    status, default_time = BusinessLogic.getProviderDefaultTime(providerDF['PROVIDER_CODE'].iloc[0])
    
    default_time_list = get_formatted_time_ranges(default_time)
    print(f"Default time of provider: {default_time_list}")
    
    provider_prompt_new = fill_missing_dates(provider_prompt, schedule, default_times=default_time_list if status else None)
    if patientHistoryDF is None:
        return provider_prompt_new
    
    patient_prompt = generate_patient_prompt(patientHistoryDF)
    final_prompt = generate_final_prompt(patient_prompt, provider_prompt_new)
    
    return final_prompt



# =========================================
from datetime import datetime, timedelta
import pandas as pd

def parse_date(date_str):
    return datetime.strptime(date_str, '%Y-%m-%d')

def format_date(dt):
    return dt.strftime('%Y-%m-%d')

def fill_missing_dates(data, weekly_schedule, default_times=None):
    if default_times is None:
        default_times = ['09:00 AM to 12:15 PM', '01:00 PM to 05:00 PM']
    
    lines = data.strip().split('\n')
    # print("Input Lines:", lines)
    if lines and lines[0].strip() == "Provider's Availability:":
        lines = lines[1:]
        # print("Lines after header removal:", lines)
    
    availability = []
    for line in lines:
        if not line.strip():
            print(f"Skipping empty line: {line}")
            continue
        try:
            parts = line.split(', the provider is available at: ')
            if len(parts) != 2:
                print(f"Invalid split for line: {line}")
                continue
            date_part = parts[0].split(', ')
            if len(date_part) < 2:
                print(f"Invalid date part for line: {line}")
                continue
            date_str = date_part[1]
            date = parse_date(date_str)
            times = parts[1].split(', ')
            availability.append((date, times))
            # print(f"Parsed: date={date_str}, times={times}")
        except (IndexError, ValueError) as e:
            print(f"Error parsing line: {line}, Error: {e}")
            continue
    
    if not availability:
        print("No valid availability data parsed.")
        return "Provider's Availability:\nNo valid availability data provided."
    
    # print("Availability:", [(d.strftime('%Y-%m-%d'), t) for d, t in availability])
    
    availability.sort(key=lambda x: x[0])
    
    existing_dates = {date.date() for date, _ in availability}
    # print("Existing Dates:", existing_dates)
    
    start_date = availability[0][0]
    end_date = availability[-1][0]
    # print(f"Date Range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
    
    current_date = start_date
    result = []
    
    weekly_schedule = weekly_schedule.copy()
    weekly_schedule['Weekday'] = weekly_schedule['Weekday'].astype(int)
    weekly_schedule['Status'] = weekly_schedule['Status'].map({True: 1, False: 0, 1: 1, 0: 0}).astype(int)
    
    # print("Weekly Schedule:\n", weekly_schedule)
    schedule_dict = dict(zip(weekly_schedule['Weekday'], weekly_schedule['Status']))
    # print("Schedule Dict:", schedule_dict)
    
    while current_date <= end_date:
        current_date_only = current_date.date()
        weekday_num = current_date.isoweekday()
        status = schedule_dict.get(weekday_num, 0)
        # print(f"Processing: {current_date_only}, Weekday: {weekday_num}, Status: {status}")
        found = False
        for date, times in availability:
            if date.date() == current_date_only:
                # print(f"Found existing: {current_date_only}, Times: {times}")
                result.append(f"On {current_date.strftime('%A').upper()}, {format_date(current_date)}, the provider is available at: {', '.join(times)}")
                found = True
                break
        if not found and (current_date_only in existing_dates or status == 1):
            # print(f"Adding missing: {current_date_only}")
            result.append(f"On {current_date.strftime('%A').upper()}, {format_date(current_date)}, the provider is available at: {', '.join(default_times)}")
        current_date += timedelta(days=1)
    
    return "Provider's Availability:\n" + '\n'.join(result)


def get_formatted_time_ranges(df):
    if isinstance(df, str):        
        return None

    def to_ampm(time_str):
        return datetime.strptime(time_str, "%H:%M:%S").strftime("%I:%M %p")

    formatted_ranges = []

    for _, row in df.iterrows():
        time_from = row['Time_From_New']
        time_to = row['Time_To_New']
        break_from = row['Break_Time_From_New']
        break_to = row['Break_Time_To_New']

        formatted_ranges.append(f"{to_ampm(time_from)} to {to_ampm(break_from)}")
        formatted_ranges.append(f"{to_ampm(break_to)} to {to_ampm(time_to)}")

    return formatted_ranges


# data = """Provider's Availability:
# On MONDAY, 2025-04-28, the provider is available at: 08:00 AM to 04:30 PM, 05:00 PM to 08:00 PM
# On THURSDAY, 2025-05-01, the provider is available at: 08:00 AM to 11:30 AM, 12:00 PM to 08:00 PM
# On MONDAY, 2025-05-05, the provider is available at: 08:30 AM to 09:00 AM, 12:30 PM to 03:15 PM, 03:35 PM to 08:00 PM
# On THURSDAY, 2025-05-08, the provider is available at: 08:00 AM to 10:00 AM, 10:30 AM to 03:00 PM, 03:30 PM to 08:00 PM
# On MONDAY, 2025-05-12, the provider is available at: 08:15 AM to 09:00 AM, 09:10 AM to 08:00 PM
# On TUESDAY, 2025-05-13, the provider is available at: 08:00 AM to 09:00 AM, 09:30 AM to 08:00 PM
# On FRIDAY, 2025-05-16, the provider is available at: 09:00 AM to 09:30 AM, 10:00 AM to 01:30 PM, 02:30 PM to 08:00 PM
# """

# weekly_schedule = pd.DataFrame({
#     'Weekday': [7, 6, 5, 4, 3, 2, 1],
#     'Status': [True, True, True, True, True, True, True]
# })

# result = fill_missing_dates(data, weekly_schedule)
# print("\nFinal Output:")
# print(result)