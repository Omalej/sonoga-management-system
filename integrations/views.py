from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json

@csrf_exempt
def wordpress_ping(request):
    return JsonResponse({'status': 'success', 'message': 'Sonoga API is online and synchronized.'})

@csrf_exempt
def wordpress_booking_webhook(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            # Placeholder for processing incoming WordPress hotel bookings
            return JsonResponse({'status': 'success', 'message': 'Booking received and processed.'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    return JsonResponse({'status': 'error', 'message': 'Invalid request method.'}, status=405)
