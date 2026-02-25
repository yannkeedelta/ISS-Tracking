# This is a sample Python script.

# Press Maj+F10 to execute it or replace it with your code.
# Press Double Shift to search everywhere for classes, files, tool windows, actions, and settings.

import math
from http.client import responses
from time import sleep
from skyfield.api import EarthSatellite, Topos, load
import requests
from pprint import pprint
import gpsd
import urllib.request
import json

from skyfield.elementslib import semi_major_axis


class ISS:
    def __init__(self):
        self.api = 'https://api.wheretheiss.at/v1/satellites/25544'
        self.tle_api = 'https://tle.ivanstanojevic.me/api/tle/25544'
        self.R = 6371000

        self.latitude = None
        self.longitude = None
        self.speed = None
        self.altitude = None
        self.azimut = None
        self.elevation = None
        self.distance = None
        self.satellite = None

        self._load_tle()


    def _load_tle(self):
        """Charge les TLE depuis l'API ivanstanojevic"""
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
            response = requests.get(
                self.tle_api,
                headers=headers,
                timeout=5
            )
            if response.status_code == 200:
                data = response.json()
                name = data['name']
                self.tle = {
                    'name': data['name'],
                    'line1': data['line1'],
                    'line2': data['line2']
                }
                print(f"TLE chargé : {name}")
            else:
                print(f"Erreur API TLE : status {response.status_code}")
        except Exception as e:
            print(f"Erreur chargement TLE : {e}")

    def get_position(self, seconds=10):
        """Retourne la position projetée de l'ISS dans `seconds` secondes"""

        ts = load.timescale()
        self.satellite = EarthSatellite(self.tle['line1'], self.tle['line2'], self.tle['name'], ts)


        t_future = ts.now() + seconds / 86400.0
        geo = self.satellite.at(t_future)
        subpoint = geo.subpoint()

        if seconds == 0:
            self.latitude = float(subpoint.latitude.degrees)
            self.longitude = float(subpoint.longitude.degrees)
            self.altitude = float(subpoint.elevation.km)

        return (
            float(subpoint.latitude.degrees),
            float(subpoint.longitude.degrees),
            float(subpoint.elevation.km)
        )

    def get_iss(self):
        print("########### Get API ISS Loc ##############")
        response = requests.get(self.api)
        if response.status_code == 200:
            data = response.json()
            self.latitude = float(data['latitude'])
            self.longitude = float(data['longitude'])
            self.altitude = float(data['altitude'])
            self.speed = float(data['velocity']) * 3.6

            return (
                self.latitude,
                self.longitude,
                self.altitude,
                self.speed
            )
        else:
            return False

    def get_azimut(self, lat1, lon1):
        phi1 = math.radians(lat1)
        phi2 = math.radians(self.latitude)
        delta_lambda = math.radians(self.longitude - lon1)

        y_val = math.sin(delta_lambda) * math.cos(phi2)
        x_val = math.cos(phi1) * math.sin(phi2) - math.sin(phi1) * math.cos(phi2) * math.cos(delta_lambda)

        azimut_rad = math.atan2(y_val, x_val)
        azimut_deg = math.degrees(azimut_rad)

        self.azimut = (azimut_deg + 360) % 360
        print("Azimut: {:.2f}".format(self.azimut))
        return self.azimut

    def get_elevation(self, lat1, lon1, altitude):
        d = self.get_distance(lat1, lon1)
        courbure_hauteur = (math.pow(d, 2)) / (2 * self.R)
        delta_hauteur = (self.altitude - altitude) - courbure_hauteur
        hauteur_radian = math.atan(delta_hauteur / d)
        self.elevation = math.degrees(hauteur_radian)
        print("Elevation: {:.2f}".format(self.elevation))
        return self.elevation

    def get_distance(self, lat1, lon1):
        # Conversion degrés -> radians
        phi1 = math.radians(lat1)
        phi2 = math.radians(self.latitude)
        delta_phi = math.radians(self.latitude - lat1)
        delta_lambda = math.radians(self.longitude - lon1)

        a = (math.sin(delta_phi / 2) ** 2 +
             math.cos(phi1) * math.cos(phi2) *
             math.sin(delta_lambda / 2) ** 2)

        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        self.distance = self.R * c

        return self.distance


class GPS:
    def __init__(self):
        self.latitude = None
        self.longitude = None
        self.altitude = None

        try:
            gpsd.connect()
            print("Connexion à gpsd réussie")
        except Exception as e:
            print(f"Impossible de se connecter à gpsd : {e}")
            print("Vérifiez que gpsd est lancé : sudo gpsd /dev/ttyUSB0 -F /var/run/gpsd.sock")
            return

        self.read_position()

    def read_position(self):
        try:
            packet = gpsd.get_current()
            if packet.mode >= 2:  # 2 = fix 2D, 3 = fix 3D
                self.latitude = packet.lat
                self.longitude = packet.lon
                self.altitude = packet.alt if packet.mode == 3 else None
            else:
                print("En attente de fix GPS...")
                sleep(1)
                self.read_position()
        except Exception as e:
            print(f"Erreur de lecture : {e}")

    def get_position(self):
        """Retourne la dernière position connue"""
        return self.latitude, self.longitude, self.altitude


#gps = GPS()
#current_position = gps.get_position()
lat_src, long_src, haut_src = float(48.85), float(2.34), float(0)
iss = ISS()

while True:
    iss.get_position(0)
    iss.get_azimut(lat_src, long_src)
    iss.get_elevation(lat_src, long_src, haut_src)
    sleep(1)


# Press the green button in the gutter to run the script.
# if __name__ == '__main__':
#     print_hi('PyCharm')

# See PyCharm help at https://www.jetbrains.com/help/pycharm/
