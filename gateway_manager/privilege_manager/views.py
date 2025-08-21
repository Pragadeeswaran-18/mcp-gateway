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
    
def check_tool_privilege(request):
    tool_name = request.GET.get("tool_name")
    if not tool_name:
        return JsonResponse({"error": "Tool name is required"}, status=400)
    if tool_name in ["create_issue", "delete_file", "merge_pull_request"]:
        return JsonResponse({"allowed": False}, status=403)
    return JsonResponse({"allowed": True}, status=200)