from django.shortcuts import render
# Framework
from rest_framework.views import APIView
from rest_framework import status
from rest_framework.response import Response
from django.http import HttpResponse
from django.core.cache import cache
# Modules
from rescheduling_app.prompts import Prompts
from rescheduling_app.utils.logging_utils import log, log_request
from rescheduling_app.generate_response import GenerateResponse
from rescheduling_app.generate_openai_respose import GenerateOpenAIResponse
from rescheduling_app.db_operations import BusinessLogic
from rescheduling_app.data_processing import getSummarizedDataForPrompt
from rescheduling_app.parse_logs import parse_logs_to_dataframe, parse_logs_for_user_response, make_dataframe, make_dataframe_user_response
from rescheduling_app.location import generate_google_maps_url
from rescheduling_app.traverse_slots import get_all_previous_slots
from rescheduling_app.enums import AppointmentChatBotStatus as STATUS
# Misc
import pandas as pd
import os, re, requests, ast
import pickle
import json
import secrets
import time
from datetime import datetime, timedelta
import traceback
import logging
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import quote
# import os

BASE_DIR = Path(__file__).resolve().parent.parent

prmpt_obj = Prompts()
gr_obj = GenerateResponse()
gr_openai_obj = GenerateOpenAIResponse()
LOGS_FILE_PATH = f'{BASE_DIR}/LOGS/info.log'

print(f"Log file path: {LOGS_FILE_PATH}")


class SmartScheduling(APIView):
    def get(self, request):
        return HttpResponse("Smart Rescheduling is up and running!")
    
# Create your views here.
class Rescheduler(APIView):
    def post(self, request):
        try:
            uid = secrets.token_hex(4)
            CURRENT_DATE = datetime.now().date()
            if request.method != 'POST':
                log('error',uid,"Invalid Request")
                log('error',uid,'Status Code: 400')
                return Response({"result": {}, "status": "Failure", "message : ": "Get method is not allowed"}, status=400)
            
            log_request('info', uid, request)

            patient_ID = request.data.get('patient_ID')
            provider_Code = request.data.get('provider_Code')

            log('info',uid, f"Patient ID: {patient_ID}")
            print(f"\npatient_ID: {patient_ID}")
            
            log('info',uid, f"Provider Code: {provider_Code}")
            print(f"provider_Code: {provider_Code}")

            patient_status, patient_Appointment_df = BusinessLogic.getPatientAppointmentHistory(patient_ID)
            log('info',uid, f"Patient status: {patient_status}")
            log('info',uid, f"Patient Appointment History Columns:\n{patient_Appointment_df.columns}")


            if patient_status:
                provider_status, provider_Availability_df = BusinessLogic.getProviderAvailability(provider_Code)
                log('info',uid, f"Provider status: {provider_status}")
                log('info',uid, f"Provider Availability Columns:\n{provider_Availability_df.columns}")
                
                summarized_data_with_history = getSummarizedDataForPrompt(provider_Availability_df, patient_Appointment_df)  # sequence of parameters is important and it must be this

                prompt_with_history = prmpt_obj.prompt(summarized_data_with_history, history=True)
                log('info',uid, f"Prompt when patient history:\n{prompt_with_history}")

                start = time.time()
                raw_response = gr_obj.generate_response(uid, prompt_with_history)
                end = time.time()
                
                log('info', uid, f"Time Taken: {end - start} seconds")                
                # response = gr_openai_obj.generate_response(uid, prompt_with_history)
                log('info',uid, f"Response:\n{raw_response}")

                response = raw_response.replace('```json', '')
                response = response.replace('```', '')

                # Saving logs in DB
                # logs_data = parse_logs_to_dataframe(LOGS_FILE_PATH)
                logs_data = make_dataframe(uid, CURRENT_DATE, patient_ID, practice_code=None, provider_Code=provider_Code,
                                            patient_status=patient_status, response=raw_response, chief_Complaint=None,
                                            visit_Type=None, recommended_specialists=None)
                                
                log("info", uid, f'Record for insertion with uid {uid}\n{logs_data[logs_data["uid"] == uid]}')
                BusinessLogic.dump_dataframe_to_sql_server(logs_data, uid) # To AI_DB

                return Response({"Response": json.loads(response), "UID":uid}, status=200)

            else:
                provider_status, provider_Availability_df = BusinessLogic.getProviderAvailability(provider_Code)
                log('info',uid, f"Provider status:\n{provider_status}")
                log('info',uid, f"Provider availability columns:\n{provider_Availability_df.columns}")

                summarized_data_without_history = getSummarizedDataForPrompt(provider_Availability_df)    # sequence of parameters is important

                prompt_without_history = prmpt_obj.prompt(summarized_data_without_history)
                log('info',uid, f"Prompt when no patient history:\n{prompt_without_history}")

                start = time.time()
                raw_response = gr_obj.generate_response(uid, prompt_without_history)
                end = time.time()

                log('info', uid, f"Time Taken: {end - start} seconds")
                # response = gr_openai_obj.generate_response(uid, prompt_without_history)
                log('info',uid, f"Response:\n{raw_response}")

                response = raw_response.replace('```json', '')
                response = response.replace('```', '')

                # Saving logs in DB
                # logs_data = parse_logs_to_dataframe(LOGS_FILE_PATH)
                logs_data = make_dataframe(uid, CURRENT_DATE, patient_ID, practice_code=None, provider_Code=provider_Code,
                            patient_status=patient_status, response=raw_response, chief_Complaint=None,
                            visit_Type=None, recommended_specialists=None)
                
                log("info", uid, f'Record for insertion with uid {uid}\n{logs_data[logs_data["uid"] == uid]}')
                BusinessLogic.dump_dataframe_to_sql_server(logs_data, uid) # To AI_DB

                return Response({"Response": json.loads(response), "UID":uid}, status=200)
            
        except Exception as e:
            traceback.print_exc()
            log('error', uid, str(e))
            return Response({"status": "Failure", "message : ": str(e)}, status=400)


class EnhancedRescheduler(APIView):
    def post(self, request):
        try:
            uid = secrets.token_hex(4)
            if request.method != 'POST':
                log('error', uid, "Invalid Request")
                log('error', uid, 'Status Code: 400')
                return Response({"result": {}, "status": "Failure", "message": "Get method is not allowed"}, status=400)

            log_request('info', uid, request)

            patient_ID = request.data.get('patient_ID')
            practice_Code = request.data.get('practice_code')
            chief_Complaint = request.data.get('chief_complaint')
            visit_Type = request.data.get('visit_type')

            log('info',uid, f"Patient ID: {patient_ID}")            
            log('info',uid, f"Practice Code: {practice_Code}")
            log('info',uid, f"Chief Complaint: {chief_Complaint}")
            log('info',uid, f"Visit Type: {visit_Type}")

            status, result = BusinessLogic.getSpecialistsDetail(practice_Code)
            if status:
                print(f"getSpecialistsDetail Result:\n{result}")
                prompt = prmpt_obj.getRecommendationPrompt(result, chief_Complaint)
                print(f"Speciality matching prompt:\n{prompt}")
                response = gr_obj.generate_response(uid, prompt)
                # response = gr_openai_obj.generate_response(uid, prompt)
                response = response.replace('```json', '').replace('```', '')
                response = json.loads(response)

                log('info',uid, f"All Recommended Specialists: {response}")

                print(f"Model response:\n{response}")

                provider_codes = response.get("Provider_Codes")
                if not provider_codes:
                    return Response({"Response": "chief complaint does not match with any record of providers data"}, status=400)
                                
                # Fetch preferred providers for the patient                            
                result = BusinessLogic.getPreferredProvider(patient_ID, provider_codes)

                print(f"getPreferredProvider result:\n{result}")

                if result.empty:
                    print(f"No appointment found for patient {patient_ID} with providers {provider_codes}. Using first two providers")
                    provider_codes = provider_codes[:5]  # Take only the first 5 provider codes

                    print(provider_codes)

                else:
                    print(f"Preferred provider data available. Proceeding with top 2 matched providers.")
                    provider_codes = result['Provider_Code'].value_counts().head(5).index.tolist()

                    print(provider_codes)

                def get_provider_availability(provider_code):
                    provider_status, provider_Availability_df = BusinessLogic.getProviderAvailability(provider_code)
                    return provider_code, provider_status, provider_Availability_df

                with ThreadPoolExecutor() as executor:
                    futures = {executor.submit(get_provider_availability, code): code for code in provider_codes}
                    availability_results = []

                    for future in futures:
                        try:
                            provider_code, provider_status, provider_Availability_df = future.result()
                            if provider_status:
                                availability_results.append((provider_code, provider_Availability_df))
                        except Exception as e:
                            log('error', uid, f"Error fetching availability for provider {futures[future]}: {e}")

                if not availability_results:
                    return Response({"Response": "No available providers found for the given chief complaint."}, status=400)

                # Gather all slots for all providers
                all_slots = []
                for provider_code, provider_Availability_df in availability_results:
                    patient_status, patient_Appointment_df = BusinessLogic.getPatientAppointmentHistory(patient_ID)

                    if patient_status:
                        summarized_data_with_history = getSummarizedDataForPrompt(provider_Availability_df, patient_Appointment_df)
                        prompt = prmpt_obj.prompt(summarized_data_with_history, history=True)
                    else:
                        summarized_data_without_history = getSummarizedDataForPrompt(provider_Availability_df)
                        prompt = prmpt_obj.prompt(summarized_data_without_history)

                    print(f"Slots recommendation prompt:\n{prompt}")
                    response = gr_obj.generate_response(uid, prompt)
                    # response = gr_openai_obj.generate_response(uid, prompt)
                    response = response.replace('```json', '').replace('```', '')
                    provider_slots = json.loads(response)
                                        
                    all_slots.append({"Provider_Code": str(provider_code), "Slots": provider_slots})

                # Saving logs in DB
                logs_data = parse_logs_to_dataframe(LOGS_FILE_PATH)
                print(logs_data)
                BusinessLogic.dump_dataframe_to_sql_server(logs_data)

                log('info',uid, f"Response:\n{all_slots}")                
                return Response({"Response": all_slots}, status=200)

            else:
                return Response({"Response": result}, status=200)

        except Exception as e:
            traceback.print_exc()
            log('error', uid, str(e))
            return Response({"status": "Failure", "message": str(e)}, status=400)


class UserResponse(APIView):
    def post(self, request):
        try:                
            uid = secrets.token_hex(4)
            CURRENT_DATE = datetime.now().date()
            if request.method != 'POST':
                log('error', uid, "Invalid Request")
                log('error', uid, 'Status Code: 400')
                return Response({"result": {}, "status": "Failure", "message": "Get method is not allowed"}, status=400)
            
            log_request('info', uid, request)

            previous_uid = request.data.get('previous_uid')
            patient_account = request.data.get('patient_account')
            provider_code = request.data.get('provider_code')
            practice_code = request.data.get('practice_code')
            user_message = request.data.get('user_message')
            appointment_id = request.data.get('appointment_id')
            
            log('info',uid, f"previous_uid: {previous_uid}")
            log('info',uid, f"patient_account: {patient_account}")
            log('info',uid, f"practice_code: {practice_code}")
            log('info',uid, f"provider_code: {provider_code}")
            log('info',uid, f"user_followup_msg: {user_message}")
            log('info',uid, f"appointment_id: {appointment_id}")

            location_status, location_code = BusinessLogic.getLocationCode(patient_account, provider_code)
                        
            log('info',uid, f"location_code: {location_code}")

            if location_status:                
                location_code = location_code["Location_Id"].iloc[0]                
                print(location_code)
            
            else:
                location_status, location_code = BusinessLogic.getDefaultProviderLocation(provider_code)                
                location_code = location_code["Location_Id"].iloc[0]

            status, result = BusinessLogic.getLastSessionHistory(uid, previous_uid, patient_account) # From AI_DB
            
            # print(initial_recommended_slots_date)
            # print(type(initial_recommended_slots_date))

            all_future_recommended_slots = ""

            if status:
                initial_recommended_slots_date = result['creation_date'][0]
                future_recommended_slots_status, future_recommended_slots_result = BusinessLogic.getFutureReschedulingLogs(previous_uid, patient_account, initial_recommended_slots_date) # From AI_DB
                if future_recommended_slots_status:                    
                    all_future_recommended_slots_string = get_all_recommended_slots_as_string(future_recommended_slots_result)                    
                    # print(all_future_recommended_slots_string)

                    all_future_recommended_slots = all_future_recommended_slots_string
                
            if status:
                raw_response = result['response']
                # print(raw_response)
                # print(type(raw_response))
        
                # Ensure raw_response is a string
                if isinstance(raw_response, pd.Series):
                    raw_response = raw_response.iloc[0]  # Get the first element of the Series
                    # print(type(raw_response))

                if not isinstance(raw_response, str):
                    raw_response = str(raw_response)  # Convert non-string values to string

                # print(type(raw_response))
              
                # Extract text content using regex
                # Pattern for gemini response
                # pattern = r"```json\\n(.*?)\\n```"

                # Pattern for openai  response
                pattern = r"```json\s*(.*?)(?:\s*```|$)"
                
                match = re.search(pattern, raw_response, re.DOTALL)
                
                # openai match
                if match:
                    json_string = match.group(1).strip()
                    json_string = json_string.replace('\\n', '').replace('\\"', '"')  # Clean up escape characters                                  
                    
                    # Fix unbalanced braces
                    if json_string.count('{') > json_string.count('}'):
                        json_string += '}'                
                    
                    try:
                        parsed_json = json.loads(json_string)
                        print(f"parsed_json: {parsed_json}")
                        log('info',uid, f"initial_recommended_slots: {parsed_json}")
                
                    except json.JSONDecodeError as e:
                        traceback.print_exc()
                        log('Error decoding JSON:', uid, str(e))
                        print("Error decoding JSON:", e)
                else:
                    log('info',uid, f"Invalid JSON found in response")
                
                # gemini match
                # if match:
                #     json_string = match.group(1)  # Extract JSON string part
                #     json_string = json_string.replace('\\n', '').replace('\\"', '"')  # Clean up escape characters                    
                #     print(json_string)

                #     try:
                #         parsed_json = json.loads(json_string)  # Convert to proper JSON object
                #         log('info',uid, f"initial_recommended_slots: {parsed_json}")
                #         # print(parsed_json)  # Print the cleaned JSON response

                #     except json.JSONDecodeError as e:
                #         traceback.print_exc()
                #         log('Error decoding JSON:', uid, str(e))
                #         # print("Error decoding JSON:", e)
                # else:
                #     log('info',uid, f"Invalid JSON found in response")
                    # print("Invalid JSON found in response")
                    

                initial_recommended_slots = parsed_json.get("Recommended_Slots")
                slots = str(initial_recommended_slots) + "\n" + all_future_recommended_slots
                prompt = prmpt_obj.message_category_prompt(slots, user_message)
                
                log('info',uid, f"message_category_prompt:\n{prompt}")

                start = time.time()                
                response = gr_obj.generate_response(uid, prompt)
                end = time.time()

                log('info', uid, f"Time Taken: {end - start} seconds")
                # log('info',uid, f"message_category_Response: {response}")
                response = response.replace('```json', '').replace('```', '')
                ai_response = json.loads(response)
                
                status_code = ai_response.get("Status_Code")
                print(status_code)
                
                log('info',uid, f"message_category_Response: {ai_response}")

                if int(status_code):
                    provider_code = result['provider_code'][0]
                    
                    app_date = ai_response["Selected_Slot"].get("Date")
                    time_From = ai_response["Selected_Slot"].get("Time")

                    appointment_response = book_appointment(uid, practice_code, patient_account, provider_code, location_code, app_date, time_From, appointment_id, app_reason_id="")
                    log('info',uid, f"appointment_response: {appointment_response}")

                    if appointment_response.get("message").upper() == "SUCCESS":
                        log('info' ,uid, f"isAppointmentInserted: { appointment_response['data'].get('isAppointmentInserted') }")
                        log('info' ,uid, f"finalMessage: { appointment_response['data'].get('finalMessage') }")
                        
                        # when appointment is successful
                        if appointment_response['data'].get('isAppointmentInserted') == "True":
                            return Response({"AI_Response" : ai_response, "Appointment_Response": appointment_response}, status=200)
                        
                        else:
                            # when appointment is unsuccessful (Modify AI response)
                            ai_response["Message"] = appointment_response['data'].get('finalMessage')
                            ai_response["Status_Code"] = "0"
                            ai_response['Selected_Slot']['Date'] = "Null"
                            ai_response['Selected_Slot']['Time'] = "Null"

                            return Response({"AI_Response" : ai_response, "Appointment_Response": appointment_response}, status=200)
                    
                    elif appointment_response.get("message").upper() == "APPOINTMENT RESCHEDULED SUCCESSFULLY":
                        return Response({"AI_Response" : ai_response, "Appointment_Response": appointment_response}, status=200)
                        
                    
                    else:
                        log('info',uid, f"Error while calling Appointment creation API")
                        return Response({"error": "Error while calling Appointment creation API", "details": appointment_response}, status=400)
                    # return Response({"Response": ai_response}, status=200)

                else:
                    if ai_response.get("Category") == "Future_Rescheduling_Request":
                        # print(f'Category: {ai_response.get("Category")}')                        
                        provider_code = result['provider_code'][0]

                        patient_status, patient_Appointment_df = BusinessLogic.getPatientAppointmentHistory(patient_account)
                        
                        if patient_status:
                            provider_status, provider_Availability_df = BusinessLogic.getProviderAvailability(provider_code)
                            log('info',uid, f"Provider status: {provider_status}")
                            log('info',uid, f"Provider Availability Columns:\n{provider_Availability_df.columns}")
                            
                            summarized_data_with_history = getSummarizedDataForPrompt(provider_Availability_df, patient_Appointment_df)  # sequence of parameters is important and it must be this

                            prompt_with_msg = prmpt_obj.prompt_with_user_msg(summarized_data_with_history, user_message, history=True)
                            log('info',uid, f"Prompt with user msg:\n{prompt_with_msg}")

                            start = time.time()
                            response = gr_obj.generate_response(uid, prompt_with_msg)
                            end = time.time()

                            log('info', uid, f"Time Taken: {end - start} seconds")
                            # log('info',uid, f"Future_Rescheduling_Request_Response: {response}")

                            response = response.replace('```json', '').replace('```', '')
                            final_response = json.loads(response)
                            # print(final_response)
                            
                            log('info',uid, f"Future_Rescheduling_Request_Response: {final_response}")
                            # Saving logs in DB
                            # logs_data = parse_logs_for_user_response(LOGS_FILE_PATH)
                            logs_data = make_dataframe_user_response(uid, previous_uid, CURRENT_DATE, patient_account,
                                            location_code,  user_message, initial_recommended_slots,
                                            ai_response, final_response, appointment_response=None)
                            
                            BusinessLogic.dump_future_appointment_request_to_sql_server(logs_data, uid) # To AI_DB
                            
                            return Response({"AI_Response" : ai_response, "Future_Rescheduling_Response": final_response, "UID": previous_uid}, status=200)
                        
                        else:
                            provider_status, provider_Availability_df = BusinessLogic.getProviderAvailability(provider_code)
                            log('info',uid, f"Provider status:\n{provider_status}")
                            # log('info',uid, f"Provider availability columns:\n{provider_Availability_df.columns}")

                            summarized_data_without_history = getSummarizedDataForPrompt(provider_Availability_df)    # sequence of parameters is important

                            # prompt_without_history = prmpt_obj.prompt(summarized_data_without_history)
                            prompt_without_history = prmpt_obj.prompt_with_user_msg(summarized_data_without_history, user_message, history=False)
                            log('info',uid, f"Prompt when no patient history:\n{prompt_without_history}")

                            start = time.time()
                            response = gr_obj.generate_response(uid, prompt_without_history)
                            end = time.time()

                            log('info', uid, f"Time Taken: {end - start} seconds")
                            # response = gr_openai_obj.generate_response(uid, prompt_without_history)
                            log('info',uid, f"Response:\n{response}")

                            response = response.replace('```json', '').replace('```', '')
                            final_response = json.loads(response)

                            # Saving logs in DB                            
                            # logs_data = parse_logs_for_user_response(LOGS_FILE_PATH)                            
                            logs_data = make_dataframe_user_response(uid, previous_uid, CURRENT_DATE, patient_account,
                                            location_code,  user_message, initial_recommended_slots,
                                            ai_response, final_response, appointment_response=None)
                            
                            print(f'Record for insertion with uid {uid}\n{logs_data[logs_data["uid"] == uid]}')

                            # print(logs_data)
                            BusinessLogic.dump_future_appointment_request_to_sql_server(logs_data, uid)

                            # return Response({"Response": json.loads(response), "UID":uid}, status=200)
                            return Response({"AI_Response" : ai_response, "Future_Rescheduling_Response": final_response, "UID": previous_uid}, status=200)
                                                
                    elif ai_response.get("Category") == "Past_Rescheduling_Request":                                                                        
                        return Response({"Response": ai_response}, status=200)     

                    elif ai_response.get("Category") == "Location_Inquiry":                        
                        provider_code = result['provider_code'][0]
                        status, data = BusinessLogic.getProviderLocationData(provider_code, patient_account)

                        if status:
                            location_address = data["Location_Address"][0]
                            location_name = data["Location_Name"][0]
                            location_state = data["Location_State"][0]
                            location_zip = data["Location_Zip"][0]

                            map_url = generate_google_maps_url(location_address, location_name, location_state, location_zip)                            

                            return Response({"Response": ai_response, "Location" : map_url}, status=200)

                    elif ai_response.get("Category") == "Friendly_Note":                                                                        
                        return Response({"Response": ai_response}, status=200)     

                    elif ai_response.get("Category") == "About_CareCloud":
                        return Response({"Response": ai_response}, status=200)
                    
                    else:
                        print(f'Category: {ai_response.get("Category")}')                        
                        return Response({"Response": ai_response}, status=200)
                                        
            else:
                return Response({"Response": f"Session {previous_uid} did not found for patient {patient_account}"}, status=200)
        
        except Exception as e:
            traceback.print_exc()
            log('error', uid, str(e))
            return Response({"status": "Failure", "message": str(e)}, status=400)
        

class ProviderSlots(APIView):
    def post(self, request):         
        uid = secrets.token_hex(4)
        DEFAULT_REASON_ID = "592"
        appointment_id = ""

        try:
            log_request('info', uid, request)

            # Step 1: Extract payload
            practice_Code = request.data.get('practiceCode')
            patient_Code = request.data.get('patientCode', '')
            user_Msg = request.data.get('userMsg', '')
            Session_ID = request.data.get('sessionId', '')            
            provider_Code = request.data.get('providerCode', '')
            location_Code = request.data.get('locationCode', '')
            isTelehealth = request.data.get('isTelehealth', "false")
            app_date = request.data.get('appDate', '')
            time_From = request.data.get('timeFrom', '')
            previous_appointment = request.data.get('Previous_Appointment','')
            
            log('info', uid, f"Received Session_ID: {Session_ID}, User_Msg: {user_Msg}, Provider_Code: {provider_Code},\n \
                Practice_Code: {practice_Code}, Patient_Code: {patient_Code}, Is_Telehealth: {isTelehealth}, Location_Code: {location_Code}")

            # Step 2: Validate input
            if not practice_Code:
                return Response({"status": False, "message": "Practice code is required", "state":"Error"}, status=200)
            
            if not user_Msg:
                return Response({"status": False, "message": "User message is required", "state":"Error"}, status=200)

            if not patient_Code:
                return Response({"status": False, "message": "Patient code is required", "state":"Error"}, status=200)
            
            
            # Step 3: Fetch or build conversation history
            start = time.time()
            status, conv_record = BusinessLogic.getConversationHistory(Session_ID, practice_Code)
            end = time.time()
            print(f"[DEBUG] Execution time for getting Conversation History: {end - start} seconds")

            if status and not conv_record.empty:
                existing_history = "\n".join(conv_record['CONVERSATION_TEXT'].astype(str))
                
            else:
                existing_history = None                
                Session_ID = secrets.token_hex(6)  # First time, so generate new session
                
                # Get Last Appointment Data
                status, data = BusinessLogic.getLastAppointmentData(patient_Code, practice_Code)
                if status:
                    last_Provider_Name = data.iloc[0]['Provider_Name']
                    last_Provider_Code = data.iloc[0]['Provider_Code']
                    last_Appointment_ReasonID = data.iloc[0]['Appointment_ReasonID']
                    last_Appointment_LocationID = data.iloc[0]['Appointment_LocationID']
                    # last_Appointment_LocationName = data.iloc[0]['Appointment_LocationName']
                    last_Location_Address = data.iloc[0]['Location_Address']
                    last_Appointment_Date_Time = data.iloc[0]['Appointment_Date_Time']

                    message = f"Hello! Would you like to schedule your next appointment with Dr. {last_Provider_Name.title()} ?"
                    last_appointment_info = {
                        "Provider_Name": last_Provider_Name,
                        "Provider_Code": str(int(last_Provider_Code)),
                        "Appointment_ReasonID": str(int(last_Appointment_ReasonID)),
                        "Appointment_LocationID": str(int(last_Appointment_LocationID)),
                        "Location_Address": last_Location_Address,
                        "Appointment_Date_Time": str(last_Appointment_Date_Time)
                    }

                    formatted_info = to_custom_format(last_appointment_info)

                    conversation_text = str({"user_query": user_Msg, "AI_response": message, "Tool_message": last_appointment_info})
                    
                    start = time.time()
                    BusinessLogic.dump_conversation_history(Session_ID, patient_Code, practice_Code, provider_Code, category="Previous_Appointment", previous_appointment=last_appointment_info, conversation_text=conversation_text)
                    end = time.time()
                    print(f"[DEBUG] Execution time of dump_conversation_history: {end - start} seconds")

                    return Response({"status": True, "state": "Previous_Appointment", "current_state": STATUS.PREVIOUS_APPOINTMENT.value, "message": message, "session_id": Session_ID, "data": formatted_info}, status=200)

                else:
                    existing_history = None                
                    Session_ID = secrets.token_hex(6)  # First time, so generate new session

                    conversation_text = str({"user_query": user_Msg, "AI_response": "Last appointment of patient not exist", "Tool_message": "Last appointment of patient not exist"})
                    start = time.time()
                    BusinessLogic.dump_conversation_history(Session_ID, patient_Code, practice_Code, provider_Code, category="Previous_Appointment", conversation_text=conversation_text)
                    end = time.time()
                    print(f"[DEBUG] Execution time of dump_conversation_history: {end - start} seconds")

                    return Response({"status": True, "state": "Previous_Appointment", "message": "Last appointment of patient not exist", "session_id": Session_ID}, status=200)

            # print(f"Conversation history:\n{existing_history}")
            # print(f"Conversation history last 10: {existing_history[-10:] if existing_history else 'No history'}")

            # Step 4: Prepare prompt and get AI response
            print(f"Existing History:\n{existing_history}")

            prompt = prmpt_obj.web_api_categorize_msg_prompt(user_Msg, existing_history)
            print(f"Prompt:\n{prompt}")
            
            start = time.time()
            response_text = gr_obj.generate_response(uid, prompt, model_name="gemini-2.5-pro")
            end = time.time()
            print(f"[DEBUG] Execution time of model response for categorize user msg: {end - start} seconds")

            print(f"Raw AI Response: {response_text}")

            try:
                # Clean and parse JSON response
                clean_response = response_text.replace('```json', '').replace('```', '').strip()
                response_json = json.loads(clean_response)
            
            except Exception as parse_err:
                log('error', uid, f"JSON parsing failed: {parse_err}")
                return Response({"status": False, "message": "AI returned invalid response format", "state":"Error"}, status=200)

            category = response_json.get("Category")
            ai_message = response_json.get("Response")
            
            log('info', uid, f"Category: {category}")
            log('info', uid, f"AI Message: {ai_message}")

            if not category or not ai_message:
                return Response({"status": False, "message": "AI response: Missing required fields", "state":"Error"}, status=200)

            # Step 5: Handle known categories
            if category == "Requested_Providers_List":
                start = time.time()
                status, result = BusinessLogic.getProviderNamesAndCode(practice_Code)
                end = time.time()
                print(f"[DEBUG] Execution time of getProviderNamesAndCode: {end - start} seconds")
                
                if status:
                    result['ProviderName'] = result['ProviderName'].str.strip()    # removing whitespaces
                    formatted_providers = format_providers(result)
                    formatted_providers = to_custom_format(formatted_providers)
                    
                    conversation_text = str({"user_query": user_Msg, "AI_response": ai_message, "Tool_message": formatted_providers})
                    
                    start = time.time()
                    BusinessLogic.dump_conversation_history(Session_ID, patient_Code, practice_Code, provider_Code, category, conversation_text=conversation_text)
                    end = time.time()
                    print(f"[DEBUG] Execution time of dump_conversation_history: {end - start} seconds")

                    return Response({"status": True, "state": category, "current_state": STATUS.REQUESTED_PROVIDERS_LIST.value, "message": ai_message, "session_id": Session_ID, "data": formatted_providers}, status=200)

                else:
                    return Response({"status": False, "state": "Error", "current_state": STATUS.ERROR.value, "message": f"No providers found in practice."}, status=200)


            elif category == "Book_With_Last_Provider":
                # Get yesterday's date
                # date = datetime.now().date() - timedelta(days=1)
                # startDate = date
                # endDate = date + timedelta(days=0)

                # # Convert to 'MM/DD/YYYY' format
                # date = date.strftime('%m/%d/%Y')
                # startDate = startDate.strftime('%m/%d/%Y')
                # endDate = endDate.strftime('%m/%d/%Y')
                appointment_date = datetime.now().date().strftime('%m/%d/%Y')
                
                # get last provider data from payload
                provider_name, provider_code, appointment_reason_id, appointment_location_id, location_address, appointment_date_time = extract_appointment_details(previous_appointment)
                print(provider_name)

                start = time.time()
                slots_response = get_available_time_slots(uid, provider_code, appointment_location_id, practice_Code, appointment_reason_id, appointment_date, appointment_date, appointment_date, patient_Code, isTelehealth, isFirstAvailable=True)
                end = time.time()
                print(f"[DEBUG] Execution time of get_available_time_slots API: {end - start} seconds")

                # print(f"Slots Response:\n{slots_response}")
                slots = slots_response.get("data", {}).get("appointmentSlots", [])
                filtered_slots = [
                    {
                        "availableDate": slot.get("availableDate"),
                        "availableSlot": slot.get("availableSlot"),
                    }
                    for slot in slots
                ]

                print(slots)
                print(filtered_slots)

                slots_formatted_data = to_custom_format(filtered_slots, key_col="availableDate", value_col="availableSlot")
                
                if slots_response:
                    conversation_text = str({"user_query": user_Msg, "AI_response": ai_message, "Tool_message": filtered_slots})
                    start = time.time()
                    BusinessLogic.dump_conversation_history(Session_ID, patient_Code, practice_Code, provider_Code, category, conversation_text=conversation_text)
                    end = time.time()
                    print(f"[DEBUG] Execution time of dump_conversation_history: {end - start} seconds")

                    return Response({"status" : True, "state": category, "current_state": STATUS.BOOK_WITH_LAST_PROVIDER.value, "isFirstAvailable": True, "message": ai_message, "session_id": Session_ID, "data": slots_formatted_data}, status=200)

                else:
                    conversation_text = str({"user_query": user_Msg, "AI_response": ai_message, "Tool_message": slots_formatted_data.get("appointmentSlots")})
                    start = time.time()
                    BusinessLogic.dump_conversation_history(Session_ID, patient_Code, practice_Code, provider_Code, category, conversation_text=conversation_text)
                    end = time.time()
                    print(f"[DEBUG] Execution time of dump_conversation_history: {end - start} seconds")

                    return Response({"status": False, "state" : "Error", "current_state": STATUS.ERROR.value, "isFirstAvailable": None, "message": "No appointment slots are currently available for this provider."}, status=200)

            elif category == "Request_More_Slots":
                # Request_More_Slots incase of booking with new provider
                if provider_Code:
                    # Get yesterday's date
                    date = datetime.now().date() - timedelta(days=1)
                    startDate = date
                    endDate = date + timedelta(days=7)

                    # Convert to 'MM/DD/YYYY' format
                    date = date.strftime('%m/%d/%Y')
                    startDate = startDate.strftime('%m/%d/%Y')
                    endDate = endDate.strftime('%m/%d/%Y')

                    print(f"Original data:\n{conv_record}")

                    # Getting ReasonID
                    conv_record['REASON_ID'] = pd.to_numeric(conv_record['REASON_ID'], errors='coerce')

                    # Get last non-null REASON_ID or default
                    reasonID = str(int(conv_record['REASON_ID'].dropna().iloc[-1] if conv_record['REASON_ID'].notna().any() else DEFAULT_REASON_ID))
                    print(f"Reason ID: {reasonID}")

                    # get default provider location
                    start = time.time()
                    status, location_data = BusinessLogic.getDefaultProviderLocation(provider_Code)
                    end = time.time()
                    print(f"[DEBUG] Execution time of getDefaultProviderLocation: {end - start} seconds")

                    if not status:
                        conversation_text = str({"user_query": user_Msg, "AI_response": "Please choose any other provider", "Tool_message": "Default provider location is not available in database"})
                        start = time.time()
                        BusinessLogic.dump_conversation_history(Session_ID, patient_Code, practice_Code, provider_Code, category, conversation_text=conversation_text)
                        end = time.time()
                        print(f"[DEBUG] Execution time of dump_conversation_history: {end - start} seconds")
                        
                        log('error', uid, f"Failed to get default provider location for provider {provider_Code}")
                        return Response({"status": False, "message": "Failed to get default provider location", "state":"Error"}, status=200)

                    print(location_data)
                    location_Code = location_data["Location_Id"].iloc[0] if not location_data.empty else None
                    print(f"Location Code: {location_Code}")

                    if not all([provider_Code, location_Code, practice_Code, reasonID, startDate, endDate, date, patient_Code]):
                        print("One or more required values are missing.")
                        log('error', uid, "One or more required values are missing for appointments slots API.")
                        log('error', uid, f"Missing values: Provider Code: {provider_Code}, Location Code: {location_Code}, \
                            Practice Code: {practice_Code}, Reason ID: {reasonID}, Start Date: {startDate}, End Date: {endDate}, Date: {date}, Patient Code: {patient_Code}")
                        
                        raise ValueError(f"Session ID: {Session_ID}. One or more required values are missing for appointments slots API")

                    start = time.time()
                    slots_response = get_available_time_slots(uid, provider_Code, location_Code, practice_Code, reasonID, startDate, endDate, date, patient_Code, isTelehealth, isFirstAvailable=False)
                    end = time.time()
                    print(f"[DEBUG] Execution time of get_available_time_slots API: {end - start} seconds")

                    # print(f"Slots Response:\n{slots_response}")
                    slots = slots_response.get("data", {}).get("appointmentSlots", [])
                    filtered_slots = [
                        {
                            "availableDate": slot.get("availableDate"),
                            "availableSlot": slot.get("availableSlot"),
                        }
                        for slot in slots
                    ]

                    print(slots)
                    print(filtered_slots)

                    slots_formatted_data = to_custom_format(filtered_slots, key_col="availableDate", value_col="availableSlot")
                    
                    if slots_response:
                        conversation_text = str({"user_query": user_Msg, "AI_response": ai_message, "Tool_message": filtered_slots})
                        start = time.time()
                        BusinessLogic.dump_conversation_history(Session_ID, patient_Code, practice_Code, provider_Code, category, conversation_text=conversation_text)
                        end = time.time()
                        print(f"[DEBUG] Execution time of dump_conversation_history: {end - start} seconds")

                        return Response({"status" : True, "state": category, "current_state": STATUS.BOOK_WITH_LAST_PROVIDER.value, "isFirstAvailable": False, "message": ai_message, "session_id": Session_ID, "data": slots_formatted_data}, status=200)

                    else:
                        conversation_text = str({"user_query": user_Msg, "AI_response": ai_message, "Tool_message": slots_formatted_data.get("appointmentSlots")})
                        start = time.time()
                        BusinessLogic.dump_conversation_history(Session_ID, patient_Code, practice_Code, provider_Code, category, conversation_text=conversation_text)
                        end = time.time()
                        print(f"[DEBUG] Execution time of dump_conversation_history: {end - start} seconds")

                        return Response({"status": False, "state" : "Error", "current_state": STATUS.ERROR.value, "isFirstAvailable": None, "message": "No appointment slots are currently available for this provider."}, status=200)


                # Request_More_Slots incase of booking with new provider
                else:
                    # Get yesterday's date
                    date = datetime.now().date() - timedelta(days=1)
                    startDate = date
                    endDate = date + timedelta(days=7)

                    # Convert to 'MM/DD/YYYY' format
                    date = date.strftime('%m/%d/%Y')
                    startDate = startDate.strftime('%m/%d/%Y')
                    endDate = endDate.strftime('%m/%d/%Y')
                    
                    # get last provider data from payload
                    provider_name, provider_code, appointment_reason_id, appointment_location_id, location_address, appointment_date_time = extract_appointment_details(previous_appointment)
                    print(provider_name)

                    start = time.time()
                    slots_response = get_available_time_slots(uid, provider_code, appointment_location_id, practice_Code, appointment_reason_id, startDate, endDate, date, patient_Code, isTelehealth, isFirstAvailable=False)
                    end = time.time()
                    print(f"[DEBUG] Execution time of get_available_time_slots API: {end - start} seconds")

                    # print(f"Slots Response:\n{slots_response}")
                    slots = slots_response.get("data", {}).get("appointmentSlots", [])
                    filtered_slots = [
                        {
                            "availableDate": slot.get("availableDate"),
                            "availableSlot": slot.get("availableSlot"),
                        }
                        for slot in slots
                    ]

                    print(slots)
                    print(filtered_slots)

                    slots_formatted_data = to_custom_format(filtered_slots, key_col="availableDate", value_col="availableSlot")
                    
                    if slots_response:
                        conversation_text = str({"user_query": user_Msg, "AI_response": ai_message, "Tool_message": filtered_slots})
                        start = time.time()
                        BusinessLogic.dump_conversation_history(Session_ID, patient_Code, practice_Code, provider_Code, category, conversation_text=conversation_text)
                        end = time.time()
                        print(f"[DEBUG] Execution time of dump_conversation_history: {end - start} seconds")

                        return Response({"status" : True, "state": category, "current_state": STATUS.REQUEST_MORE_SLOTS.value, "isFirstAvailable": False, "message": ai_message, "session_id": Session_ID, "data": slots_formatted_data}, status=200)

                    else:
                        conversation_text = str({"user_query": user_Msg, "AI_response": ai_message, "Tool_message": slots_formatted_data.get("appointmentSlots")})
                        start = time.time()
                        BusinessLogic.dump_conversation_history(Session_ID, patient_Code, practice_Code, provider_Code, category, conversation_text=conversation_text)
                        end = time.time()
                        print(f"[DEBUG] Execution time of dump_conversation_history: {end - start} seconds")

                        return Response({"status": False, "state" : "Error", "current_state": STATUS.ERROR.value, "isFirstAvailable": None, "message": "No appointment slots are currently available for this provider."}, status=200)


            elif category == "Requested_Providers_Slots":
                # Get yesterday's date
                # date = datetime.now().date() - timedelta(days=1)
                # startDate = date
                # endDate = date + timedelta(days=7)

                # # Convert to 'MM/DD/YYYY' format
                # date = date.strftime('%m/%d/%Y')
                # startDate = startDate.strftime('%m/%d/%Y')
                # endDate = endDate.strftime('%m/%d/%Y')

                appointment_date = datetime.now().date().strftime('%m/%d/%Y')

                print(f"Original data:\n{conv_record}")

                # Getting ReasonID
                conv_record['REASON_ID'] = pd.to_numeric(conv_record['REASON_ID'], errors='coerce')

                # Get last non-null REASON_ID or default
                reasonID = str(int(conv_record['REASON_ID'].dropna().iloc[-1] if conv_record['REASON_ID'].notna().any() else DEFAULT_REASON_ID))
                print(f"Reason ID: {reasonID}")

                # get default provider location
                start = time.time()
                status, location_data = BusinessLogic.getDefaultProviderLocation(provider_Code)
                end = time.time()
                print(f"[DEBUG] Execution time of getDefaultProviderLocation: {end - start} seconds")

                if not status:
                    conversation_text = str({"user_query": user_Msg, "AI_response": "Please choose any other provider", "Tool_message": "Default provider location is not available in database"})
                    start = time.time()
                    BusinessLogic.dump_conversation_history(Session_ID, patient_Code, practice_Code, provider_Code, category, conversation_text=conversation_text)
                    end = time.time()
                    print(f"[DEBUG] Execution time of dump_conversation_history: {end - start} seconds")
                    
                    log('error', uid, f"Failed to get default provider location for provider {provider_Code}")
                    return Response({"status": False, "message": "Failed to get default provider location", "state":"Error", "current_state": STATUS.ERROR.value}, status=200)

                print(location_data)
                location_Code = location_data["Location_Id"].iloc[0] if not location_data.empty else None
                print(f"Location Code: {location_Code}")
                
                if not location_Code:
                    print("Location code is missing.")
                    log('error', uid, "Location code is missing for appointment slots API.")
                    
                    conversation_text = str({"user_query": user_Msg, "AI_response": "Provider Location is missing. You can choose any other provider", "Tool_message": "Provider location is not available in database"})
                    start = time.time()
                    BusinessLogic.dump_conversation_history(Session_ID, patient_Code, practice_Code, provider_Code, category, conversation_text=conversation_text)
                    end = time.time()
                    print(f"[DEBUG] Execution time of dump_conversation_history: {end - start} seconds")
                                        
                    return Response({"status": False, "message": "Provider Location is missing", "state": "Error",
                                     "current_state": STATUS.ERROR.value}, status=200)
                
                if not all([provider_Code, practice_Code, reasonID, appointment_date, patient_Code]):
                    print("One or more required values are missing.")
                    log('error', uid, "One or more required values are missing for appointments slots API.")
                    log('error', uid, f"Missing values: Provider Code: {provider_Code}, Location Code: {location_Code}, \
                         Practice Code: {practice_Code}, Reason ID: {reasonID}, Appointment Date: {appointment_date}, Patient Code: {patient_Code}")
                                     
                    conversation_text = str({"user_query": user_Msg, "AI_response": "Required data of provider is missing. You can choose any other provider", "Tool_message": "One or more required values are missing for appointments slots API."})
                    start = time.time()
                    BusinessLogic.dump_conversation_history(Session_ID, patient_Code, practice_Code, provider_Code, category, conversation_text=conversation_text)
                    end = time.time()
                    print(f"[DEBUG] Execution time of dump_conversation_history: {end - start} seconds")

                    return Response({"status": False, "message": f"Session ID: {Session_ID}. One or more required values are missing for appointments slots API", "state":"Error", "current_state": STATUS.ERROR.value}, status=200)

                start = time.time()
                slots_response = get_available_time_slots(uid, provider_Code, location_Code, practice_Code, reasonID, appointment_date, appointment_date, appointment_date, patient_Code, isTelehealth, isFirstAvailable=True)
                end = time.time()
                print(f"[DEBUG] Execution time of get_available_time_slots API: {end - start} seconds")

                # print(f"Slots Response:\n{slots_response}")
                slots = slots_response.get("data", {}).get("appointmentSlots", [])
                filtered_slots = [
                    {
                        "availableDate": slot.get("availableDate"),
                        "availableSlot": slot.get("availableSlot"),
                    }
                    for slot in slots
                ]

                print(slots)
                print(filtered_slots)

                slots_formatted_data = to_custom_format(filtered_slots, key_col="availableDate", value_col="availableSlot")
                
                if slots_response:
                    conversation_text = str({"user_query": user_Msg, "AI_response": ai_message, "Tool_message": filtered_slots})
                    start = time.time()
                    BusinessLogic.dump_conversation_history(Session_ID, patient_Code, practice_Code, provider_Code, category, conversation_text=conversation_text)
                    end = time.time()
                    print(f"[DEBUG] Execution time of dump_conversation_history: {end - start} seconds")

                    return Response({"status" : True, "state": category, "current_state": STATUS.REQUESTED_PROVIDERS_SLOTS.value, "isFirstAvailable": True, "message": ai_message, "session_id": Session_ID, "data": slots_formatted_data}, status=200)

                else:
                    conversation_text = str({"user_query": user_Msg, "AI_response": ai_message, "Tool_message": slots_formatted_data.get("appointmentSlots")})
                    start = time.time()
                    BusinessLogic.dump_conversation_history(Session_ID, patient_Code, practice_Code, provider_Code, category, conversation_text=conversation_text)
                    end = time.time()
                    print(f"[DEBUG] Execution time of dump_conversation_history: {end - start} seconds")

                    return Response({"status": False, "state" : "Error", "current_state": STATUS.ERROR.value, "isFirstAvailable": None, "message": "No appointment slots are currently available for this provider."}, status=200)

            elif category == "Provide_Chief_Complaint":
                start = time.time()
                status, result = BusinessLogic.getSpecialistsDetail(practice_Code)
                end = time.time()
                print(f"[DEBUG] Execution time of getSpecialistsDetail: {end - start} seconds")

                if status:
                    # Get appointment reason ID based on chief complaint
                    start = time.time()
                    _, appointment_reason_data = BusinessLogic.getAppointmentReasonID(practice_Code)
                    end = time.time()
                    print(f"[DEBUG] Execution time of getAppointmentReasonID: {end - start} seconds")

                    prompt = prmpt_obj.get_reason_Id_prompt(user_Msg, appointment_reason_data)
                    print(f"Prompt:\n{prompt}")
                    
                    start = time.time()
                    response = gr_obj.generate_response(uid, prompt)
                    end = time.time()
                    print(f"[DEBUG] Execution time of model in get_reason_Id_prompt: {end - start} seconds")

                    try:
                        # Clean and parse JSON response
                        clean_response = response.replace('```json', '').replace('```', '').strip()
                        response_json = json.loads(clean_response)
                
                    except Exception as parse_err:
                        log('error', uid, f"JSON parsing failed: {parse_err}")
                        return Response({"status": False, "message": "AI returned invalid response format", "state":"Error"}, status=200)

                    appointment_reason_id = response_json.get("Reason_Id")
                    appointment_reason_name = response_json.get("Reason_Name")
                    
                    log('info', uid, f"Appointment Reason ID: {appointment_reason_id}")
                    log('info', uid, f"Appointment Reason Name: {appointment_reason_name}")
                    
                    print(f"getSpecialistsDetail Result:\n{result}")
                    
                    specialists_list = result["Speciality"].unique().tolist()

                    prompt = prmpt_obj.getMatchedSpecilistsPrompt(specialists_list, user_Msg)
                    print(f"getMatchedSpecilistsPrompt prompt:\n{prompt}")
                    
                    start = time.time()
                    response = gr_obj.generate_response(uid, prompt, model_name="gemini-2.0-flash-001")
                    end = time.time()
                    print(f"[DEBUG] Execution time of model in getRecommendationPrompt: {end - start} seconds")

                    try:
                        response = response.replace('```json', '').replace('```', '')
                        response = json.loads(response)
                    
                    except Exception as parse_err:
                        log('error', uid, f"JSON parsing failed: {parse_err}")
                        return Response({"status": False, "message": "AI returned invalid response format", "state":"Error"}, status=200)

                    specialists = response.get("Specialist")
                    
                    result = result[result['Speciality'].isin(specialists)]
                                        
                    prompt = prmpt_obj.getRecommendationPrompt(result, user_Msg)
                    print(f"Speciality matching prompt:\n{prompt}")

                    start = time.time()
                    response = gr_obj.generate_response(uid, prompt, model_name="gemini-2.0-flash-001")
                    end = time.time()
                    print(f"[DEBUG] Execution time of model in getRecommendationPrompt: {end - start} seconds")

                    try:
                        response = response.replace('```json', '').replace('```', '')
                        response = json.loads(response)

                    except Exception as parse_err:
                        log('error', uid, f"JSON parsing failed: {parse_err}")
                        return Response({"status": False, "message": "AI returned invalid response format", "state":"Error"}, status=200)

                    log('info',uid, f"All Recommended Specialists: {response}")

                    provider_codes = response.get("Provider_Codes")
                    provider_codes_formatted = to_custom_format(provider_codes, key_col="Provider_Code", value_col="Provider_Name")
                    
                    if not provider_codes:
                        return Response({"status": False, "data": provider_codes_formatted,
                                          "message": "We're sorry, we couldn't find any providers available who specialize in addressing your specific health concern at this time.", "state":"Error"},
                                            status=200)

                    conversation_text = str({"user_query": user_Msg, "AI_response": ai_message, "Tool_message": provider_codes})
                    
                    start = time.time()
                    BusinessLogic.dump_conversation_history(Session_ID, patient_Code, practice_Code, provider_Code, category, reason_id=appointment_reason_id, reason_name=appointment_reason_name, chief_complaint=user_Msg, conversation_text=conversation_text)
                    end = time.time()
                    print(f"[DEBUG] Execution time of dump_conversation_history: {end - start} seconds")

                    # If we have provider codes, we can proceed
                    return Response({"status": True, "state": category, "current_state": STATUS.PROVIDE_CHIEF_COMPLAINT.value, "message": ai_message, "session_id": Session_ID, "data": provider_codes_formatted}, status=200)

                else:
                    return Response({"status": False, "state" : "Error", "current_state": STATUS.ERROR.value, "message": f"No provider found against your reason of visit."}, status=200)

            elif category == "Choosed_Provider_Available_Slots":
                print(f"Conversation Data: {conv_record}")
                sorted_conv = conv_record.sort_values(by='CONVERSATION_ID', ascending=False)

                top_category = sorted_conv.iloc[0]['CATEGORY']
                second_top_category = sorted_conv.iloc[1]['CATEGORY'] if len(sorted_conv) > 1 else None

                has_book_with_last_provider = "Book_With_Last_Provider" in sorted_conv['CATEGORY'].values
                
                if has_book_with_last_provider:
                    provider_name, provider_code, appointment_reason_id, appointment_location_id, location_address, appointment_date_time = extract_appointment_details(previous_appointment)

                    if not all([practice_Code, patient_Code, provider_code, appointment_location_id, appointment_reason_id, app_date, time_From]):
                        print("One or more required values are missing for appointment creation API")
                        log('error', uid, "One or more required values are missing for appointments slots API.")
                        log('error', uid, f"Missing values: Provider Code: {provider_Code}, Location Code: {appointment_location_id}, \
                            Practice Code: {practice_Code}, Reason ID: {appointment_reason_id}, App Date: {app_date}, Time From: {time_From}")
                        
                        raise ValueError(f"Session ID: {Session_ID}. One or more required values are missing for appointment creation API")

                    start = time.time()
                    appointment_response = book_appointment(uid, practice_Code, patient_Code, provider_code, appointment_location_id, app_date, time_From, appointment_id, app_reason_id=appointment_reason_id)
                    end = time.time()
                    print(f"[DEBUG] Execution time of book_appointment API: {end - start} seconds")

                    if appointment_response.get("message").upper() == "SUCCESS":
                        log('info' ,uid, f"isAppointmentInserted: { appointment_response['data'].get('isAppointmentInserted') }")
                        log('info' ,uid, f"finalMessage: { appointment_response['data'].get('finalMessage') }")
                        
                        appointment_msg = appointment_response['data'].get('finalMessage')

                        # when appointment is successful
                        if appointment_response['data'].get('isAppointmentInserted') == "True":
                            conversation_text = str({"user_query": user_Msg, "AI_response": appointment_msg})
                            start = time.time()
                            BusinessLogic.dump_conversation_history(Session_ID, patient_Code, practice_Code, provider_Code, category, conversation_text=conversation_text)
                            end = time.time()
                            print(f"[DEBUG] Execution time of dump_conversation_history: {end - start} seconds")

                            return Response({"status" : True, "state": category, "current_state": STATUS.APPOINTMENT_SCHEDULED.value, "session_id": Session_ID, "message": appointment_msg, "appointmentResponse": appointment_response, "data": None}, status=200)

                        else:
                            conversation_text = str({"user_query": user_Msg, "AI_response": "Please choose some other slot or some other provider", "Tool_message": appointment_msg})
                            start = time.time()
                            BusinessLogic.dump_conversation_history(Session_ID, patient_Code, practice_Code, provider_Code, category, conversation_text=conversation_text)
                            end = time.time()
                            print(f"[DEBUG] Execution time of dump_conversation_history: {end - start} seconds")
                            return Response({"status" : False, "state": "Error", "current_state": STATUS.APPOINTMENT_NOT_SCHEDULED.value, "session_id": Session_ID, "message": appointment_msg, "appointmentResponse": appointment_response, "data": None}, status=200)
                    else:
                        log('error', uid, f"Error while calling Appointment creation API: {appointment_response}")
                        return Response({"status": False, "message": "Error while calling Appointment creation API", "state": "Error", "current_state": STATUS.APPOINTMENT_NOT_SCHEDULED.value, "appointmentResponse": appointment_response}, status=200)

                    
                # Get Provider Code
                # provider_code = conv_record["PROVIDER_CODE"].iloc[0] if not conv_record.empty else provider_Code
                start = time.time()                
                status, available_locations = BusinessLogic.getDefaultProviderLocation(provider_Code)
                end = time.time()
                print(f"[DEBUG] Execution time of getDefaultProviderLocation: {end - start} seconds")

                print(available_locations)
                
                if status:                    
                    location_dict = available_locations.to_dict(orient='records')
                    print(f"Provider's default location code: {location_dict}")

                else:
                    conversation_text = str({"user_query": user_Msg, "AI_response": f"Please choose some other provider", "Tool_message": f"Provider {provider_Code} does not have a default location code."})
                    start = time.time()
                    BusinessLogic.dump_conversation_history(Session_ID, patient_Code, practice_Code, provider_Code, category, conversation_text=conversation_text)
                    end = time.time()
                    print(f"[DEBUG] Execution time of dump_conversation_history: {end - start} seconds")

                    log('error', uid, f"Provider {provider_Code} does not have a default location code.")
                    return Response({"status": False, "message": f"Provider {provider_Code} does not have a default location code.", "state":"Error"}, status=200)

                # Format location codes
                location_codes_formatted = to_custom_format(location_dict, key_col="Location_Id", value_col="Location_Name")
                
                # Storing selected time slot in DB
                conversation_text = str({"user_query": user_Msg, "AI_response": ai_message, "Tool_message": location_dict})
                
                start = time.time()
                BusinessLogic.dump_conversation_history(Session_ID, patient_Code, practice_Code, provider_Code, category, selected_time_slot = user_Msg, location_data = location_dict, conversation_text=conversation_text)
                end = time.time()
                print(f"[DEBUG] Execution time of dump_conversation_history: {end - start} seconds")

                return Response({"status": True, "state": category, "current_state": STATUS.CHOOSED_PREFERRED_LOCATION.value, "message": ai_message, "session_id": Session_ID, "data": location_codes_formatted}, status=200)

            elif category == "Choosed_Preferred_Location":
                # Get all required data
                # Extracting values safely
                practice_code = get_last_valid_int_value(conv_record, 'PRACTICE_CODE')
                patient_Account = get_last_valid_int_value(conv_record, 'PATIENT_CODE')
                provider_Code = get_last_valid_int_value(conv_record, 'PROVIDER_CODE')
                reasonID = get_last_valid_int_value(conv_record, 'REASON_ID', default=DEFAULT_REASON_ID)
                location_Code = location_Code
                

                if not all([practice_code, patient_Account, provider_Code, location_Code, reasonID, app_date, time_From]):
                    print("One or more required values are missing for appointment creation API")
                    log('error', uid, "One or more required values are missing for appointments slots API.")
                    log('error', uid, f"Missing values: Provider Code: {provider_Code}, Location Code: {location_Code}, \
                         Practice Code: {practice_code}, Reason ID: {reasonID}, App Date: {app_date}, Time From: {time_From}")
                    
                    raise ValueError(f"Session ID: {Session_ID}. One or more required values are missing for appointment creation API")

                start = time.time()
                appointment_response = book_appointment(uid, practice_code, patient_Account, provider_Code, location_Code, app_date, time_From, appointment_id, app_reason_id=reasonID)
                end = time.time()
                print(f"[DEBUG] Execution time of book_appointment API: {end - start} seconds")

                if appointment_response.get("message").upper() == "SUCCESS":
                    log('info' ,uid, f"isAppointmentInserted: { appointment_response['data'].get('isAppointmentInserted') }")
                    log('info' ,uid, f"finalMessage: { appointment_response['data'].get('finalMessage') }")
                    
                    appointment_msg = appointment_response['data'].get('finalMessage')

                    # when appointment is successful
                    if appointment_response['data'].get('isAppointmentInserted') == "True":
                        conversation_text = str({"user_query": user_Msg, "AI_response": appointment_msg})
                        start = time.time()
                        BusinessLogic.dump_conversation_history(Session_ID, patient_Code, practice_Code, provider_Code, category, conversation_text=conversation_text)
                        end = time.time()
                        print(f"[DEBUG] Execution time of dump_conversation_history: {end - start} seconds")

                        return Response({"status" : True, "state": category, "current_state": STATUS.APPOINTMENT_SCHEDULED.value, "session_id": Session_ID, "message": appointment_msg, "appointmentResponse": appointment_response, "data": None}, status=200)

                    else:
                        conversation_text = str({"user_query": user_Msg, "AI_response": "Please choose some other slots", "Tool_message": appointment_msg})
                        start = time.time()
                        BusinessLogic.dump_conversation_history(Session_ID, patient_Code, practice_Code, provider_Code, category, conversation_text=conversation_text)
                        end = time.time()
                        print(f"[DEBUG] Execution time of dump_conversation_history: {end - start} seconds")
                        return Response({"status" : False, "state": category, "current_state": STATUS.APPOINTMENT_NOT_SCHEDULED.value, "session_id": Session_ID, "message": appointment_msg, "appointmentResponse": appointment_response, "data": None}, status=200)
                else:
                    log('error', uid, f"Error while calling Appointment creation API: {appointment_response}")
                    return Response({"status": False, "message": "Failed to book your appointment.", "state":"Error", "appointmentResponse": appointment_response}, status=200)
                
            elif category in ["Friendly_Note", "Appointment_Scheduling_Request", "General_Query", "Request_More_Information", "Unclear_Message"]:
                # Save the conversation and respond
                conversation_text = str({"user_query": user_Msg, "AI_response": ai_message})
                
                start = time.time()
                BusinessLogic.dump_conversation_history(Session_ID, patient_Code, practice_Code, provider_Code, category, conversation_text=conversation_text)
                end = time.time()
                print(f"[DEBUG] Execution time of dump_conversation_history: {end - start} seconds")

                return Response({"status": True, "state": category, "current_state": STATUS.GENERAL_QUERY.value, "message": ai_message, "session_id": Session_ID}, status=200)
            
            else:
                print(f"Unhandled category from AI: {category}")
                
                conversation_text = str({"user_query": user_Msg, "AI_response": ai_message})
                start = time.time()
                BusinessLogic.dump_conversation_history(Session_ID, patient_Code, practice_Code, provider_Code, category, conversation_text=conversation_text)
                end = time.time()
                print(f"[DEBUG] Execution time of dump_conversation_history: {end - start} seconds")

                return Response({"status":True, "state": category, "current_state": STATUS.GENERAL_QUERY.value, "message": ai_message, "session_id": Session_ID}, status=200)

            # Step 6: Handle unknown category
            # return Response({"status": "Failure", "message": f"Unhandled category from AI: {category}", "Session_ID": Session_ID}, status=500)

        except Exception as e:
            traceback.print_exc()
            log('error', uid, str(e))
            return Response({"status": False, "state": "Error", "message": str(e)}, status=200)



def format_providers(df: pd.DataFrame) -> list:
    formatted_list = [
        {
            "key": str(row["ProviderCode"]),
            "value": f"{row['ProviderPrefix']} {row['ProviderName']}"
        }
        for _, row in df.iterrows()
    ]
    return formatted_list



def to_custom_format(data, key_col=None, value_col=None):
    result = {
        "objectArray": None,
        "text": None,
        "stringArray": None
    }

    if isinstance(data, dict):
        # Convert dictionary to [{"key": ..., "value": ...}]
        result["objectArray"] = [{"key": str(k), "value": str(v)} for k, v in data.items()]

    elif isinstance(data, list):
        if all(isinstance(item, dict) for item in data):
            if key_col and value_col:
                # Convert list of dicts using specific column names
                result["objectArray"] = [
                    {"key": str(item.get(key_col, '')), "value": str(item.get(value_col, ''))}
                    for item in data
                ]
            else:
                # Return original list of dicts
                result["objectArray"] = data
        else:
            # Handle list of strings or other types
            result["stringArray"] = [str(item) for item in data]

    elif isinstance(data, str):
        result["text"] = data

    return result




def book_appointment(uid, practice_code, patient_Account, provider_Code, location_Code, app_date, time_From, appointment_id, *, app_reason_id=None):
    # API URL
    # url_test = "https://qa-webservices.mtbc.com/SmartSchedulingAPI/api/Appointment/AddAppointment"
    # url_pre_live = "https://uat-webservices.mtbc.com/SmartSchedulingAPI/api/Appointment/AddAppointment"
    url_live = "https://mhealth.mtbc.com/SmartSchedulingAPI/api/Appointment/AddAppointment"

    headers = {
        "accept": "*/*",
        "api_Key": "652*3121119876543210*2*1AHS*eulaV4@tt*esarhP4@tt*==AhVRnOMTXSpenbctUjp+Ar",
        "Content-Type": "application/json-patch+json"
    }

    # Payload
    data = {
        "practice_code": f"{practice_code}",
        "patient_Account": f"{patient_Account}",
        "provider_Code": f"{provider_Code}",
        "location_Code": f"{location_Code}",
        "app_date": f"{app_date}",
        "time_From": f"{time_From}",
        "appointment_ID" : f"{appointment_id}",
        "appReasonId": f"{app_reason_id}"
    }

    try:
        print("Payload being sent:\n", json.dumps(data, indent=2))

        response = requests.post(url_live, json=data, headers=headers)
        
        # Check if the response status is OK (200-299)
        response.raise_for_status()
        
        # Print Success Response
        print(response.json())
        return response.json()

    except requests.exceptions.RequestException as e:
        # Print error message
        log('info',uid, f"Appointment API request failed: {e}")
        print(f"Appointment API request failed: {e}")
    

def get_available_time_slots(uid, providerCode, locationCode, practiceCode, reasonID, startDate, endDate, date, patientAccount, isTelehealth: bool = False, patientTimeZone="+0500", isFirstAvailable: bool = False):
    # url_test = "https://qa-webservices.mtbc.com/breezeCheckinAPI/api/TalkCheckinPhaseTwo/GettimeSlotsBreezeDateRange"
    url_live = "https://mhealth.mtbc.com/breezecheckinapi/api/TalkCheckinPhaseTwo/GettimeSlotsBreezeDateRange"

    headers = {
        "accept": "*/*",
        "Content-Type": "application/json-patch+json",
        "api_Key": "652*3121119876543210*2*1AHS*eulaV4@tt*esarhP4@tt*==AhVRnOMTXSpenbctUjp+Ar"
    }

    payload = {
        "providerCode": str(providerCode),
        "locationCode": str(locationCode),
        "practiceCode": str(practiceCode),
        "patientAccount": patientAccount, 
        "reasonID": str(reasonID),
        "patientTimeZone": patientTimeZone,
        "isFirstAvailable": isFirstAvailable,
        "startDate": startDate,  # Format: "MM/DD/YYYY"
        "endDate": endDate,
        "date": date,
        "isTelehealth": isTelehealth
    }

    try:
        # Log payload to verify boolean values
        print("Payload being sent:\n", json.dumps(payload, indent=2))

        response = requests.post(url_live, json=payload, headers=headers)
        response.raise_for_status()
        # print(response.json())
        return response.json()

    except requests.exceptions.RequestException as e:
        log('info', uid, f"Get time slots API request failed: {e}")
        print(f"Get time slots API request failed: {e}")
        raise ValueError(f"Get time slots API request failed: {e}")


def get_last_valid_int_value(df, column, default=None):
    """
    Safely extracts the last non-null, valid integer value from a DataFrame column.
    Converts it to an int and then to str.
    Returns default if the column has no valid integer values.
    """
    # Convert column to numeric, coercing invalid values to NaN
    numeric_series = pd.to_numeric(df[column], errors='coerce')
    
    # Get the last non-null value from the numeric series
    val = numeric_series.dropna().iloc[-1] if numeric_series.notna().any() else default
    
    # If no valid value is found, return default
    if pd.isna(val) or val is None:
        return default
    
    # Convert to int and then to str
    return str(int(val))

def get_all_recommended_slots_as_string(df):
    output = []
    
    for _, row in df.iterrows():
        raw = row.get("future_rescheduling_response", "")        
        if not raw or raw == "None":
            continue
        
        try:            
            raw = raw.replace("```json", "").replace("```", "").strip()

            parsed = ast.literal_eval(raw) 
            slots = parsed.get("Recommended_Slots", {})            
            output.append(str(slots))
        except Exception as e:
            print(f"Failed to parse row: {raw}, error: {e}")
            continue

    return "\n\n".join(output)


def extract_appointment_details(previous_appointment):
    # Convert list of key-value pairs into a dictionary
    details = {item['key']: item['value'] for item in previous_appointment}
    
    # Extract individual variables
    provider_name = details.get("Provider_Name")
    provider_code = details.get("Provider_Code")
    appointment_reason_id = details.get("Appointment_ReasonID")
    appointment_location_id = details.get("Appointment_LocationID")
    location_address = details.get("Location_Address")
    appointment_date_time = details.get("Appointment_Date_Time")

    return provider_name, provider_code, appointment_reason_id, appointment_location_id, location_address, appointment_date_time



class SlotsDuration(APIView):
    def post(self, request):
        try:                
            uid = secrets.token_hex(4)
            if request.method != 'POST':
                log('error', uid, "Invalid Request")
                log('error', uid, 'Status Code: 400')
                return Response({"result": {}, "status": "Failure", "message": "Get method is not allowed"}, status=400)
            
            log_request('info', uid, request)

            previous_uid = request.data.get('previous_uid')
            patient_account = request.data.get('patient_account')
            chief_complaint = request.data.get('chief_complaint')
            visit_type = request.data.get('visit_type')

            status, result = BusinessLogic.getLastSessionHistory(previous_uid, patient_account)
        
            if status:
                raw_response = result['response']
                print(raw_response)
                print(type(raw_response))
            
                # Ensure raw_response is a string
                if isinstance(raw_response, pd.Series):
                    raw_response = raw_response.iloc[0]  # Get the first element of the Series
                    print(type(raw_response))

                if not isinstance(raw_response, str):
                    raw_response = str(raw_response)  # Convert non-string values to string

                print(type(raw_response))
              
                # Extract text content using regex              
                pattern = r"```json\\n(.*?)\\n```"                
                match = re.search(pattern, raw_response, re.DOTALL)
                
                if match:
                    json_string = match.group(1)  # Extract JSON string part
                    json_string = json_string.replace('\\n', '').replace('\\"', '"')  # Clean up escape characters

                    try:
                        parsed_json = json.loads(json_string)  # Convert to proper JSON object
                        print(parsed_json)  # Print the cleaned JSON response
                
                    except json.JSONDecodeError as e:
                        traceback.print_exc()
                        log('error', uid, str(e))
                        print("Error decoding JSON:", e)
                else:
                    print("No valid JSON found in response")

                slots = parsed_json.get("Recommended_Slots")
                prompt = prmpt_obj.slot_duration_prompt(slots, visit_type, chief_complaint)
                response = gr_obj.generate_response(uid, prompt)            
                response = response.replace('```json', '').replace('```', '')
                final_response = json.loads(response)
        
        except Exception as e:            
            traceback.print_exc()
            log('error', uid, str(e))
            return Response({"status": "Failure", "message": str(e)}, status=400)
