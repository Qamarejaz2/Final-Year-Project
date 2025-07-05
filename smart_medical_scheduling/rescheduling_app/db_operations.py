import os, re
from dotenv import load_dotenv
import pymssql
import pandas as pd
import json
from datetime import datetime
from collections import defaultdict
from rescheduling_app.utils.logging_utils import log, log_request
from concurrent.futures import ThreadPoolExecutor, as_completed
from rescheduling_app.utils.json_utils import escape_sql_string

import warnings
warnings.filterwarnings('ignore')

load_dotenv()
    
DB_HOST = os.getenv("LIVE_DB_HOST")
DB_USER = os.getenv("LIVE_DB_USER")
DB_PASSWORD = os.getenv("LIVE_DB_PWD")
DB_NAME = os.getenv("LIVE_DB_NAME") 

TEST_DB_HOST = os.getenv("TEST_DB_HOST")
TEST_DB_USER = os.getenv("TEST_DB_USER")
TEST_DB_PWD = os.getenv("TEST_DB_PWD")
TEST_DB_NAME = os.getenv("TEST_DB_NAME")

AI_DB_HOST = os.getenv("AI_DB_HOST")
AI_DB_USER = os.getenv("AI_DB_USER")
AI_DB_PWD = os.getenv("AI_DB_PWD")
AI_DB_NAME = os.getenv("AI_DB_NAME")


class DBConnection:
    @staticmethod
    def live_db():
        try:
            conn = pymssql.connect(
                user = DB_USER,
                password = DB_PASSWORD,
                host = DB_HOST,
                database = DB_NAME,
                autocommit = True,
            )
            cursor = conn.cursor()
            print(cursor, conn)
            print("Success")
            return conn, cursor
        
        except Exception as exp:
            print("Error in live_db():", exp)
            return None, None
    
    @staticmethod
    def logging_db():
        try:
            conn = pymssql.connect(
                user = AI_DB_USER,
                password = AI_DB_PWD,
                host = AI_DB_HOST,
                database = AI_DB_NAME,
                autocommit = True,
            )
            cursor = conn.cursor()
            print(cursor, conn)
            print("Success")
            return conn, cursor
        
        except Exception as exp:
            print("Error in logging_db():", exp)
            return None, None
    
    @staticmethod
    def test_db():
        try:
            conn = pymssql.connect(
                user = TEST_DB_USER,
                password = TEST_DB_PWD,
                host = TEST_DB_HOST,
                database = TEST_DB_NAME,
                autocommit = True,
            )
            cursor = conn.cursor()
            print(cursor, conn)
            print("Success")
            return conn, cursor
        
        except Exception as exp:
            print("Error in test_db():", exp)
            return None, None

    @staticmethod
    def db_disconnect(conn, cursor):
        try:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
        except Exception as exp:
            print("Error in db_disconnect:", exp)


class BusinessLogic:   
    @staticmethod
    def execute_query(query, params=None, empty_df=None, fetch_results=True):
        conn, cursor = None, None
        df = empty_df if empty_df is not None else pd.DataFrame()  
        result = None  # Placeholder for the final return value

        try:
            conn, cursor = DBConnection.live_db()
            
            if fetch_results:
                # SELECT queries
                df = pd.read_sql(query, conn, params=params)
                result = df
            else:
                # DML queries
                cursor.execute(query, params)
                conn.commit()
                result = True  # Indicate success for DML queries
        except Exception as exe:
            print(f"Error executing query: {exe}")
            if fetch_results:
                # Return an empty DataFrame for failed SELECT queries
                result = empty_df
            else:                
                # Return False for failed DML queries
                result = False
        finally:
            if conn and cursor:
                DBConnection.db_disconnect(conn, cursor)
        
        return result  # Ensure the connection is closed before returning


    @staticmethod
    def execute_query_for_logger(query, params=None, empty_df=None, fetch_results=True):
        conn, cursor = None, None
        df = empty_df if empty_df is not None else pd.DataFrame()  
        result = None  # Placeholder for the final return value

        try:
            conn, cursor = DBConnection.logging_db()
            
            if fetch_results:
                # SELECT queries
                df = pd.read_sql(query, conn, params=params)
                result = df
            else:
                # DML queries
                cursor.execute(query, params)
                conn.commit()
                result = True  # Indicate success for DML queries
        except Exception as exe:
            print(f"Error executing query: {exe}")
            if fetch_results:
                # Return an empty DataFrame for failed SELECT queries
                result = empty_df
            else:                
                # Return False for failed DML queries
                result = False
        finally:
            if conn and cursor:
                DBConnection.db_disconnect(conn, cursor)
        
        return result  # Ensure the connection is closed before returning
    
    @staticmethod
    def execute_query_in_test(query, params=None, empty_df=None, fetch_results=True):
        conn, cursor = None, None
        df = empty_df if empty_df is not None else pd.DataFrame()  
        result = None  # Placeholder for the final return value

        try:
            conn, cursor = DBConnection.test_db()
            
            if fetch_results:
                # SELECT queries
                df = pd.read_sql(query, conn, params=params)
                result = df
            else:
                # DML queries
                cursor.execute(query, params=params)
                conn.commit()
                result = True  # Indicate success for DML queries
        except Exception as exe:
            print(f"Error executing query: {exe}")
            if fetch_results:
                # Return an empty DataFrame for failed SELECT queries
                result = empty_df
            else:                
                # Return False for failed DML queries
                result = False
        finally:
            if conn and cursor:
                DBConnection.db_disconnect(conn, cursor)
        
        return result  # Ensure the connection is closed before returning
    


    @staticmethod
    def getSpecialistsDetail(practice_code):
        df_empty = pd.DataFrame(columns=["Speciality", "Provider_Code","Provid_FName","Provid_LName"])

        query = """
                SELECT
                    TEX.Description AS Speciality,
                    pro.provider_code AS Provider_Code,
                    pro.Provid_FName,
                    pro.Provid_LName
                FROM
                    Providers pro
                JOIN
                    Taxonomy_Codes TEX
                    ON pro.Taxonomy_Code = TEX.Taxonomy_Codes
                WHERE
                    practice_code = %s
                    AND ISNULL(pro.DELETED, 0) = 0
                    AND ISNULL(TEX.DELETED, 0) = 0
                    AND ISNULL(pro.IS_ACTIVE, 0) = 1
                    -- AND pro.Created_By LIKE '%test%'
                    -- AND pro.Provid_FName LIKE '%WAYNE%'
                OPTION (MAXDOP 1);"""

        params = (practice_code,)  # Tuple with a single element
        result_df = BusinessLogic.execute_query(query, params=params, empty_df=df_empty)

        if result_df.empty:
            return [False, f"No Provider found in Practice {practice_code}"]

        # # Ensure the Provider_Code column is converted to strings
        # result_df["Provider_Code"] = result_df["Provider_Code"].astype(str)

        # # Group the providers by speciality and aggregate them
        # grouped = result_df.groupby("Speciality")["Provider_Code"].apply(lambda x: ", ".join(x)).reset_index()
        # grouped.columns = ["Speciality", "Provider_Codes"]
                
        # return [True, grouped]
        return [True, result_df]

    
    @staticmethod
    def getPreferredProvider(patient_account, provider_codes):
        df_result = pd.DataFrame(columns=['Provider_Code', 'Appointments_Count'])

        def fetch_provider_appointments(code):            
            query = f"""
                DECLARE @PATIENT_ACCOUNT BIGINT = {patient_account};
                DECLARE @PROVIDER_CODE BIGINT = {code};
                SELECT Provider_Code, COUNT(*) AS Appointments_Count FROM Appointments a
                WHERE Patient_Account = @PATIENT_ACCOUNT
                AND Provider_Code = @PROVIDER_CODE
                AND Created_By NOT LIKE '%test%'
                AND ISNULL(deleted, 0) = 0
                GROUP BY Provider_Code
            """
            # Execute the query and return the result
            df_empty = pd.DataFrame(columns=['Provider_Code', 'Appointments_Count'])
            return BusinessLogic.execute_query(query, df_empty)

        # Use ThreadPoolExecutor for parallel execution
        with ThreadPoolExecutor() as executor:
            future_to_code = {executor.submit(fetch_provider_appointments, code): code for code in provider_codes}
            
            for future in as_completed(future_to_code):
                code = future_to_code[future]
                try:
                    result_df = future.result()
                    if not result_df.empty:
                        df_result = pd.concat([df_result, result_df], ignore_index=True)
                except Exception as e:
                    print('error', f"Error fetching appointments for provider {code}: {e}")

        # Sort results by Appointments_Count in descending order
        df_result = df_result.sort_values(by='Appointments_Count', ascending=False)

        return df_result

    @staticmethod
    def getPatientAppointmentHistory(patient_account):
        df_empty = pd.DataFrame(columns=[
            "Patient_Account", "Appointment_Id", "Provider_Code", "Appointment_Date_Time",
            "Time_From", "Created_By", "WEEKDAY", "Reason_Description",
            "Appointment_Status_Id", "Appointment_Status_Description", "Practice_Code",
            "Provid_FName", "Provid_MName", "Provid_LName"
        ])

        try:
            query = """                
                SELECT TOP 100 apmts.Patient_Account, apmts.Appointment_Id, apmts.Provider_Code,
                    apmts.Appointment_Date_Time, apmts.Time_From, apmts.Created_By,
                    DATENAME(WEEKDAY, Appointment_Date_Time) AS WEEKDAY,
                    ar.Reason_Description, apps.Appointment_Status_Id,
                    apps.Appointment_Status_Description, p.Practice_Code,
                    p.Provid_FName, p.Provid_MName, p.Provid_LName
                FROM Appointments apmts
                LEFT JOIN Appointment_Reasons ar ON apmts.Reason_Id = ar.Reason_Id
                LEFT JOIN AF_TBL_APPOINTMENT_REASONS_CUSTOMIZED CAR ON CAR.REASONS_CUSTOMIZED_ID = ar.Reason_Id
                JOIN Providers p ON apmts.Provider_Code = p.Provider_Code
                JOIN Appointment_Status apps ON apmts.Appointment_Status_Id = apps.Appointment_Status_Id
                WHERE apmts.Patient_Account = %s
                AND ISNULL(apmts.DELETED, 0) = 0
                AND apps.Appointment_Status_Id = 6 
              --  AND apmts.Created_By NOT LIKE '%test%'
                ORDER BY apmts.Appointment_Date_Time DESC
            """
            
            params = (patient_account,)
            result_df = BusinessLogic.execute_query(query, params=params, empty_df=df_empty)
            if not result_df.empty:
                return [True, result_df]
            else:
                return [False, result_df]

        except ValueError as ve:
            print(f"Input Error: {ve}")
            return [False, f"Input Error: {ve}"]

        except ConnectionError as ce:            
            print(f"Database Connection Error: {ce}")
            return [False, "Database connection failed. Please try again later."]

        except Exception as e:            
            print(f"Unexpected Error: {str(e)}")
            return [False, f"An unexpected error occurred: {str(e)}"]

        finally:            
            print("Execution of getPatientAppointmentHistory completed.")


    @staticmethod
    def getProviderAvailability(provider_code):
        df_empty = pd.DataFrame(columns=[
            "PROVIDER_CODE", "PRACTICE_CODE", "LOCATION_CODE", "WEEK_DAY", "DAY_ON",
            "PROVIDER_DURATION", "PROVIDER_TIME_FROM", "PROVIDER_TIME_TO",
            "PROVIDER_BREAK_TIME_FROM", "PROVIDER_BREAK_TIME_TO", "Appointment_Id",
            "Patient_Account", "Appointment_Date", "APPOINTMENT_TIME_FROM",
            "Appointment_Units", "APPOINTMENT_DURATION", "APPOINTMENT_CREATED_BY"
        ])

        try:
            query = """
                -- Select working day time details with Appointments join
                WITH ProviderData AS (
                    SELECT   
                        ISNULL(A.PROVIDER_CODE, %s) AS PROVIDER_CODE,    
                        ISNULL(A.PRACTICE_CODE, (
                            SELECT TOP (1) PRACTICE_CODE    
                            FROM dbo.PROVIDERS    
                            WHERE PROVIDER_CODE = %s    
                            ORDER BY PROVIDER_CODE
                        )) AS PRACTICE_CODE,    
                        ISNULL(A.LOCATION_CODE, 0) AS LOCATION_CODE,    
                        CASE P.Weekday_Id
                            WHEN 1 THEN 'MONDAY'
                            WHEN 2 THEN 'TUESDAY'
                            WHEN 3 THEN 'WEDNESDAY'
                            WHEN 4 THEN 'THURSDAY'
                            WHEN 5 THEN 'FRIDAY'
                            WHEN 6 THEN 'SATURDAY'
                            WHEN 7 THEN 'SUNDAY'
                        END AS WEEK_DAY,
                        CASE ISNULL(A.DAY_ON, P.DAY_ON)
                            WHEN 1 THEN 'ON' ELSE 'OFF'
                        END AS DAY_ON,
                        ISNULL(A.DURATION, P.DURATION) AS PROVIDER_DURATION,    
                        ISNULL(A.TIME_FROM_NEW, P.TIME_FROM_NEW) AS PROVIDER_TIME_FROM,    
                        ISNULL(A.TIME_TO_NEW, P.TIME_TO_NEW)  AS PROVIDER_TIME_TO,

                        ISNULL(NULLIF(A.BREAK_TIME_FROM_NEW, ''), 
                            (SELECT TOP 1 BREAK_TIME_FROM_NEW 
                                FROM AF_TBL_PROVIDER_WORKING_DAYS_TIME 
                                WHERE PROVIDER_CODE = %s 
                                AND NULLIF(BREAK_TIME_FROM_NEW, '') IS NOT NULL 
                                ORDER BY MODIFIED_DATE DESC)) 
                        AS PROVIDER_BREAK_TIME_FROM,

                        ISNULL(NULLIF(A.BREAK_TIME_TO_NEW, ''), 
                            (SELECT TOP 1 BREAK_TIME_TO_NEW 
                                FROM AF_TBL_PROVIDER_WORKING_DAYS_TIME 
                                WHERE PROVIDER_CODE = %s 
                                AND NULLIF(BREAK_TIME_TO_NEW, '') IS NOT NULL 
                                ORDER BY MODIFIED_DATE DESC)) 
                        AS PROVIDER_BREAK_TIME_TO,

                        ISNULL(AP.Appointment_Id, 0) AS Appointment_Id,
                        ISNULL(AP.Patient_Account, 0) AS Patient_Account,
                        CAST(ISNULL(AP.Appointment_Date_Time, GETDATE()) AS DATE) AS Appointment_Date,
                        AP.Time_From AS APPOINTMENT_TIME_FROM,
                        ISNULL(AP.Appointment_Units, 1) AS Appointment_Units,
                        ISNULL(AP.Duration, 15) AS APPOINTMENT_DURATION,
                        ISNULL(AP.Created_By, 'AI') AS APPOINTMENT_CREATED_BY
                    FROM PROVIDER_WORKING_DAYS_TIME_DEFAULT P    
                    LEFT OUTER JOIN dbo.AF_TBL_PROVIDER_WORKING_DAYS_TIME A    
                        ON A.WEEKDAY_ID = P.WEEKDAY_ID    
                        AND A.PROVIDER_CODE = %s    
                        AND CONVERT(DATE, A.MODIFIED_DATE) = (    
                            SELECT MAX(CONVERT(DATE, MODIFIED_DATE))    
                            FROM dbo.AF_TBL_PROVIDER_WORKING_DAYS_TIME    
                            WHERE PROVIDER_CODE = %s
                        )    
                    LEFT JOIN dbo.Appointments AP
                        ON AP.PROVIDER_CODE = ISNULL(A.PROVIDER_CODE, %s)
                        AND ISNULL(AP.deleted, 0) = 0
                        AND AP.Appointment_Date_Time >= CAST(GETDATE() AS DATE)
                )
                SELECT * 
                FROM ProviderData 
                WHERE Appointment_Date IN (
                    SELECT DISTINCT TOP 60 Appointment_Date
                    FROM ProviderData
                    WHERE Appointment_Date >= CAST(GETDATE() AS DATE)
                    AND Appointment_Date < DATEADD(DAY, 60, CAST(GETDATE() AS DATE))
                    AND DAY_ON = 'ON'
                    ORDER BY Appointment_Date ASC
                )
                AND DAY_ON = 'ON'
                ORDER BY Appointment_Date, WEEK_DAY;
            """
                # SELECT * 
                # FROM ProviderData 
                # WHERE Appointment_Date IN (
                #     SELECT DISTINCT TOP 30 Appointment_Date
                #     FROM ProviderData
                #     WHERE Appointment_Date >= CAST(GETDATE() AS DATE)
                #     AND Appointment_Date < DATEADD(DAY, 30, CAST(GETDATE() AS DATE))
                #     AND DAY_ON = 'ON'
                #     ORDER BY Appointment_Date ASC
                # )
                # AND DAY_ON = 'ON'
                # ORDER BY Appointment_Date, WEEK_DAY;
            
            # SELECT *
            #     FROM ProviderData
            #     WHERE YEAR(Appointment_Date) = YEAR(GETDATE())
            #     AND DAY_ON = 'ON'
            #     ORDER BY WEEK_DAY, Appointment_Date DESC;


            # Provide same value for all placeholders (7 times)
            params = (
                provider_code,  # ISNULL(A.PROVIDER_CODE, %s)
                provider_code,  # subquery for PRACTICE_CODE
                provider_code,  # BREAK_TIME_FROM subquery
                provider_code,  # BREAK_TIME_TO subquery
                provider_code,  # join condition A.PROVIDER_CODE = %s
                provider_code,  # max date filter
                provider_code   # AP.PROVIDER_CODE = ISNULL(...)
            )

            result_df = BusinessLogic.execute_query(query, params=params, empty_df=df_empty)

            if not result_df.empty:
                return [True, result_df]
            else:
                return [False, "Not found"]

        except ValueError as ve:
            print(f"Input Error: {ve}")
            return [False, f"Input Error: {ve}"]

        except ConnectionError as ce:
            print(f"Database Connection Error: {ce}")
            return [False, "Database connection failed. Please try again later."]

        except Exception as e:
            print(f"Unexpected Error: {str(e)}")
            return [False, f"An unexpected error occurred: {str(e)}"]

        finally:
            print("Execution of getProviderAvailability completed.")


    
    @staticmethod
    def dump_dataframe_to_sql_server(df, uid, table_name="Rescheduling_Logs"):
        try:
            # Step 1: Validate or whitelist table name
            allowed_tables = {"Rescheduling_Logs"}  # whitelist
            if table_name not in allowed_tables:
                raise ValueError("Invalid table name provided.")

            # Step 2: Create table (if it doesn't exist) — still safe because table_name is validated
            create_table_query = f"""
            IF OBJECT_ID(%s, 'U') IS NULL
            BEGIN
                EXEC('CREATE TABLE {table_name} (
                    uid NVARCHAR(50) PRIMARY KEY,
                    creation_date DATE,
                    patient_id NVARCHAR(50),
                    practice_code NVARCHAR(50),
                    provider_code NVARCHAR(50),
                    patient_status NVARCHAR(50),
                    chief_complaint NVARCHAR(MAX),
                    visit_type NVARCHAR(MAX),
                    recommended_specialists NVARCHAR(MAX),
                    response NVARCHAR(MAX)
                )')
            END
            """
            BusinessLogic.execute_query_for_logger(create_table_query, params=(table_name,), fetch_results=False)

            # Step 3: Get already inserted UIDs
            existing_uids_query = f"SELECT uid FROM {table_name}"
            existing_df = BusinessLogic.execute_query_for_logger(existing_uids_query)
            existing_uids = set(existing_df["uid"]) if not existing_df.empty else set()

            # Step 4: Filter only new rows
            df_new = df[~df["uid"].isin(existing_uids)]

            if df_new.empty:
                print("No new records to insert.")
                return

            # Step 5: Parameterized bulk insert using executemany()
            insert_query = f"""
                INSERT INTO {table_name} (
                    uid, creation_date, patient_id, practice_code, provider_code, patient_status, 
                    chief_complaint, visit_type, recommended_specialists, response
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """

            data = [
                (
                    row["uid"], row["creation_date"], row["patient_id"], row["practice_code"],
                    row["provider_code"], row["patient_status"], row["chief_complaint"],
                    row["visit_type"], row["recommended_specialists"], row["response"]
                )
                for _, row in df_new.iterrows()
            ]

            # Use cursor.executemany for safe and fast insertion
            conn, cursor = DBConnection.logging_db()
            cursor.executemany(insert_query, data)
            conn.commit()
            DBConnection.db_disconnect(conn, cursor)

            log('info', uid, f"Successfully inserted {len(df_new)} new rows into {table_name}.")
            print(f"Successfully inserted {len(df_new)} new rows into {table_name}.")

        except Exception as exp:
            log('info', uid, f"Error in dump_dataframe_to_sql_server: {exp}")
            print(f"Error in dump_dataframe_to_sql_server: {exp}")



    @staticmethod
    def dump_future_appointment_request_to_sql_server(df, uid, table_name="Future_Rescheduling_Logs"):
        try:
            # Step 1: Whitelist table name
            allowed_tables = {"Future_Rescheduling_Logs"}
            if table_name not in allowed_tables:
                raise ValueError("Invalid table name.")

            # Step 2: Create table safely (use hardcoded table name if possible)
            create_table_query = f"""
            IF OBJECT_ID(%s, 'U') IS NULL
            BEGIN
                EXEC('CREATE TABLE {table_name} (
                    uid NVARCHAR(50) PRIMARY KEY,
                    creation_date DATE,
                    previous_uid NVARCHAR(50),
                    patient_account NVARCHAR(50),
                    location_code NVARCHAR(50),
                    user_followup_msg NVARCHAR(MAX),
                    initial_recommended_slots NVARCHAR(MAX),
                    message_category_Response NVARCHAR(MAX),
                    appointment_response NVARCHAR(MAX),
                    future_rescheduling_response NVARCHAR(MAX)
                )')
            END
            """
            BusinessLogic.execute_query_for_logger(create_table_query, params=(table_name,), fetch_results=False)

            # Step 3: Get existing UIDs
            existing_query = f"SELECT uid FROM {table_name}"
            existing_df = BusinessLogic.execute_query_for_logger(existing_query)
            existing_uids = set(existing_df["uid"]) if not existing_df.empty else set()

            # Step 4: Filter new records
            df_new = df[~df["uid"].isin(existing_uids)]

            if df_new.empty:
                print("No new records to insert.")
                return

            # Step 5: Bulk insert safely using executemany
            insert_query = f"""
            INSERT INTO {table_name} (
                uid, creation_date, previous_uid, patient_account, location_code, 
                user_followup_msg, initial_recommended_slots, message_category_Response, 
                appointment_response, future_rescheduling_response
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """

            data = [
                (
                    safe_sql_value(row["uid"]),
                    safe_sql_value(row["creation_date"]),
                    safe_sql_value(row["previous_uid"]),
                    safe_sql_value(row["patient_account"]),
                    safe_sql_value(row["location_code"]),
                    safe_sql_value(row["user_followup_msg"]),
                    safe_sql_value(row["initial_recommended_slots"]),
                    safe_sql_value(row["message_category_Response"]),
                    safe_sql_value(row["appointment_response"]),
                    safe_sql_value(row["future_rescheduling_response"])
                )
                for _, row in df_new.iterrows()
            ]

            conn, cursor = DBConnection.logging_db()
            cursor.executemany(insert_query, data)
            conn.commit()
            DBConnection.db_disconnect(conn, cursor)

            print(f"Successfully inserted {len(df_new)} new rows into {table_name}.")

        except Exception as exp:
            log('info', uid, f"Error in future_appointment_request_to_sql_server: {exp}")
            print(f"Error in future_appointment_request_to_sql_server: {exp}")



    @staticmethod
    def getLastSessionHistory(uid, previous_uid, patient_acc):
        df_empty = pd.DataFrame(columns=["uid","creation_date","patient_id","provider_code","patient_status",
                                         "chief_complaint","visit_type","recommended_specialists","response"])
        
        try:
            query = """SELECT * FROM Rescheduling_Logs WHERE uid = %s AND patient_id = %s"""
            params = (previous_uid, patient_acc)

            result_df = BusinessLogic.execute_query_for_logger(query, params=params, empty_df=df_empty)
            # print(result_df)

            if not result_df.empty:
                log('info', uid, f"Record of session {previous_uid} and patient {patient_acc} retrieved successfully")
                return [True, result_df]
            else:
                log('info', uid, f"No data found in session ID {previous_uid} and patient ID {patient_acc}")
                return [False, f"No data found in session ID {previous_uid} and patient ID {patient_acc}"]

        except Exception as exp:
            print(f"Error in getLastSessionHistory: {exp}")


    @staticmethod
    def getFutureReschedulingLogs(uid, patient_acc, date):
        df_empty = pd.DataFrame(columns=["uid", "creation_date", "previous_uid", "patient_account", "location_code", 
                                        "user_followup_msg", "initial_recommended_slots", "message_category_Response", 
                                        "appointment_response", "future_rescheduling_response"])
        try:            
            query = """SELECT * FROM Future_Rescheduling_Logs WHERE previous_uid = %s AND patient_account = %s AND future_rescheduling_response <> 'None' AND creation_date = %s"""
            params = (uid, patient_acc, date)

            result_df = BusinessLogic.execute_query_for_logger(query, params=params, empty_df=df_empty)
            if not result_df.empty:
                return [True, result_df]
            else:
                return [False, f"No data found for uid {uid} and patient {patient_acc} in Future_Rescheduling_Logs"]
        except Exception as exp:
            print(f"Error in getFutureReschedulingLogs: {exp}")            
            return [False, str(exp)]
    

    @staticmethod    
    def getProviderWeeklySchedule(provider_code):        
        df_empty = pd.DataFrame(columns=["Weekday", "Status"])
        
        try:
            query = """SELECT top 7 Weekday_Id AS Weekday, Day_On AS Status FROM AF_TBL_PROVIDER_WORKING_DAYS_TIME WHERE Provider_Code = %s order by Created_Date desc;"""
            
            # Input provider_code is numpy integer, convert to int
            params = (int(provider_code),)
            result_df = BusinessLogic.execute_query(query, params=params, empty_df=df_empty)

            if not result_df.empty:
                return [True, result_df]
            else:
                return [False, f"Empty data found for provider {provider_code} in AF_TBL_PROVIDER_WORKING_DAYS_TIME"]
        except Exception as exp:
            print(f"Error in getProviderWeeklySchedule: {exp}")            
            return [False, str(exp)]
    
    @staticmethod
    def getProviderDefaultTime(provider_code):
        df_empty = pd.DataFrame(columns=["Time_From_New", "Time_To_New", "Break_Time_From_New", "Break_Time_To_New"])
        
        try:
            query = """SELECT TOP 1 Time_From_New, Time_To_New, Break_Time_From_New, Break_Time_To_New FROM AF_TBL_PROVIDER_WORKING_DAYS_TIME WHERE Provider_Code = %s order by Created_Date desc;"""

            # Input provider_code is numpy integer, convert to int
            params = (int(provider_code),)
            result_df = BusinessLogic.execute_query(query, params=params, empty_df=df_empty)

            if not result_df.empty:
                return [True, result_df]
            else:
                return [False, f"Empty data found for provider {provider_code} in AF_TBL_PROVIDER_WORKING_DAYS_TIME"]
        
        except Exception as exp:
            print(f"Error in getProviderDefaultTime: {exp}")            
            return [False, str(exp)]

    @staticmethod
    def getProviderLocationData(provider_code, patient_account):
        df_empty = pd.DataFrame(columns=["Provider_Code","Patient_Account","Location_Code",
                                         "Location_Address","Location_Name","Location_State","Location_Zip"])
        
        try:
            query = """SELECT
                        apt.Provider_Code,    
                        apt.Patient_Account,  
                        pl.Location_Code,    
                        pl.Location_Address,    
                        pl.Location_Name,      
                        pl.Location_State, 
                        pl.Location_Zip
                    FROM Appointments apt
                    JOIN Practice_Locations pl 
                        ON apt.Location_Id = pl.Location_Code
                    WHERE apt.Provider_Code = %s
                    AND apt.Patient_Account = %s
                    AND apt.Created_By NOT LIKE '%test%' 
                    AND pl.Location_Name NOT IN ('test', 'MTBC', 'DEMO')
                    AND ISNULL(pl.Deleted, 0) = 0
                    GROUP BY 
                        apt.Provider_Code,
                        apt.Patient_Account,  
                        pl.Location_Code,
                        pl.Location_Address,
                        pl.Location_Name,      
                        pl.Location_State, 
                        pl.Location_Zip
                    ORDER BY 1;"""

            params = (provider_code, patient_account)
            result_df = BusinessLogic.execute_query(query, params=params, empty_df=df_empty)
            # print(result_df)

            if not result_df.empty:
                return [True, result_df]
            else:
                return [False, f"No data found"]

        except Exception as exp:
            print(f"Error in getProviderLocationData: {exp}")
    
    @staticmethod
    def getLocationCode(patient_Code, provider_Code):
        df_empty = pd.DataFrame(columns=['Location_Id'])

        try:
            query = """SELECT TOP 1 Location_Id FROM Appointments a where Provider_Code = %s AND Patient_Account = %s Order by Created_Date desc"""

            params = (provider_Code, patient_Code)
            result_df = BusinessLogic.execute_query(query, params=params, empty_df=df_empty)
            # print(result_df)

            if not result_df.empty:
                return [True, result_df]
            else:
                return [False, f"No data found"]

        except Exception as exp:
            print(f"Error in getLocationCode: {exp}")
    
    @staticmethod
    def getDefaultProviderLocation(provider_Code):
        df_empty = pd.DataFrame(columns=['Location_Id', 'Location_Name'])

        try:
            # query = f"""SELECT DEFAULT_LOCATION AS Location_Id FROm AF_TBL_PRACTICE_USER atpu WHERE PROVIDER_CODE = '{provider_Code}'"""
            query = """
                    SELECT atpu.DEFAULT_LOCATION AS Location_Id, pl.Location_Name FROM AF_TBL_PRACTICE_USER atpu 
                    LEFT JOIN Practice_Locations pl
                    ON atpu.DEFAULT_LOCATION = pl.Location_Code 
                    WHERE atpu.PROVIDER_CODE = %s"""

            params = (provider_Code,)
            result_df = BusinessLogic.execute_query(query, params=params, empty_df=df_empty)
            # print(result_df)

            if not result_df.empty:
                return [True, result_df]
            else:
                return [False, f"No data found"]

        except Exception as exp:
            print(f"Error in getLocationCode: {exp}")


    @staticmethod
    def getProviderDefaultLocationCode(provider_Code, patient_Code):
        df_empty = pd.DataFrame(columns=['ProviderCode', 'ProviderName', 'ProviderPrefix'])
        try:
            query = f""" """

            result_df = BusinessLogic.execute_query(query, df_empty)
            # print(result_df)

            if not result_df.empty:
                return [True, result_df]
            else:
                return [False, f"No data found"]

        except Exception as exp:
            print(f"Error in getLocationCode: {exp}")

    @staticmethod
    def dump_conversation_history(Session_ID, patient_code, practice_Code, provider_code, category,
                                conversation_text, location_data=None, selected_time_slot=None,
                                reason_id=None, reason_name=None, chief_complaint=None,
                                previous_appointment=None, table_name="Conversation_History"):
        try:
            # Step 1: Whitelist table name to avoid injection
            allowed_tables = {"Conversation_History"}
            if table_name not in allowed_tables:
                raise ValueError("Invalid table name.")

            # Step 2: Create table if it doesn't exist (use EXEC only after validating table_name)
            create_table_query = f"""
            IF OBJECT_ID(%s, 'U') IS NULL
            BEGIN
                EXEC('CREATE TABLE {table_name} (
                    CONVERSATION_ID INT IDENTITY(1,1) PRIMARY KEY,
                    CREATION_DATE DATE DEFAULT GETDATE(),
                    SESSION_ID NVARCHAR(50),
                    PATIENT_CODE NVARCHAR(50),
                    PRACTICE_CODE NVARCHAR(50),
                    PROVIDER_CODE NVARCHAR(50),
                    CATEGORY NVARCHAR(50),
                    REASON_ID NVARCHAR(50),
                    REASON_NAME NVARCHAR(50),
                    CHIEF_COMPLAINT NVARCHAR(MAX),
                    SELECTED_TIME_SLOT NVARCHAR(50),
                    AVAILABLE_LOCATION_CODES NVARCHAR(MAX),
                    PREVIOUS_APPOINTMENT NVARCHAR(MAX),
                    CONVERSATION_TEXT NVARCHAR(MAX)
                )')
            END
            """
            BusinessLogic.execute_query_for_logger(create_table_query, params=(table_name,), fetch_results=False)

            # Step 3: Prepare insert query with parameters
            insert_query = f"""
            INSERT INTO {table_name} (
                SESSION_ID, PATIENT_CODE, PRACTICE_CODE, PROVIDER_CODE, CATEGORY, 
                REASON_ID, REASON_NAME, CHIEF_COMPLAINT, SELECTED_TIME_SLOT, 
                AVAILABLE_LOCATION_CODES, PREVIOUS_APPOINTMENT, CONVERSATION_TEXT
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            # Safely convert any dict-like values to strings
            safe_previous_appointment = (
                json.dumps(previous_appointment) if isinstance(previous_appointment, dict) else previous_appointment
            )
            safe_conversation_text = (
                json.dumps(conversation_text) if isinstance(conversation_text, dict) else conversation_text
            )
            safe_location_data = (
                json.dumps(location_data) if isinstance(location_data, (dict, list)) else location_data
            )

            params = (
                Session_ID, patient_code, practice_Code, provider_code, category,
                reason_id, reason_name, chief_complaint, selected_time_slot,
                safe_location_data, safe_previous_appointment, safe_conversation_text
            )

            insert_status = BusinessLogic.execute_query_for_logger(insert_query, params=params, fetch_results=False)

            if insert_status:
                log('info', Session_ID, f"Successfully inserted new row into {table_name}.")
                print(f"Successfully inserted new row into {table_name}.")
            else:
                log('info', Session_ID, "No records inserted due to an error.")
                print("No records inserted due to an error.")

        except Exception as exp:
            log('info', Session_ID, f"Error in dump_conversation_history: {exp}")
            print(f"Error in dump_conversation_history: {exp}")


    @staticmethod
    def dump_provider_list(Session_ID, practice_Code, provider_names, table_name="Provider_List"):
        try:
            # Step 1: Ensure table exists
            create_table_query = f"""
            IF OBJECT_ID('{table_name}', 'U') IS NULL
            BEGIN
                CREATE TABLE {table_name} (                    
                    SESSION_ID NVARCHAR(50),                    
                    PRACTICE_CODE NVARCHAR(50),
                    PROVIDER_NAMES NVARCHAR(MAX)
                );
            END
            """
            BusinessLogic.execute_query_for_logger(create_table_query, fetch_results=False)

            # Step 2: Check if SESSION_ID already exists
            check_query = f"SELECT 1 FROM {table_name} WHERE SESSION_ID = '{escape_sql_string(Session_ID)}'"
            check_result = BusinessLogic.execute_query_for_logger(check_query)

            if not check_result.empty:
                log('info', Session_ID, f"Record with SESSION_ID {Session_ID} already exists. Skipping insert.")
                print(f"Record with SESSION_ID {Session_ID} already exists. Skipping insert.")
                return

            # Step 3: Escape values
            safe_session_id = escape_sql_string(Session_ID)
            safe_practice_code = escape_sql_string(practice_Code)
            safe_provider_names = escape_sql_string(provider_names)

            # Step 4: Insert
            insert_query = f"""
            INSERT INTO {table_name} (
                SESSION_ID, PRACTICE_CODE, PROVIDER_NAMES
            ) VALUES (
                '{safe_session_id}', '{safe_practice_code}', '{safe_provider_names}'
            )
            """

            insert_status = BusinessLogic.execute_query_for_logger(insert_query, fetch_results=False)

            if insert_status:
                log('info', Session_ID, f"Successfully inserted new row into {table_name}.")
                print(f"Successfully inserted new row into {table_name}.")
            else:
                log('info', Session_ID, f"No records inserted due to an error.")
                print("No records inserted due to an error.")

        except Exception as exp:
            log('info', Session_ID, f"Error in dump_provider_list: {exp}")
            print(f"Error in dump_provider_list: {exp}")


    @staticmethod
    def getConversationHistory(session_id, practice_code):
        df_empty = pd.DataFrame(columns=["CONVERSATION_ID","CREATION_DATE","SESSION_ID","PATIENT_CODE",
                                         "PRACTICE_CODE","PROVIDER_CODE","CATEGORY","REASON_ID","REASON_NAME",
                                         "CHIEF_COMPLAINT","SELECTED_TIME_SLOT","AVAILABLE_LOCATION_CODES","CONVERSATION_TEXT"])

        try:
            query = """SELECT * FROM Conversation_History WHERE SESSION_ID = %s AND PRACTICE_CODE = %s Order By CONVERSATION_ID ASC"""
            
            params = (session_id, practice_code)
            result_df = BusinessLogic.execute_query_for_logger(query, params=params, empty_df=df_empty)
            # print(result_df)

            if not result_df.empty:
                return [True, result_df]
            else:
                return [False, f"No data found"]

        except Exception as exp:
            print(f"Error in getConversationHistory: {exp}")

    @staticmethod
    def getProviderNamesAndCode(practiceCode):
        df_empty = pd.DataFrame(columns=['ProviderCode', 'ProviderName', 'ProviderPrefix'])

        try:
            query = """EXEC WS_PROC_TALKPHR_GET_PRACTICE_PROVIDERS %s"""

            params = (practiceCode,)
            result_df = BusinessLogic.execute_query(query, params=params, empty_df=df_empty)
            # print(result_df)

            if not result_df.empty:
                return [True, result_df]
            else:
                return [False, f"No data found"]

        except Exception as exp:
            print(f"Error in getProviderNames: {exp}")


    @staticmethod
    def getAppointmentReasonID(practiceCode):
        df_empty = pd.DataFrame(columns=['Reason_Id', 'Reason_Name'])

        try:
            query = """Select Reason_Id, Reason_Name from AF_Tbl_Practice_Appointment_Reasons WHERE PRACTICE_CODE = %s AND DELETED = 0"""
            
            params = (practiceCode,)
            result_df = BusinessLogic.execute_query(query, params=params, empty_df=df_empty)
            # print(result_df)

            if not result_df.empty:
                return [True, result_df]
            else:
                return [False, f"No data found"]

        except Exception as exp:
            print(f"Error in getAppointmentReasonID: {exp}")

    @staticmethod
    def getLastAppointmentData(patient_Code, practice_Code):
        df_empty = pd.DataFrame(columns=["Provider_Name", "Provider_Code", "Appointment_ReasonID", "Appointment_LocationID",
                                         "Appointment_LocationName", "Location_Address", "Appointment_Date_Time"])

        try:
            query = """SELECT TOP 1
                        CONCAT(pro.Provid_FName, ' ', pro.Provid_LName) AS Provider_Name,
                        app.Provider_Code,
                        app.Reason_Id AS Appointment_ReasonID,
                        app.Location_Id AS Appointment_LocationID, 
                        pl.Location_Name AS Appointment_LocationName, 
                        pl.Location_Address,
                        app.Appointment_Date_Time
                    FROM Appointments app
                    LEFT JOIN Providers pro ON app.Provider_Code = pro.Provider_Code
                    LEFT JOIN Practice_Locations pl ON app.Location_Id = pl.Location_Code
                    WHERE app.Patient_Account = %s
                    AND app.practice_code = %s
                    AND ISNULL(app.deleted, 0) = 0
                    -- AND app.Created_By NOT LIKE '%test%'
                    ORDER BY app.Appointment_Date_Time DESC;"""
            
            params = (patient_Code, practice_Code)
            result_df = BusinessLogic.execute_query(query, params=params, empty_df=df_empty)
            # print(result_df)

            if not result_df.empty:
                return [True, result_df]
            else:
                return [False, f"No data found"]

        except Exception as exp:
            print(f"Error in getLastAppointmentData: {exp}")

        

def escape_sql_string(value):
    """Escape single quotes in a value by converting it to a string and replacing ' with ''."""
    return str(value).replace("'", "''")


def safe_sql_value(val):
    """Convert dict/list to JSON string; leave other types unchanged."""
    if isinstance(val, (dict, list)):
        return json.dumps(val)
    return val