import json

def lambda_handler(event, context):
    return {
        "messages": [
                    {
                      "type": "unstructured",
                      "unstructured": {
                          "id": "string",
                          "text": "Application under development. Search functionality will be implemented in Assignment 2",
                          "timestamp": "string"
                      }
                    }
        ]
    }
    


