import json
from django.http import JsonResponse
import requests

def list_tools(request):
    try:
        response = requests.get("http://localhost:9000/config/tools")
        data = json.loads(response.json())
        return JsonResponse(data["tools"], safe=False)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)