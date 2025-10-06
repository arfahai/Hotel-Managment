Menu = {
    'pizza': 500,
    "pasta": 750,
    "spin rolls": 525,
    "garlic bread": 350,
    "brownie icecream": 450,
    "soft drinks": 250,
    "water": 100
}

print("Welcome to Our Restaurant!")   


cart_total = 0   # total amount initialize

while True:
    item = input("Please enter your item (or type 'no'  to finish): ").lower()

    if item == "no":          # loop break condition
        print("Thank you! Your order is completed.")
        break

    if item in Menu:          # check item in menu
        cart_total += Menu[item]
        print(f"{item.title()} has been added to your cart.")
    else:
        print("Your entered item is not in the menu.")

print(f"Your total bill is: {cart_total} PKR")
