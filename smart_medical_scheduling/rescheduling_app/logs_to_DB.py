import pymssql
import pandas as pd
from parse_logs import parse_logs_to_dataframe
from db_operations import BusinessLogic
import os


def dump_logs_to_DB(df, server, database, username, password, table_name="Rescheduling_Logs"):
    """
    Dumps a pandas DataFrame into a SQL Server table.

    Parameters:
        df (pd.DataFrame): The pandas DataFrame to be dumped into the database.
        server (str): SQL Server hostname or IP address.
        database (str): Name of the database.
        username (str): SQL Server username.
        password (str): SQL Server password.
        table_name (str): Name of the target table in SQL Server (default: 'Rescheduling_Logs').
    """
    BusinessLogic.execute_query()
    # Create a connection to the SQL Server
    conn = pymssql.connect(server=server, user=username, password=password, database=database)
    cursor = conn.cursor()

    # Create the table if it doesn't already exist
    create_table_query = f"""
    IF OBJECT_ID('{table_name}', 'U') IS NULL 
    CREATE TABLE {table_name} (
        uid NVARCHAR(50),
        creation_date DATE,
        patient_id NVARCHAR(50),
        provider_code NVARCHAR(50),
        patient_status NVARCHAR(50),
        chief_complaint NVARCHAR(MAX),
        visit_type NVARCHAR(MAX),
        recommended_specialists NVARCHAR(MAX),
        response NVARCHAR(MAX)
    )
    """
    cursor.execute(create_table_query)
    conn.commit()

    # Insert data into the table
    for _, row in df.iterrows():
        insert_query = f"""
        INSERT INTO {table_name} (uid, creation_date, patient_id, provider_code, patient_status, 
                                  chief_complaint, visit_type, recommended_specialists, response)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        cursor.execute(insert_query, (
            row['uid'],
            row['creation_date'],
            row['patient_id'],
            row['provider_code'],
            row['patient_status'],
            row['chief_complaint'],
            row['visit_type'],
            row['recommended_specialists'],
            row['response']
        ))

    # Commit the transaction and close the connection
    conn.commit()
    cursor.close()
    conn.close()

    print(f"Data has been successfully inserted into the {table_name} table!")

# Example usage
# LOGS_FILE_PATH = ""
    
# server = ""  
# database = "" 
# username = ""
# password = ""

# dump_logs_to_DB(logs_df, server, database, username, password)
