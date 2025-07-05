from urllib.parse import quote

def generate_google_maps_url(location, name, state, zip):
    full_address = f"{location}, {name}, {state} {zip}"

    return f"https://www.google.com/maps/search/?q={quote(full_address)}"



# # Example Usage
# address = "2648 ROUTE 27, NORTH BRUNSWICK, NJ, 089021021"
# map_url = generate_google_maps_url(address)
# print(map_url)
