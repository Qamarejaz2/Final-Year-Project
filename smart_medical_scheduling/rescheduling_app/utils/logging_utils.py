import logging

error_logger = logging.getLogger('api_request_error')
info_logger = logging.getLogger('api_request_info')
 
log_info = lambda x:  info_logger.info(x)
log_error = lambda x:  error_logger.error(x)

modes = {
    'error': log_error,
    'info': log_info
}
 
def log(mode, uid, message = None):
    log_message = f"[{uid}] | {message or ''}"
    logger = modes.get(mode,info_logger)
    logger(log_message)
 
def log_request(mode, uid, request):
    method = request.method
    url = request.path
    headers = request.headers
    remote_address = request.META.get('REMOTE_ADDR')
    request_log = f"{method} on {url} from {remote_address} having headers: {headers}"
   
    log_message = f"[{uid}] | {request_log}"
    logger = modes.get(mode,info_logger)
    logger(log_message)