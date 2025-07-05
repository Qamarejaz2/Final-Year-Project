from enum import Enum, auto

class AppointmentChatBotStatus(Enum):        
    REQUESTED_PROVIDERS_SLOTS = "Appointment_Slots"
    REQUESTED_PROVIDERS_LIST = "Providers_List"
    APPOINTMENT_SCHEDULING_REQUEST = "Plain_Text"
    PROVIDE_CHIEF_COMPLAINT = "Providers_List"
    CHOOSED_PROVIDER_AVAILABLE_SLOTS = "Appointment_Slots"
    CHOOSED_PREFERRED_LOCATION = "Locations_List"
    BOOK_WITH_LAST_PROVIDER = "Appointment_Slots"
    REQUEST_MORE_SLOTS = "Appointment_Slots"
    REQUEST_MORE_INFORMATION = "Plain_Text"
    GENERAL_QUERY = "Plain_Text"
    FRIENDLY_NOTE = "Plain_Text"
    UNCLEAR_MESSAGE = "Plain_Text"
    PREVIOUS_APPOINTMENT = "Previous_Appointment"
    ERROR = "Error"
    APPOINTMENT_SCHEDULED = "Appointment_Scheduled"
    APPOINTMENT_NOT_SCHEDULED = "Appointment_Not_Scheduled"
