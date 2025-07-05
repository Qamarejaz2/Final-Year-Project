import traceback
# from rescheduling_app.utils.logging_utils import log_info,log_error,log
import openai
from openai import OpenAI
import os
# from django.conf import settings
from dotenv import load_dotenv

load_dotenv()
API_KEY = "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"
# os.environ["OPENAI_API_KEY"] = API_KEY

client = OpenAI(api_key=API_KEY)
# print(api_key)

class GenerateOpenAIResponse:
    def __init__(self):
        self.model = None
        self.model_name = 'gpt-4o'

        try:                       
            openai.api_key = API_KEY
            print("API Key configured")

        except Exception as e:
            raise Exception(f'OpenAI model initialization failed: {e}')

    def generate_response(self, uid, prompt):
        try:
            # Generate response using the OpenAI model
            response = client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant"},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=4096,
                temperature=0.3,
                top_p=0.95
            )
            # print(response)
            generated_text = response.choices[0].message.content

            return generated_text
        except Exception as e:
            print("Exception generate_response:", e)
            return 'Error'

