from flask import Flask, request, jsonify
import mysql.connector
import networkx as nx
import osmnx as ox
from geopy.distance import great_circle
import googlemaps
import traceback

app = Flask(__name__)

# Initialize Google Maps client with your API key
gmaps = googlemaps.Client(key='AIzaSyAb3441ZSzyHBhjWdA0_5mh0hsYDOM0oD0')  # Replace with your actual API key

# Define metro stations with coordinates and associated databases
metro_stations = {
    "Ameerpet Metro": (17.435723391979465, 78.44458510250297, "ameerpetmetro"),
    "Secunderabad East Metro": (17.435941421622882, 78.50542839511284, "secondrabadmetro"),
    "MG Bus Station Metro": (17.378494099997923, 78.48570319141346, "mgbsmetro")
}

def find_closest_station(lat, lon):
    closest_station = None
    min_distance = float('inf')
    
    for station, (station_lat, station_lon, db_name) in metro_stations.items():
        distance = great_circle((lat, lon), (station_lat, station_lon)).meters
        if distance < min_distance:
            min_distance = distance
            closest_station = (station, db_name)
    
    return closest_station

@app.route('/get_paths', methods=['GET'])
def get_paths():
    try:
        orig_lat = float(request.args.get('orig_lat'))
        orig_lon = float(request.args.get('orig_lon'))
        dest_lat = float(request.args.get('dest_lat'))
        dest_lon = float(request.args.get('dest_lon'))
        k = int(request.args.get('k', 3))

        # Find nearest metro stations for origin and destination
        orig_station, orig_db = find_closest_station(orig_lat, orig_lon)
        dest_station, dest_db = find_closest_station(dest_lat, dest_lon)

        # Use the database of the nearest origin station
        db_connection = mysql.connector.connect(
            host="127.0.0.1",
            user="root",
            password="admin",
            database=orig_db
        )
        cursor = db_connection.cursor()

        # Fetch node coordinates
        cursor.execute("SELECT node_id, latitude, longitude FROM node_coordinates")
        nodes = cursor.fetchall()

        # Fetch edges with distance and rating
        cursor.execute("SELECT node_a, node_b, distance, rating FROM adjacency_matrix")
        edges = cursor.fetchall()

        cursor.close()
        db_connection.close()

        # Create the graph
        G = nx.Graph()
        for node_id, latitude, longitude in nodes:
            G.add_node(node_id, pos=(latitude, longitude))

        for node_a, node_b, distance, rating in edges:
            G.add_edge(node_a, node_b, weight=distance, rating=rating)

        # Create OSMnx graph from origin point
        G_osmnx = ox.graph_from_point((orig_lat, orig_lon), dist=1000, dist_type='bbox', network_type='walk', simplify=True)

        # Find the nearest nodes in OSMnx graph
        orig_node_osmnx = ox.distance.nearest_nodes(G_osmnx, X=orig_lon, Y=orig_lat)
        dest_node_osmnx = ox.distance.nearest_nodes(G_osmnx, X=dest_lon, Y=dest_lat)

        # Get k shortest paths
        k_shortest_paths_osmnx = list(ox.k_shortest_paths(G_osmnx, orig_node_osmnx, dest_node_osmnx, k, weight='length'))

        paths = []
        for idx, path in enumerate(k_shortest_paths_osmnx):
            path_coords = [(G_osmnx.nodes[node]['y'], G_osmnx.nodes[node]['x']) for node in path]

            # Add origin at the start and destination at the end
            path_coords.insert(0, (orig_lat, orig_lon))  # Add the origin coordinates at the beginning
            path_coords.append((dest_lat, dest_lon))     # Add the destination coordinates at the end

            # Calculate total length and total rating for the current path
            total_length = 0
            total_rating = 0  # This will store sum of (length * rating) for all edges
            
            # Calculate the distance from the origin to the first node in the path using Google Maps API
            first_node_lat, first_node_lon = path_coords[1]  # First node after the origin
            result_origin = gmaps.distance_matrix(
                origins=(orig_lat, orig_lon),
                destinations=(first_node_lat, first_node_lon),
                mode="walking"
            )
            
            # Extract the distance from the API response
            distance_to_first_node = 0
            if result_origin['rows'][0]['elements'][0]['status'] == 'OK':
                distance_to_first_node = result_origin['rows'][0]['elements'][0]['distance']['value']
                total_length += distance_to_first_node

            for u, v in zip(path[:-1], path[1:]):
                # Calculate the length of the edge
                if 'length' in G_osmnx[u][v]:
                    edge_length = G_osmnx[u][v]['length']
                else:
                    coords_u = (G_osmnx.nodes[u]['y'], G_osmnx.nodes[u]['x'])
                    coords_v = (G_osmnx.nodes[v]['y'], G_osmnx.nodes[v]['x'])
                    edge_length = great_circle(coords_u, coords_v).meters

                total_length += edge_length

                # Add the weighted rating for the edge
                if G.has_edge(u, v):
                    edge_rating = G[u][v]['rating']
                    total_rating += edge_length * edge_rating  # Multiply distance by rating

            # Calculate distance from the last node to the destination using Google Maps API
            last_node_lat, last_node_lon = path_coords[-2]  # Last node before the added destination
            result = gmaps.distance_matrix(
                origins=(last_node_lat, last_node_lon),
                destinations=(dest_lat, dest_lon),
                mode="walking"
            )
            
            # Extract the distance from the API response
            additional_distance = 0
            if result['rows'][0]['elements'][0]['status'] == 'OK':
                additional_distance = result['rows'][0]['elements'][0]['distance']['value']
                total_length += additional_distance

            # Calculate final total_rating as weighted average
            if total_length > 0:
                final_total_rating = round(total_rating / (total_length - (additional_distance + distance_to_first_node)) , 2)
            else:
                final_total_rating = 0  # Handle case where total_length is zero

            paths.append({
                'path_number': idx + 1,
                'coordinates': path_coords,
                'total_length_meters': round(total_length,2),
                'total_rating': final_total_rating,  # Use the weighted average rating
                'distance_from_origin_to_first_node_meters': distance_to_first_node,
                'additional_distance_meters': additional_distance
            })

        return jsonify(paths=paths)

    except Exception as e:
        print("An error occurred:", str(e))
        print(traceback.format_exc())
        return jsonify(error=str(e)), 500

if __name__ == '__main__':
    app.run(debug=True)
