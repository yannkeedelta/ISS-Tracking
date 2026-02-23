# This is a sample Python script.

# Press Maj+F10 to execute it or replace it with your code.
# Press Double Shift to search everywhere for classes, files, tool windows, actions, and settings.

import math
from time import sleep
import requests
import gpsd


class ISS:
    def __init__(self):
        self.api = 'https://api.wheretheiss.at/v1/satellites/25544'
        self.latitude = None
        self.longitude = None
        self.speed = None
        self.altitude = None
        self.azimut = None
        self.elevation = None
        self.distance = None
        self.R = 6371000


    def get_iss(self):
        print("########### Get API ISS Loc ##############")
        response = requests.get(self.api)
        if response.status_code == 200:
            data = response.json()
            self.latitude = float(data['latitude'])
            self.longitude = float(data['longitude'])
            self.altitude = float(data['altitude'])
            self.speed = float(data['velocity']) * 3.6

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

    def projection_gps(self, temps):
        lat = math.radians(self.latitude)
        lon = math.radians(self.longitude)
        azimut = math.radians(self.azimut)

        d = self.speed * temps

        # nouvelle latitude
        lat2 = math.asin(
            math.sin(lat) * math.cos(d / self.R) +
            math.cos(lat) * math.sin(d / self.R) * math.cos(azimut)
        )

        # nouvelle longitude
        lon2 = lon + math.atan2(
            math.sin(azimut) * math.sin(d / self.R) * math.cos(lat),
            math.cos(d / self.R) - math.sin(lat) * math.sin(lat2)
        )

        self.latitude = math.degrees(lat2)
        self.longitude = math.degrees(lon2)

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


gps = GPS()
current_position = gps.get_position()
lat_src, long_src, haut_src = float(current_position[0]), float(current_position[1]), float(current_position[2])
iss = ISS()

while True:
    #ISS.projection_gps(1)
    sleep(1)
    iss.get_iss()
    iss.get_azimut(lat_src, long_src)
    iss.get_elevation(lat_src, long_src, haut_src)


# Press the green button in the gutter to run the script.
# if __name__ == '__main__':
#     print_hi('PyCharm')

# See PyCharm help at https://www.jetbrains.com/help/pycharm/
