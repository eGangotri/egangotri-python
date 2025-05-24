import uuid
import json
import logging
from typing import Collection, Dict, Any

from ..utils.rest_util import RestUtil

ITEMS_QUEUED_PATH = "itemsQueued"
ITEMS_USHERED_PATH = "itemsUshered"
UPLOAD_CYCLE_ROUTE = "uploadCycle"
BACKEND_SERVER = "http://localhost:8000/"

def add_to_upload_cycle(profile: str, profile_path: str, uploadables: Collection[str], mode: str = "") -> Dict[str, Any]:
    """Add profiles to the upload cycle and return the result.
    
    Args:
        profile: Profile name
        profile_path: Profile path
        uploadables: List of uploadable files
        mode: Optional mode string
        
    Returns:
        Dictionary containing the response from the REST API call
    """
    result: Dict[str, Any] = {}
    rest_api_route = f"/{UPLOAD_CYCLE_ROUTE}/add"
    grand_total_of_all_uploadables = len(uploadables)
    logging.info("grand_total_of_all_uploadables %s", grand_total_of_all_uploadables)
    
    profiles_and_count = []
    
    profile_data = {
        "archiveProfile": profile,
        "archiveProfilePath": profile_path,
        "count": grand_total_of_all_uploadables,
        "absolutePaths": uploadables,
    }
    profiles_and_count.append(profile_data)
    
    logging.info("profiles_and_count: %s", json.dumps(profiles_and_count))
    
    try:
        params_map: Dict[str, Any] = {}
        
        upload_cycle_id = str(uuid.uuid4())
            
        params_map["uploadCycleId"] = upload_cycle_id
        params_map["uploadCount"] = grand_total_of_all_uploadables
        params_map["archiveProfiles"] = profiles_and_count
        params_map["deleted"] = False

        
        if mode:
            params_map["mode"] = mode
            
        logging.info("params_map %s", params_map)
        result = RestUtil.make_post_call(rest_api_route, params_map)
        
    except Exception as e:
        logging.error("Exception: addToUploadCycle Error while calling %s %s", rest_api_route, str(e), exc_info=True)
        return None
        
    return result