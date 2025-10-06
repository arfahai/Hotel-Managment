room_rates = {
    "single": 3000,   # 1 bed
    "double": 5000,   # 2 beds
    "suite": 8000,    # luxury room
    "deluxe": 12000   # premium room
}

hotel_bookings = []

def new_booking():
    print("\nAvailable Room Types & Rates (per night):")
    for room, rate in room_rates.items():
        print(f"{room.title()}: {rate} PKR")
    
    booking = {
        "booking_id": len(hotel_bookings) + 1,
        "name": input("Enter your name: "),
        "phone": input("Enter your phone number: "),
        "check_in": input("Enter check-in date (YYYY-MM-DD): "),
        "check_out": input("Enter check-out date (YYYY-MM-DD): "),
        "num_guests": int(input("Enter number of guests: ")),
        "room_type": input("Enter room type (single/double/suite/deluxe): ").lower(),
        "num_rooms": int(input("Enter number of rooms: ")),
    }

    # Calculate total price
    if booking["room_type"] in room_rates:
        rate = room_rates[booking["room_type"]]
        booking["price_per_room"] = rate
        booking["total_price"] = booking["num_rooms"] * rate
    else:
        booking["price_per_room"] = 0
        booking["total_price"] = 0

    booking["payment_status"] = "pending"
    
    hotel_bookings.append(booking)
    
    print("\nBooking successful!")
    print(f"Booking ID: {booking['booking_id']}")
    print(f"Room Type: {booking['room_type'].title()}")
    print(f"Rooms: {booking['num_rooms']}, Guests: {booking['num_guests']}")
    print(f"Total Price: {booking['total_price']} PKR")

new_booking()
