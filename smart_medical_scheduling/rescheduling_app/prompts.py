import pandas as pd
from datetime import datetime

class Prompts:
    
    def prompt(self, summarized_data, history=False):
        current_date = datetime.now().strftime("%m/%d/%Y")  # USA format
        current_day = datetime.now().strftime("%A")

        try:            
            if history:
                prompt  = f"""
                You are an intelligent medical appointment scheduling assistant. You are given with the patient appointment history data and provider's availability schedule. Your primary task is to first analyze patterns in patient's past appointment data, such as whether patient prefers appointment at first half of the day or second half of the day, patient's preferred day of the week and time range of appointments. You then need to cross-check these preferences with the provider's availability schedule to determine the most suitable and recent appointment slots. If multiple patterns exist in the patient's historical data, identify the two most frequently occurring ones and prioritize time slots that are both recent and frequent while ensuring that all suggested slots align with the provider's availability schedule. Do not recommend any backdated appointments and should always suggest the three earliest available time slots of three days beyond {current_date} based on your analysis. The recommendations should be returned in JSON format with the following structure:

                Required Key:
                1. 'Recommended_Slots' must be a dictionary where:
                    - Keys are dates in "Month Day" format (e.g., "Feb 22").
                    - Values are non-empty lists of time slot strings.                                                

                Required JSON Output:
                {{
                "Recommended_Slots": {{
                    "Feb 22": ["10:00 AM", "11:00 AM", "03:00 PM"], 
                    "Mar 23": ["09:00 AM", "12:00 PM"],
                    "Mar 26": ["09:30 AM", "11:30 PM"] 
                }}
                }}

                Instructions:
                - Keep in mind that today's date is {current_date}, and the day is {current_day}.
                - Recommend appointment slots based on both:
                    1. The provider's available slots.
                    2. The patient's past appointment **time range** and **day** to ensure its alignment with patient's historical preferences.
                - **Do not recommend any time slot from your own. Always select time slots from the provided summarized data of provider's available schedule**.
                - Do not recommend any time slots on weekend (Saturday or Sunday) until its exists in **patient preferences** and **provider availability schedule**.
                - If the patient has historic preference on Saturday, then in this case you must need to check availability in provider schedule. If provider available on recent Saturday and has available slots, then choose best matched time slots, otherwise choose best matched options from weekdays.
                - Recommend slots from recent closer month and dates that aligns with patient past appointment history (days, time from first half or day or second half of a day) and provider availability, do not recommend slots dates with variations.
                - Prioritize the most recent three available slots of three days that align with the patient's past appointments **time range** and preferred days, as it increases the likelihood of appointment completion.
                - If no matching slots are found, check onward days until a suitable match is found.
                - If a provider's available slots on a given working day do not match the patient's preferences, suggest slots from the next available working days, even if no appointments are currently booked on those days.
                - Do not recommend date with empty time slots, if no available slots exist, then consider next working days until you find a best time, but do not give empty slots like "May 7": []. Do not suggest these kind of empty slots.
                - When recommending an appointment based on the preferred and best-matched date and time, make sure that **do not choose any end time slot from provider schedule** or give slot of atleast 15 minute before the provider end time, as provider is available until that time. For example, in the following schedule, the end time slot are 02:00 PM and 02:25 PM: (On MONDAY, YYYY-MM-DD, the provider is available at: 01:50 PM to 02:00 PM, 02:15 PM to 02:25 PM)
                - If the patient's preferred day is not available in the provider's schedule, recommend the next most suitable working day slot that falls within patient's preferred time range and is available soonest.
                - Only recommend slots for future dates beyond {current_date}, select the three nearest available and best matched options.
                - Avoid suggesting night time slots or very early morning slots (e.g., 3 AM, 4 AM) or times outside official USA working hours.
                - Return only the required data format without any additional details.

                Input:
                {summarized_data}
                                
                Output:
                """
                return prompt
            
            else:                
                prompt  = f"""
                You are an intelligent medical appointment scheduling assistant. You are given with the summarized data of provider availability. First analyze provider availability data and then recommend at least two recent available appointment time slots of three days for a patient (if available). Do not recommend any backdated appointments and should always suggest at least two available time slots (half from first half of the day and half from second half of the day) of three days beyond {current_date} based on your analysis. The recommendations should be returned in JSON format with the following structure:

                Required Keys:                
                1. 'Recommended_Slots' must be a dictionary where:
                    - Keys are dates in "Month Day" format (e.g., "Feb 22").
                    - Values are non-empty lists of time slot strings.                

                Required JSON Output:
                {{
                "Recommended_Slots": {{
                    "Feb 22": ["10:00 AM", "11:30 AM", "02:30 PM", "03:00 PM"],
                    "Mar 23": ["09:00 AM", "01:00 PM"],
                    "Mar 26": ["09:30 AM", "03:30 PM"]
                }}                
                }}

                Instructions:
                - Keep in mind that today date is {current_date} and day is {current_day}.
                - Consider the provider's availability to recommend at least two most suitable and recent days time slots. Time slot should be recommended from the first half of the day and second half of the day.
                - Always recommend at least two available time slots of three days beyond {current_date} based on your analysis.            
                - Always recommend slots from the provided data of provider availability. If no earlier available slots exist, then consider next working days from provided available slots.
                - If there is no earlier available slots of provider on a specific working day, recommend slots from the nearby working day(s) based on provided slots data.
                - You can consider the consecutive working days if no suitable option is found. Do not recommend any slots from weekend (Saturday or Sunday).
                - Do not recommend date with empty time slots, if no available slots exist, then consider next working days until you find a best time, but do not give empty slots like "May 7": []. Do not suggest these kind of empty slots.
                - When selecting an appointment slots time on the preferred day, choose from starting time or anywhere in between time of provider's availability of that specific day, or at least 15 minutes before the provider's end time.                                                
                - Ensure that recommended slots are only from the very nearest possible future dates greater than {current_date}.
                - Avoid suggesting night time slots or very early morning slots (e.g., 3 AM, 4 AM) or times outside official USA working hours.
                - Return only the required data format without any additional details. 

                Input:
                {summarized_data}
                
                Output:        
                """
                return prompt
            
                 
        except Exception as e:
            print("Exception in prompt:", e)            

    # def getRecommendationPrompt(self, specialist_data:pd.DataFrame, cheif_complaint:str):
    #     try:
    #         prompt = f"""You are an intelligent assistant trained to recommend suitable healthcare providers based on a patient’s chief complaint. Below is a table of specialities and their associated provider codes. Your task is to analyze the provided data and identify the most relevant specialities for the given chief complaint. Then, return a list of the corresponding provider codes for the recommended specialities.

    #         Important instructions:
    #             - Analyze the chief complaint and map it to the most relevant speciality in the table.
    #             - Return a structured output in dictionary form where:
    #                 - Speciality: Name of the recommended speciality.
    #                 - Provider_Codes: List of associated provider codes.
    #             - If no suitable match is found, refer to Internal Medicine if it exists in the table, as they can provide initial evaluation, management and referrals.
    #             - If Internal Medicine is also unavailable or the table is empty, return an output like this:
    #                 {{
    #                     "Speciality": "",
    #                     "Provider_Codes": []
    #                 }}
    #             - Do not provide any additional details like explanations, only return the required JSON output.
                
    #         Example Input 1:
    #             - Chief Complaint: "Chest pain and irregular heartbeat."
    #             - Specialities and Provider Codes Data:
    #                 | Speciality                  | Provider Codes           |
    #                 |-----------------------------|--------------------------|
    #                 | Family Medicine             | 92810653                 |
    #                 | Family Nurse Practitioner   | 55212287                 |
    #                 | Internal Medicine           | 100, 55211862, 56511293  |
    #                 | Cardiology                  | 400, 500, 600            |
    #                 | Pulmonology                 | 700, 800, 900            |
                
    #         Example Output 1:
    #             {{
    #                 "Speciality": "Cardiology",
    #                 "Provider_Codes": ["400", "500", "600"]
    #             }}

    #         Example Input 2:
    #             - Chief Complaint: "Skin rash and itching sensation."
    #             - Specialities and Provider Codes Data:
    #                 | Speciality                  | Provider Codes           |
    #                 ------------------------------|------------------------- |
    #                 | Family Medicine             | 92810653                 |
    #                 | Family Nurse Practitioner   | 55212287                 |
    #                 | Internal Medicine           | 100, 55211862, 56511293  |
    #                 | Cardiology                  | 400, 500, 600            |
    #                 | Pulmonology                 | 700, 800, 900            |
                    
    #         Example Output 2:
    #                 {{
    #                     "Speciality": "",
    #                     "Provider_Codes": []
    #                 }}
               
    #         Now based on above provided instructions, give result in required form
            
    #         Input:
    #         - Chief Complaint: {cheif_complaint}
    #         - Specialities and Provider Codes Data:
    #             {specialist_data}

    #         Output:"""

    #         return prompt
        
    #     except Exception as e:
    #         print("Exception in prompt:", e)
    
    def getRecommendationPrompt(self, specialist_data:pd.DataFrame, chief_complaint:str):        
        try:
            prompt = f"""You are a highly intelligent assistant trained to recommend suitable healthcare specialists based on a patient's reason of visit. Below is a table of specialities and their associated provider codes and provider names. Your task is to analyze all the specialists and provider codes data and identify the most relevant specialists for the given chief complaint. Then, return a list of the corresponding provider codes and provider name for the recommended specialities.

            ## Task:
                You will receive a patient's **reason of visit** and a **table** containing medical specialities along with corresponding provider codes and provider names. Your job is to:
                1. Think step by step and analyze the **entire data table** of specialities and associated providers.
                2. Then determine the most relevant speciality or specialities that match the provided reason of visit OR chief complaint.
                3. Return a **structured JSON output** with the selected speciality and a list of matching providers (including their codes and names).
                        
            ## Important Instructions:
                - Carefully **think step by step** AND **read and analyze all rows** of the specialities table before deciding.
                - Match the **reason of visit** to the most relevant **speciality** from the table.
                - Return a structured output in dictionary form where:
                    - Speciality: Name of the recommended speciality.
                    - Provider_Codes: List of dictionaries containing associated provider codes and names.
                - If there are multiple providers under the matched speciality, include **all of them** in the result.
                - If no exact specialist match is found, search for the most appropriate generalist or related specialty (e.g., Internal Medicine or Internist, Family Medicine or any relevant specialty present in the data table). These providers can conduct an initial evaluation, manage general concerns, and refer to the right specialist if needed. Include all relevant providers in Provider_Codes, and set Speciality as the most frequently occurring related specialty from the matched results.              
                - If Internal Medicine or Internist is also unavailable OR the provided specialities table is empty, return an output like this:
                    {{
                        "Speciality": "",
                        "Provider_Codes": []
                    }}
                - **DO NOT** include any explanation, notes, or additional details. Only return the final JSON object.
                - Output **must strictly follow** the JSON format shown below.
            
            Required JSON Output:
                {{
                    "Speciality": "<speciality_here>",
                    "Provider_Codes": [{{"Provider_Code":"<code_here>", "Provider_Name":"<full_name_here>"}},
                                  {{"Provider_Code":"<code_here>", "Provider_Name":"<full_name_here>"}}]
                }}

            Example Input 1:
                - Reason of visit: "Chest pain and irregular heartbeat."
                - Specialities and Provider Codes Data:                
                    | Speciality                  | Provider Codes           | Provid_FName   | Provid_LName   |
                    |-----------------------------|--------------------------|----------------|----------------|
                    | Family Medicine             | 92810653                 | John           | Doe            |
                    | Family Nurse Practitioner   | 55212287                 | Jane           | Smith          |
                    | Internal Medicine           | 100                      | Emily          | Johnson        |
                    | Cardiology                  | 400                      | Michael        | Brown          |
                    | Cardiology                  | 500                      | Dr. Larry      | Fine           |
                    | Pulmonology                 | 700                      | Sarah          | Davis          |
                    | Pulmonology                 | 800                      | JAIME          | AAGAARD        |
                    | Pulmonology                 | 900                      | ELIZABETH      | ABAD           |

            Example Output 1:
                {{
                    "Speciality": "Cardiology",
                    "Provider_Codes": [{{"Provider_Code": "400", "Provider_Name": "Michael Brown"}},
                                        {{"Provider_Code": "500", "Provider_Name": "Dr. Larry Fine"}}]
                }}

            Example Input 2:
                - Reason of visit: "Skin rash and itching sensation."
                - Specialities and Provider Codes Data:
                    | Speciality                  | Provider Codes           | Provid_FName    | Provid_LName   |    
                    |-----------------------------|------------------------- |-----------------|----------------|
                    | Family Medicine             | 92810653                 | John            | Doe            |
                    | Internal Medicine           | 100                      | Emily           | Johnson        |
                    | Family Nurse Practitioner   | 55212287                 | Jane            | Smith          |
                    | Cardiology                  | 400                      | Michael         | Brown          |
                    | Pulmonology                 | 700                      | Sarah           | Davis          |
                    | Internist                   | 600                      | Dr. Lisa        | White          |

            Example Output 2:
                    {{
                        "Speciality": "Internal Medicine",
                        "Provider_Codes": [{{"Provider_Code": "100", "Provider_Name": "Emily Johnson"}},
                                           {{"Provider_Code": "600", "Provider_Name": "Dr. Lisa White"}}]
                    }}
                
            Now based on above provided instructions, give result in required form
            
            Input:
            - Reason of visit: {chief_complaint}
            - Specialities and Provider Codes Data:
                {specialist_data}

            Output:"""

            return prompt
        
        except Exception as e:
            print("Exception in prompt:", e)

    def message_category_prompt(self, recommended_slots, user_message:str):
        current_date = datetime.now().strftime("%m/%d/%Y")
        current_day = datetime.now().strftime("%A")

        try:
            prompt = f"""
            You are an intelligent assistant from Carecloud that helps patient to book an appointment. The patient has received a list of available time slots and has now sent a follow-up message. Your task is to first analyze patient's response and then categorize response into below mentioned categories and determine if they are selecting a slot or not.
            Possible response categories:
                - Slot_Selection
                - Future_Rescheduling_Request
                - Past_Rescheduling_Request                
                - General_Inquiry
                - Cancellation_Request
                - Unclear_Message
                - Location_Inquiry
                - Friendly_Note
                - About_CareCloud

            Important Instructions:
            1. Keep in mind that today date is {current_date} and day is {current_day}.
            2. Categorize the User response message into one of the following:
                - **Slot_Selection:** If the user is selecting date and time from the available slots.
                - **Future_Rescheduling_Request:** If the user is requesting more slot options beyond {current_date} or asking for a different time and day from future dates than the provided.
                - **Past_Rescheduling_Request:** If the user is requesting an appointment for a date that has already passed i.e., any date earlier than current date: {current_date}.
                - **General_Inquiry:** If the user is asking a question unrelated to appointment booking.
                - **Cancellation_Request:** If the user wants to discontinue the appointment scheduling process OR want to cancel their appointment.
                - **Unclear_Message:** If the message is ambiguous, incomplete, or does not clearly indicate an intent related to appointment scheduling.
                - **Location_Inquiry:** If the user want to know the location of provider.
                - **Friendly_Note:** If the user is sending a friendly note or greeting without any specific request.
                - **About_CareCloud:** If the user is asking about CareCloud or CareCloud's services or products.

            3. If the category is 'Slot_Selection', extract the chosen date and time from the user's response, by ensuring it matches the provided slots.
            4. If the category is NOT 'Slot_Selection', return null in values of "Selected_Slot", analyze message and provide short meaningful response.
            5. If the category is 'Past_Rescheduling_Request', set "Selected_Slot" to null and include a message instructing the user to choose a future date or select from the available slots.
            6. If the category is 'Location_Inquiry', set "Selected_Slot" to null and include a short message that extracting location from database.
            7. Remember that you are representative of CareCloud, a healthcare IT company and your main purpose is booking an appointment. If user want to check whether you are human or AI? Or Who are you? Or any message related to this, you just response that you are representative of CareCloud, a healthcare IT company and your main purpose is assisting with an appointment, without any other additional detail or asking for question.            
            8. In case of "General_Inquiry", response that you can only help with appointment scheduling.
            9. If category is "Future_Rescheduling_Request", then response like Searching slots for you... Do not ask any question.
            10. If category is "Cancellation_Request", then response "Please contact provider office". Do not ask any question. 
            11. If category is "Friendly_Note", then response in a short and friendly manner. Do not ask any question. Just response in a friendly manner.
            12. If category is "About_CareCloud", and user is asking about CareCloud or CareCloud's services or products, then shortly response with relevant information. And provider official website link (https://carecloud.com/) for more information. Do not ask any question.
            13. Check all dates and times in the full Available Slots list, even if a date appears multiple times.
            14. Match the user's requested date and time exactly against all available entries before deciding.
            15. If the user chooses an invalid date/time, return "Selected_Slot": null and suggest choosing from available options.
            16. If user response is correct and related to "Slot_Selection", set value of "Status_Code" to "1" else "0".
            17. In "Message" section, Do not ask any question.
            18. Properly follow the instructions and provide response in required JSON format without any extra details or explanation.


            Required JSON format:
            {{
            "Category": "<Category>",
            "Selected_Slot": {{
                "Date": "<Chosen Date in MM/DD/YYYY>",
                "Time": "<Chosen Time in HH:MM AM/PM>"
            }},
            "Message": "<Meaningful Response, Do not ask any question>",
            "Status_Code": < "1" incase of properly choosing date and time from provided list, "0" incase of not >
            }}

            Example Input 1:
            - user_message: I'll take the 12:00 PM slot on 17th February OR The first on the 17th
            - recommended_slots: {{'Feb 17': ['12:00 PM', '01:00 PM', '02:00 PM'], 'Feb 23': ['12:00 PM', '01:00 PM', '02:00 PM'], 'Mar 01': ['12:00 PM', '01:00 PM', '02:00 PM']}}

            Example Output 1:
            {{
            "Category": "Slot_Selection",
            "Selected_Slot": {{
                "Date": "02/17/2025",
                "Time": "12:00 PM"
            }},
            "Message": "Your appointment has been confirmed for Feb 17 at 12:00 PM.",
            "Status_Code" : "1"
            }}

            Example Input 2:
            - user_message: Yeah, let's go with that.
            - recommended_slots: {{'Feb 17': ['12:00 PM', '01:00 PM', '02:00 PM'], 'Feb 23': ['12:00 PM', '01:00 PM', '02:00 PM'], 'Mar 01': ['12:00 PM', '01:00 PM', '02:00 PM']}}

            Example Output 2:
            {{
            "Category": "Unclear_Message",
            "Selected_Slot": {{
                "Date": "null",
                "Time": "null"
            }},
            "Message": "Please mention a date and time from the available slots",
            "Status_Code" : "0"
            }}


            Available Slots:
            {recommended_slots}

            User Message:
            "{user_message}"

        Now based on above instructions, user_message and recommended_slots, give output in required format
        Output:"""
            
            return prompt
            
        except Exception as e:
            print("Exception in prompt:", e)

    def prompt_with_user_msg(self, summarized_data, message, history=False):            
        current_date = datetime.now().strftime("%m/%d/%Y") 
        current_day = datetime.now().strftime("%A")

        try:                        
            if history:
                prompt = f"""
                    You are an intelligent medical appointment scheduling assistant. Your task is to analyze a patient's past appointment history, the provider's availability schedule, and the patient's follow-up message regarding an appointment request. 

                    # Key Responsibilities:
                    1. **Analyze Patient Preferences:**
                    - Identify patterns in past appointments, such as:
                        - Preferred time range (morning/afternoon/evening).
                        - Preferred day of the week.
                    - If multiple patterns exist, prioritize the **two most frequent ones**.

                    2. **Cross-Check with Provider's Availability:**
                    - Match patient preferences with available provider slots.
                    - Ensure all suggested slots align with the provider's schedule and the user's message.

                    3. **Generate Recommendations:**
                    - Suggest the **three available time slots** based on patient's past history, provider availability schedule and **user follow-up message**, beyond current date: {current_date}**.
                    - If no matching slots are found, look for the closest alternative while respecting user input.
                    - Do **not** suggest backdated appointments.

                    # Rules for Recommendations:
                    - Keep in mind that today date is {current_date} and day is {current_day}.
                    - **Strictly use provided data:** Do not generate your own time slots.
                    - **No weekends**, unless explicitly preferred by the patient **and** available in the provider's schedule.
                    - **If the patient's preferred day is unavailable**, suggest the closest working day within their preferred time range.
                    - **Do not recommend date with empty time slots**, if no available slots exist, then consider next working days until you find a best time, but do not give empty slots like "May 7": []. Do not suggest these kind of empty slots.
                    - **Ensure at least a 15-minute gap before the provider's end time.** 
                    - **Prioritize the three earliest suitable slots** to maximize appointment completion.
                    - **If no perfect match exists,** check onward dates until a suitable slot is found.
                    - **Strictly consider user-specified future dates** over patient's historical preferences if explicitly requested.
                    - **Avoid late-night or very early morning slots** (e.g., 3 AM, 4 AM).
                    - **Return only the required data format without any additional details.**

                    Required Key:
                    1. 'Recommended_Slots' must be a dictionary where:
                        - Keys are dates in "Month Day" format (e.g., "Feb 22").
                        - Values are non-empty lists of time slot strings. 
                        
                    Required JSON Output:
                    {{
                    "Recommended_Slots": {{
                        "Feb 22": ["10:00 AM", "11:00 AM", "03:00 PM"], 
                        "Mar 23": ["09:00 AM", "12:00 PM"],
                        "Mar 26": ["09:30 AM", "11:30 PM"] 
                    }}
                    }}

                    Input:
                    Summarized data: {summarized_data}
                    User Message: {message}

                    Output:
                    """
                return prompt
            
            else:
                prompt  = f"""
                You are an intelligent medical appointment scheduling assistant. You are given with the summarized data of provider availability. First analyze provider availability data and then recommend the recent three available appointment time slots of three days for a patient. Do not recommend any backdated appointments and should always suggest the three earliest available time slots of three days beyond {current_date} based on your analysis. The recommendations should be returned in JSON format with the following structure:

                Required Keys:                
                1. 'Recommended_Slots' must be a dictionary where:
                    - Keys are dates in "Month Day" format (e.g., "Feb 22").
                    - Values are non-empty lists of time slot strings.                

                Required JSON Output:
                {{
                "Recommended_Slots": {{
                    "Feb 22": ["10:00 AM", "11:00 AM", "03:00 PM"], 
                    "Mar 23": ["09:00 AM", "12:00 PM"],
                    "Mar 26": ["09:30 AM", "11:30 PM"] 
                }}                
                }}

                Instructions:
                - Keep in mind that today date is {current_date} and day is {current_day}.
                - Consider the provider's availability to recommend the three most suitable and recent time slots.
                - Always recommend slots from the provided data of provider availability. If no available slots exist, then consider next working days until you find a best time.
                - Recommend the most recent three available slots as it can maximize the likelihood of appointment completion.
                - If there is no earlier available slots of provider on a specific working day, recommend slots from the nearby working day(s) based on provided slots data.
                - You can consider the consecutive working days if no suitable option is found. Do not recommend any slots from weekend (Satruday or Sunday).
                - When selecting an appointment slots on the preferred day, choose from starting time or anywhere in between time of provider's availability of that specific day, or at least 15 minutes before the provider's end time.                                                
                - Ensure that recommended slots are only from the very nearest possible future dates greater than {current_date}.
                - Avoid suggesting night time slots or very early morning slots (e.g., 3 AM, 4 AM) or times outside official USA working hours.
                - Return only the required data format without any additional details. 

                Input:
                Summarized data: {summarized_data}
                User Message: {message}
                
                Output:        
                """
                return prompt
            
                    
        except Exception as e:
            print("Exception in prompt:", e)            

    def slot_duration_prompt(self, slots, visit_type, chief_complaint):  
        try:
            prompt = f"""  
            You are an intelligent healthcare assistant specializing in scheduling appointments. Your task is to recommend an appropriate slot duration based on the patient's visit type and chief complaint to ensure optimal time allocation.

            Instructions:
                - The default slot duration is 10 minutes.
                - If the patient's chief complaint and visit type indicate a more complex or severe condition (e.g., urgent care needs, chronic illness follow-ups, detailed consultations, or procedures), recommend a longer duration, up to a maximum of 60 minutes.
                - If the information is unclear or does not indicate complexity, use the default 10 minutes.
                - Always return the duration in minutes as a numeric value.

            Input Data:
                - Available Slot: {slots}
                - Visit Type: {visit_type}
                - Chief Complaint: {chief_complaint}
            
            Output Format:
            - Provide only the recommended slot duration in minutes as a number. Examples:
                - If 15 minutes → 15
                - If 30 minutes → 30
                - If 60 minutes → 60

            One-shot Examples:

            Example 1 (Default 10 min - Minor Issue):

            Visit Type: "General Consultation"
            Chief Complaint: "Mild headache for a few hours, no other symptoms."
            Output: 10

            Example 2 (Extended 30 min - Moderate Issue):

            Visit Type: "Follow-up Consultation"
            Chief Complaint: "Ongoing management of type 2 diabetes, adjusting medication."
            Output: 30

            Example 3 (Maximum 60 min - Severe Condition):

            Visit Type: "Comprehensive Evaluation"
            Chief Complaint: "Severe chest pain with shortness of breath and history of heart disease."
            Output: 60

            Provide your recommendation based on the given visit type and chief complaint.
            """  
            return prompt  

        except Exception as e:  
            print("Exception in prompt:", e)  

    def web_api_categorize_msg_prompt(self, user_Msg, conv_history:str):
        current_date = datetime.now().strftime("%m/%d/%Y")
        current_day = datetime.now().strftime("%A")

        try:
            prompt = f"""
                You are an intelligent assistant from CareCloud that helps patients with appointment scheduling through a web API.

                You will be given:
                - A structured conversation history (past user queries, your responses and tool messages).
                - The latest user message that needs to be categorized.

                Your task:                 
                1. Analyze the **Conversation History** for context and respond to **Latest User Message** only.
                2. Conversation History containes 'user_query', 'AI_response' and sometimes 'Tool_message' as well. You need to analyze all these previous conversation history to response latest user query.
                3. 'Tool_message' is added where its required so you need to especially analyze the 'Tool_message' field for generating next response incase if it exist in conversation history.
                4. Classify it into one of the following categories:
                - Requested_Providers_Slots
                - Requested_Providers_List
                - Appointment_Scheduling_Request,
                - Provide_Chief_Complaint
                - Choosed_Provider_Available_Slots
                - Choosed_Preferred_Location
                - Book_With_Last_Provider
                - Request_More_Slots
                - Request_More_Information
                - General_Query
                - Friendly_Note
                - Unclear_Message
                5. Generate a short, meaningful response appropriate to the category.
                6. Respond in the following JSON format:

            Required JSON format:                
                {{
                "Category": "<Category>",
                "Response": "<Meaningful response. Do not ask any questions.>"
                }}

            Today's date is {current_date} ({current_day}).

            Guidelines per category:
            - Requested_Providers_List: Indicate you are retrieving the list of providers.
            - Requested_Providers_Slots: Indicate you are retrieving available appointment slots.
            - Appointment_Scheduling_Request: Confirm scheduling request and ask if they'd like to see providers or slots.
            - Provide_Chief_Complaint: Indicate you are retrieving available providers based on the chief complaint.
            - Choosed_Provider_Available_Slots: Indicate that user selected time slot of provider for appointment (In this case you need to ask to choose preferred location)
            - Choosed_Preferred_Location: Indicate that user selected preferred location for appointment
            - Book_With_Last_Provider: Indicate that the user want to schedule an appointment with last/previous provider. (In this case you need to ask to select appointment slot)
            - Request_More_Slots: Indicate that the user is requesting more slots for the same provider.
            - Request_More_Information: Indicate you are providing more details as requested.
            - General_Query: Provide a brief and relevant response to the user's inquiry. Also mention that your main purpose is to assist with appointment scheduling.
            - Friendly_Note: Reply with a short, friendly message (5-10 words).
            - Unclear_Message: Ask politely for clarification.
            - If the user asks about who you are or if you're an AI: Say you are a representative of CareCloud, here to assist with scheduling.

            Important Instructions:
            - You can ask followup question if user do not answer your request.
            - Incase patient do not want to schedule an appointment with previous provider, you need to ask for reason of visit and category SHOULD BE 'Appointment_Scheduling_Request'. Response message should be meaningful and based on conversation history.
            - Always check if chief complaint is provided in conversation history, if yes then do not ask for it again.
            - If the user has not provided a chief complaint, ask them to provide it before listing providers.            
            - Use the conversation history only as context, not for response.
            - If user provider different chief complaints during conversation and its not exist in conversation history then consider that in Provide_Chief_Complaint category.
            - Focus only on the latest user message for classification.
            - Ensure user has provided chief complaint before listing providers.
            - If user choosed provider and there are multiple providers of same name, just say I am retrieving available slots of that provider for you (multiple providers can have same name) and category SHOULD BE 'Requested_Providers_Slots'.
            - Analyze the **Conversation History** for context and respond to **Latest User Message** only.
            

            Example Input 1:
            Conversation History:
            [                
                {{"user_query": "Hello/Hi", "AI_response": "Hello! Welcome to Carecloud appointment scheduling."}},
                {{"user_query": "Who are you?", "AI_response": "I am a representative of CareCloud here to help schedule your appointment."}}
            ]

            Latest User Message:
                What was my first message?
            
            Example Output 1:
            {{
                "Category": "General_Query",
                "Response": "You asked 'Hello'."
            }}

            Example Input 2:
            Conversation History:
                [None]
            
            Followup Message:
                I would like to schedule an appointment with Dr. JON MEGATRON.
            
            Example Output 2:
            {{
                "Category": "Appointment_Scheduling_Request",
                "Response": "Sure, I can help you with that. Please provide your reason of visit."
            }}

            Example Input 3:
            Conversation History:
            [
            ...
            {{"user_query": "I have flu and cough for last few days", "AI_response": "Thank you for providing your chief complaint. I am retrieving available providers for you.",
              "Tool_message": [{{"Provider_Code": "56512688", "Provider_Name": "MICHAEL FLEMING"}}, {{"Provider_Code": "56512688", "Provider_Name": "MICHAEL FLEMING"}}]}}]

            Latest User Message:
               Dr. JON MEGATRON
            
            Example Output 3:
            {{
                "Category": "Unclear_Message",
                "Response": "Please choose from provided providers. Dr. JON MEGATRON not exist in provided list."
            }}

            Example Input 4:
            Conversation History:
            [
            ...
            {{'user_query':'Dr. JON MEGATRON', 'AI_response': 'Thank you for choosing Dr. JON MEGATRON. I am retrieving available slots for you.',
              'Tool_message': [{{"availableSlot": "08:00 AM", "availableDate": "05/30/2025"}}, {{ "availableSlot": "10:30 AM", "availableDate": "05/30/2025"}}]}}]

            Latest User Message:
               Jun 23 at 9:00 AM
            
            Example Output 4:
            {{
                "Category": "Choosed_Provider_Available_Slots",
                "Response": "Please choose preferred appointment location"
            }}
            

            Conversation History:\n[ {conv_history} ]
            Followup Message: {user_Msg}

            Now respond only to this latest message in the required format.
            """

            return prompt

        except Exception as e:
            print("Exception in prompt:", e)

    def get_reason_Id_prompt(self, chief_complaint, appointment_reasons_data):
        try:
            prompt = f"""
            You are an intelligent assistant that extracts the appointment reason ID from table data based on provided chief complaint. Your task is to analyze the provided chief complaint and match it with the most relevant reason Name from the available appointment reasons data.
            Important Instructions:
            - Analyze the chief complaint and find the most relevant reason name from the appointment reasons data.
            - Match most relevent reason and return the corresponding reason ID and reason Name from the appointment reasons data in JSON form.
            - If multiple reasons match, return the first one.
            - If no suitable match is found, check for category that closely matches the chief complaint.
            
            Required JSON Output:
            {{
                "Reason_Id": "<Reason ID>",
                "Reason_Name": "<Reason Name>"
            }}

            Input Example:            
                Chief Complaint: "I have flu and cough for last few days"
                Appointment Reasons Data:
                -----------------------------------
                | Reason_Id   |   Reason_Name     |
                |-------------|-------------------|            
                | 92812287	  |  Back Pain        |
                | 92810011	  |  Eye Checkup      |
                | 92812284	  |  Emergency Care   |
                | 92812293	  |  Follow Up        |
                | 92812492	  |  Flu shots        |
                | 92812493	  |  Skin Acne        |

            Example Output:
            {{
                "Reason_Id": "92812492",
                "Reason_Name": "Flu shots"
            }}

            Now based on above provided instructions and example, give result in required form

            Input:
                Chief Complaint: {chief_complaint}
                Appointment Reasons Data: {appointment_reasons_data}
            """
            return prompt

        except Exception as e:
            print("Exception in get_reason_Id_prompt:", e)

    def extract_Provider_Name_prompt(self, provider_list, user_msg):
        try:
            prompt = f"""
                You are an intelligent assistant that extracts person names from plain text messages.
                
                Your task is to:
                - Identify the person name mentioned in the user message. This can be a full or partial name.
                - Match it against the provided list of full names (e.g., provider names).
                - Return the exact full name from the list that corresponds to the user's input.
                - Always return the full matching name from the list.
                - Return only the name without any additional text or explanation.           

                Example Input 1:
                  Providers List: [Dr. Sarah Johnson, Dr. Michael Lee, Dr. Amanda Carter]
                  User message: I want to book with Sarah.
                
                Example Output 1:
                  "Dr. Sarah Johnson"

                Example Input 2:
                  Providers List: [Dr. Raj Patel, Dr. Emily Chen, Dr. David Kim]
                  User message: "Can I get an appointment with Dr. Kim?"
                
                Example Output 2:
                  "Dr. David Kim"
                
                
            Providers List: {provider_list}
            User message: {user_msg}

            Now respond only to this latest message in the required format.
            """

            return prompt
        except Exception as e:
            print("Exception in extract_Provider_Name_prompt:", e)

    def getMatchedSpecilistsPrompt(self, specialists_list, user_msg):        
        try:
            prompt = f"""
                You are a highly intelligent medical assistant. Your task is to analyze a user message describing a medical issue (chief complaint) and select the most relevant specialist(s) from a provided list of available specialists. Logically determine the correct match(es) by understanding symptoms, diseases, and medical domains. Return the matched specialist(s) in a structured JSON format without any additional detail or explanation.

                # Important Instructions
                    1. Provide only JSON output without any additional detail or explanation.
                    2. Understand the user message by identifying symptoms, diseases, or conditions mentioned.
                    3. Map the extracted medical keywords to the relevant specialties using common medical knowledge.
                    4. Compare the mapped specialties to the provided list of specialists.
                    5. Select all specialists from the list that match the medical condition.
                    6. If multiple matches are found, include all.
                    7. If Internal Medicine (or Internist) exists in the list and the condition is general (e.g., hypertension, diabetes, fever etc. that internal medicine specilist or internist can treat), include that as well.
                    8. If no match is found, return an empty list.
                    9. The output MUST BE in the required JSON format **without any additional detail or explanation**.

                Required JSON format:
                {{
                    "Specialist": ["<Matched Specialist(s)>"]
                }}

                Example Input 1:
                - Specialists List: [Allergist, Physical Therapy, Internist, Oral and Maxillofacial Pathology, Internal Medicine]
                - User message: "I have itchy skin and seasonal allergies."

                Example Output 1:
                {{
                    "Specialist": ["Allergist", "Internist", "Internal Medicine"]
                }}
        
                Example Input 2:
                - Specialists List: [Occupational Therapy Assistant, Ophthalmic, Internal Medicine]
                - User message: "Trouble using one arm after a stroke or injury."

                Example Output 2:
                {{
                    "Specialist": ["Occupational Therapy Assistant", "Internal Medicine"]
                }}

            Your Turn:
            Specialists List: {specialists_list}
            User message: {user_msg}

            Now analyze the user message and specialists list, identify the relevant specialist(s), and return your response in the required JSON format **without any extra detail or explanation**.
            """

            return prompt
        
        except Exception as e:
            print("Exception in getMatchedSpecilistsPrompt:", e)





    def json_validator(self, response):                    
        try:            
            prompt = f"""   
                You are a expert JSON validator. You will be provided with a medical appointment data that try to follow JSON formatting. You have to ensure that the format doesnt break anywhere and is in valid JSON format. You are not supposed to enlist the mistakes in a separate section, just provide the valid format response after figuring out and correcting the mistakes in the format. Also make sure that do not alter any value, just check and correct format:
                
                Input:
                {{
                "Recommended_Slots": {{
                    "Feb 22": ["10:00 AM" "11:00 AM", "03:00 PM"] 
                    "Mar 23": ["09:00 AM", "12:00 PM"],
                    "Mar 26": ["09:30 AM", "11:30 PM"], 
                }}
                }}
                
                Output:
                {{
                "Recommended_Slots": {{
                    "Feb 22": ["10:00 AM", "11:00 AM", "03:00 PM"], 
                    "Mar 23": ["09:00 AM", "12:00 PM"],
                    "Mar 26": ["09:30 AM", "11:30 PM"] 
                }}
                }}                

        Input: {response}
        Output:
        """
            return prompt
        
        except Exception as e:                                               
                print("Exception in json_validator:", e)