#########################################################################::API Sample::#########################################################################################################################

Assume you want to find the 3 shortest paths from origin (17.4357, 78.4446) to destination (17.3785, 78.4857). The request URL would be:
http://127.0.0.1:5000/get_paths?orig_lat=17.4357&orig_lon=78.4446&dest_lat=17.3785&dest_lon=78.4857&k=3


#########################################################################::Sample Response::#########################################################################################################################

The API will return a JSON object containing an array of paths, each with details like coordinates, total length, total rating, and distance metrics. A sample response might look like this:
{
  "paths": [
    {
      "path_number": 1,
      "coordinates": [[17.4357, 78.4446], ... , [17.3785, 78.4857]],
      "total_length_meters": 1200.5,
      "total_rating": 4.3,
      "distance_from_origin_to_first_node_meters": 85,
      "additional_distance_meters": 75
    },
    {
      "path_number": 2,
      "coordinates": [[17.4357, 78.4446], ... , [17.3785, 78.4857]],
      "total_length_meters": 1305.7,
      "total_rating": 3.9,
      "distance_from_origin_to_first_node_meters": 90,
      "additional_distance_meters": 80
    }
  ]
}
