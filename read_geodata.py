import re
from pykml import parser
from os import path


geodata_file = path.join("raw/Tuscany-subset.kml")

with open(geodata_file) as f:
    geodata = f.read()


pattern = re.compile(r'<Placemark>.*?<name>([0-9]+.*?)</name>.*?<LookAt>.*?<longitude>(.*?)</longitude>.*?<latitude>(.*?)</latitude>.*?</LookAt>.*?</Placemark>', re.DOTALL)
datapoints = re.findall(pattern, geodata)
datapoints.append(("225 Italiano", "12.65", "43.05"))  # manually add coordinates for Standard Italian (from Glottolog)

id_to_site_data = {}

for site, long, lat in datapoints:
    site_info = site.split()
    site_id = site_info[0]
    site_name = " ".join(site_info[1:]).replace("&apos;", "'")

    id_to_site_data[site_id] = {
        "name": site_name,
        "longitude": long,
        "latitude": lat
    }

# validate whether all sites can be matched

sites = []
with open("etc/languages.csv") as f:
    for line in f.read().split("\n"):
        if not line or line.startswith("ID"):
            continue
        sites.append(line.split(","))

assert len(sites) == len(id_to_site_data)

for id, name in sites:
    assert id_to_site_data[id]["name"] == name

# if checks pass, write new data to file
with open("etc/languages.csv", "w") as f:
    f.write("ID,Name,Latitude,Longitude\n")
    for id, data in id_to_site_data.items():
        name = data["name"]
        lat = data["latitude"]
        long = data["longitude"]
        f.write(",".join([id, name, lat, long]) + "\n")
