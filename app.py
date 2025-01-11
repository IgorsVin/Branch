from flask import Flask, render_template, request, jsonify
import requests
import itertools

app = Flask(__name__)

MAPBOX_ACCESS_TOKEN = "pk.eyJ1IjoiaWdvcnN2aW4iLCJhIjoiY20zZXIxMHpwMGhrbTJqcXk5Y3NtZHBqdyJ9.LVhrk96TcH0JyBMZJavc9w"  # Replace with your Mapbox access token

@app.route('/')
def order_page():
    return render_template('order.html')

@app.route('/calculate-route', methods=['POST'])
def calculate_route():
    start_location = request.form['start_location']
    locations = request.form.getlist('locations')

    all_locations = [start_location] + locations + [start_location]
    user_coordinates = get_coordinates(all_locations)
    
    distance_matrix = get_distance_matrix(user_coordinates)

    permutations = itertools.permutations(range(1, len(user_coordinates) - 1))

    best_route = None
    best_distance = float('inf')

    for perm in permutations:
        route = [0] + list(perm) + [0]
        total_distance = calculate_total_distance(route, distance_matrix)

        if total_distance < best_distance:
            best_distance = total_distance
            best_route = route

    optimal_coordinates = [user_coordinates[i] for i in best_route]
    route_geojson = get_route(optimal_coordinates)

    return render_template(
        'map.html',
        route=route_geojson,
        user_coordinates=optimal_coordinates,
        access_token=MAPBOX_ACCESS_TOKEN
    )


def get_coordinates(locations):
    coordinates = []
    for location in locations:
        response = requests.get(
            f'https://api.mapbox.com/geocoding/v5/mapbox.places/{location}.json',
            params={'access_token': MAPBOX_ACCESS_TOKEN}
        )
        data = response.json()
        
        if 'features' in data and len(data['features']) > 0:
            lng, lat = data['features'][0]['center']
            coordinates.append((lng, lat))
        else:
            raise ValueError(f"Could not find coordinates for location: {location}")
    return coordinates

def get_distance_matrix(coordinates):
    num_locations = len(coordinates)
    distance_matrix = [[0] * num_locations for _ in range(num_locations)]

    for i in range(num_locations):
        for j in range(i + 1, num_locations):
            response = requests.get(
                f'https://api.mapbox.com/directions/v5/mapbox/driving/{coordinates[i][0]},{coordinates[i][1]};{coordinates[j][0]},{coordinates[j][1]}',
                params={
                    'access_token': MAPBOX_ACCESS_TOKEN,
                    'geometries': 'geojson'
                }
            )
            data = response.json()

            distance = data['routes'][0]['distance'] / 1000
            
            distance_matrix[i][j] = distance
            distance_matrix[j][i] = distance 
    return distance_matrix


def calculate_total_distance(route, distance_matrix):
    total_distance = 0
    for i in range(len(route) - 1):
        total_distance += distance_matrix[route[i]][route[i + 1]]
    return total_distance

def get_route(coordinates):
    coordinate_str = ';'.join([f'{lng},{lat}' for lng, lat in coordinates])
    response = requests.get(
        f'https://api.mapbox.com/directions/v5/mapbox/driving/{coordinate_str}',
        params={
            'access_token': MAPBOX_ACCESS_TOKEN,
            'geometries': 'geojson'
        }
    )
    data = response.json()
    return data['routes'][0]['geometry']

if __name__ == '__main__':
    app.run(debug=True)
