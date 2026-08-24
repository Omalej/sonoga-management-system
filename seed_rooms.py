import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sonoga_hms.settings')
django.setup()

from hotel.models import Room

rooms_to_create = [
    {'number': 'Addis Ababa', 'type': 'Standard Room', 'rate': 30000.00},
    {'number': 'Family Suite 1', 'type': 'Family Suite', 'rate': 50000.00},
    {'number': 'Iga-Okpaya', 'type': 'Family Suite', 'rate': 50000.00},
    {'number': 'Omada & Qatar', 'type': 'Family Suite', 'rate': 50000.00},
    {'number': 'Accra', 'type': 'Family Suite', 'rate': 50000.00},
    {'number': 'Freetown', 'type': 'Standard Room', 'rate': 30000.00},
    {'number': 'Yaounde', 'type': 'Standard Room', 'rate': 30000.00},
    {'number': 'Libraville', 'type': 'Standard Room', 'rate': 30000.00},
    {'number': 'Bissau', 'type': 'Standard Room', 'rate': 30000.00},
    {'number': 'Conakry', 'type': 'Standard Room', 'rate': 30000.00},
    {'number': 'Iklaga', 'type': 'Standard Room', 'rate': 30000.00},
    {'number': 'Lasaka', 'type': 'Standard Room', 'rate': 30000.00},
    {'number': 'Monrovia', 'type': 'Standard Room', 'rate': 30000.00},
    {'number': 'Luanda', 'type': 'Standard Room', 'rate': 30000.00},
    {'number': 'Ochekawo', 'type': 'Standard Room', 'rate': 30000.00},
    {'number': 'Kigali', 'type': 'Standard Room', 'rate': 30000.00},
    {'number': 'Johannesburg', 'type': 'Executive Suite', 'rate': 90000.00},
    {'number': 'Cairo', 'type': 'Executive Suite', 'rate': 90000.00},
]

for r in rooms_to_create:
    room, created = Room.objects.get_or_create(
        room_number=r['number'],
        defaults={
            'room_type': r['type'],
            'rate': r['rate'],
            'status': 'Available'
        }
    )
    if not created:
        room.room_type = r['type']
        room.rate = r['rate']
        room.status = 'Available'
        room.save()
    print("Room " + room.room_number + " (" + r['type'] + ") - Synchronized successfully.")

print('All WordPress rooms successfully synchronized to Sonoga HMS!')
