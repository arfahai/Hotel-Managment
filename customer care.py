# Simple Customer Care Service

services = {
    "1": "Room Cleaning",
    "2": "Food Delivery",
    "3": "Taxi Service",
    "4": "Laundry",
    "5": "Complaint",
    "6": "Other"
}

tickets = []   # store all customer complaints/requests

print("Welcome to Hotel Customer Care Service")

while True:
    print("\nAvailable Services:")
    for key, val in services.items():
        print(f"{key}. {val}")
    
    choice = input("Enter service number (or type 'no' to exit): ")
    
    if choice.lower() == "no":
        print("Thank you for using our service!")
        break
    
    if choice in services:
        name = input("Enter your name: ")
        room = input("Enter your room number: ")
        message = input("Please describe your request/issue: ")
        
        ticket = {
            "customer": name,
            "room": room,
            "service": services[choice],
            "message": message
        }
        
        tickets.append(ticket)
        print("✅ Your request has been recorded. Our team will contact you soon.")
    else:
        print("Invalid option. Please try again.")

print("\nAll Tickets Recorded:")
for t in tickets:
    print(f"- {t['customer']} (Room {t['room']}): {t['service']} → {t['message']}")
