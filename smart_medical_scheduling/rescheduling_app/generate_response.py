import traceback
from rescheduling_app.utils.logging_utils import log_info,log_error,log
from vertexai.generative_models import Part, GenerativeModel
import vertexai
# from google import genai
# from google.genai import types
import os
from django.conf import settings


aiml_file_path = os.path.join(settings.BASE_DIR, "aiml-365220-7c2e15a0d60a.json")

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = aiml_file_path
vertexai.init(project="aiml-365220", location="us-central1")

# class GenerateResponse:
#     def __init__(self):
#         self.model = None        
#         model_name = 'gemini-2.5-flash-preview-04-17'
#         # model_name = 'gemini-2.0-flash'
         
#         try:
#             self.model = GenerativeModel(model_name)
#             log_info(f'Model loaded: {model_name}')
#         except:
#             log_error('Unable to load Model')
#             raise Exception('Gemini model did not load.')

#     def generate_response(self, uid, prompt):
#         try:
#             # Generate response using the model            
#             response = self.model.generate_content(
#                 prompt,                
#                 generation_config={
#                     "max_output_tokens": 8192,
#                     "temperature": 0.3,
#                     "top_p": 0.95,                    
#                 }
#             )
#             log('info', uid, f"Response: {response}")
#             return response.text
#         except Exception as e:
#             log('info', uid, f"Exception in model response: {e}")
#             print("Exception generate_response:", e)
#             return 'Error'

# =================================================================
# Thinking model without budget
class GenerateResponse:
    # Define model type lists
    THINKING_MODELS = [        
        "gemini-2.5-flash", 
        "gemini-2.5-pro",
        "gemini-2.5-flash-preview-04-17"
    ]
    NON_THINKING_MODELS = [                
        "gemini-2.0-flash-001",
        "gemini-2.0-flash",
        "gemini-2.0-pro"
    ]

    def __init__(self):
        self.model = None
        self.model_name = None
        self.default_model_name = 'gemini-2.5-flash'
        self.load_model(self.default_model_name)

    def load_model(self, model_name):
        try:
            self.model = GenerativeModel(model_name)
            self.model_name = model_name
            log_info(f'Model loaded: {model_name}')
        except Exception as e:
            log_error(f'Unable to load model: {e}')
            raise Exception('Gemini model did not load.')

    def get_max_tokens(self, model_name):
        if model_name in self.THINKING_MODELS:
            return 65535
        elif model_name in self.NON_THINKING_MODELS:
            return 8192
        else:
            return 8192  # fallback default if model is unknown

    def generate_response(self, uid, prompt, model_name=None):
        try:
            if model_name:
                self.load_model(model_name)

            print(f"Using Model: {self.model_name}")

            max_tokens = self.get_max_tokens(self.model_name)

            response = self.model.generate_content(
                prompt,
                generation_config={
                    "max_output_tokens": max_tokens,
                    "temperature": 0.3,
                    "top_p": 0.95,
                }
            )
            log('info', uid, f"Response: {response}")

            finish_reason = response.candidates[0].finish_reason
            text = response.candidates[0].content.parts[0].text

            log('info', uid, f"Finish Reason: {finish_reason.name}")
            log('info', uid, f"Response Text: {text}")

            print(f"\nType of finish reason: {type(finish_reason.name)}")
            print(f"Type of text: {type(text)}\n")

            if finish_reason.name == "MAX_TOKENS":
                log('info', uid, f"MAX_TOKEN Error occur, Using Gemini 2.0 flash 001...")

                # Recursive fallback call with a non-thinking model
                response = self.generate_response(uid, prompt, model_name="gemini-2.0-flash-001")
                log('info', uid, f"After MAX_TOKENS, Response: {response}")
                return response

            return text

        except Exception as e:
            log('info', uid, f"Exception in model response: {e}")
            print("Exception generate_response:", e)
            return 'Error'



# =================================================================
# Thinking model with budget
# class GenerateResponse:
#     def __init__(self):        
#         self.client = None
#         self.model_name = None
#         self.default_model_name = 'gemini-2.5-flash-preview-04-17'        
#         self.load_model(self.default_model_name)

#     def load_model(self, model_name):
#         try:
#             self.client = genai.Client(vertexai=True, project="aiml-365220", location="us-central1")
#             self.model_name = model_name
#             log_info(f'Model selected: {model_name}')
#         except Exception as e:
#             log_error(f'Unable to initialize client: {e}')
#             raise Exception('Gemini client did not load.')

#     def generate_response(self, uid, prompt, model_name=None, thinking_budget=4000):
#         try:
#             if model_name:
#                 self.load_model(model_name)
            
#             # Check if model is gemini-2.5-flash-preview-04-17 to use thinking budget
#             if self.model_name == 'gemini-2.5-flash-preview-04-17':
#                 # Create structured content with user role
#                 contents = [
#                     types.Content(
#                         role="user",
#                         parts=[types.Part.from_text(text=prompt)]
#                     )
#                 ]
                
#                 # Set up configuration with thinking budget
#                 generate_content_config = types.GenerateContentConfig(
#                     max_output_tokens=8192,
#                     temperature=0.3,
#                     top_p=0.95,
#                     thinking_config=types.ThinkingConfig(thinking_budget=thinking_budget)
#                 )
                
#                 # Generate content using client with thinking budget
#                 response = self.client.models.generate_content(
#                     model=self.model_name,
#                     contents=contents,
#                     config=generate_content_config
#                 )
                
#                 # Print thinking process if available
#                 if hasattr(response, 'thinking'):
#                     print(f"Thinking process: {response.thinking}")

#             else:
#                 # Fallback to simpler generate_content call without thinking budget
#                 response = self.client.models.generate_content(
#                     model=self.model_name,
#                     contents=prompt,
#                     generation_config={
#                         "max_output_tokens": 8192,
#                         "temperature": 0.3,
#                         "top_p": 0.95,
#                     }
#                 )
            
#             log('info', uid, f"Response: {response}")
#             return response.text
#         except Exception as e:
#             log('info', uid, f"Exception in model response: {e}")
#             print("Exception generate_response:", e)
#             return 'Error'

