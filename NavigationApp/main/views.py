from django.shortcuts import render
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
import json

# If you put logic in main/NavigationApp/graph.py, prefer that; otherwise fallback.
try:
    from .NavigationApp.graph import find_route_to_nearest_exit
except Exception:
    find_route_to_nearest_exit = None

def homepage(request):
    return render(request, 'main/homepage.html')

@csrf_exempt
def api_route(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    try:
        payload = json.loads(request.body.decode('utf-8') or "{}")
        x = float(payload.get('x'))
        y = float(payload.get('y'))
    except Exception:
        return HttpResponseBadRequest('Invalid JSON payload: expected {"x":number,"y":number}')
    if callable(find_route_to_nearest_exit):
        return JsonResponse(find_route_to_nearest_exit((x, y)))
    # fallback: return only the user point
    return JsonResponse({'path':[{'id':'user','label':'Vy','x':x,'y':y,'type':'user'}]})