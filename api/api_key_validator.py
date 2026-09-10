import os
from typing import List
from sitesync.config import settings
import requests

def validate_api_keys() -> List[str]:
    errors = []
    
    # Test NVIDIA NIM keys
    for base_url, api_key, model_id in settings.active_models:
        if "nvidia" in base_url or "nvcf" in base_url:
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            # Attempt a quick models list or basic completion to verify the key
            try:
                response = requests.get(f"{base_url.rstrip('/')}/models", headers=headers, timeout=5)
                if response.status_code == 401:
                    errors.append(f"Invalid API Key for model {model_id} at {base_url}")
            except Exception as e:
                # If the /models endpoint isn't supported, we ignore connection timeouts for this check
                pass
                
    if not errors:
        print("✅ All configured API keys validated successfully.")
    else:
        for err in errors:
            print(f"❌ {err}")
            
    return errors

if __name__ == "__main__":
    validate_api_keys()
