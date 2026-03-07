# This is a sample Python script.

# Press Maj+F10 to execute it or replace it with your code.
# Press Double Shift to search everywhere for classes, files, tool windows, actions, and settings.

import math
from time import sleep
from skyfield.api import EarthSatellite, Topos, load
import requests
import gpsd
import RPi.GPIO as GPIO


class Satellite:
    def __init__(self):
        #self.api = 'https://api.wheretheiss.at/v1/satellites/25544'
        self.R = 6371000

        self.tle_api = None
        self.latitude = None
        self.longitude = None
        self.speed = None
        self.altitude = None
        self.azimut = None
        self.elevation = None
        self.distance = None
        self.satellite = None


    def set_tle_api(self, tle):
        self.tle_api = tle
        self._load_tle()
        return self

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
                self.tle = {
                    'name': data['name'],
                    'line1': data['line1'],
                    'line2': data['line2']
                }
                print(f"[+] TLE chargé : {self.tle['name']}")
            else:
                print(f"Erreur API TLE : status {response.status_code}")
        except Exception as e:
            print(f"Erreur chargement TLE : {e}")

    def get_position(self, seconds=0):
        """Retourne la position projetée de l'ISS dans `seconds` secondes"""

        ts = load.timescale()
        self.satellite = EarthSatellite(self.tle['line1'], self.tle['line2'], self.tle['name'], ts)

        t_future = ts.now() + seconds / 86400.0
        geo = self.satellite.at(t_future)
        subpoint = geo.subpoint()

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
        return self.azimut

    def get_elevation(self, lat1, lon1, altitude):
        d = self.get_distance(lat1, lon1)
        courbure_hauteur = (math.pow(d, 2)) / (2 * self.R)
        delta_hauteur = (self.altitude - altitude) - courbure_hauteur
        hauteur_radian = math.atan(delta_hauteur / d)
        self.elevation = math.degrees(hauteur_radian)
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
                print("Position actuelle acquise")
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

class DRV8825:
    def __init__(self, dir_pin, step_pin, enable_pin, mode_pins):
        self.dir_pin = dir_pin
        self.step_pin = step_pin
        self.enable_pin = enable_pin
        self.mode_pins = mode_pins
        self.MotorDir = ['forward', 'backward' ]
        self.ControlMode = ['hardward', 'softward' ]

        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        GPIO.setup(self.dir_pin, GPIO.OUT)
        GPIO.setup(self.step_pin, GPIO.OUT)
        GPIO.setup(self.enable_pin, GPIO.OUT)
        GPIO.setup(self.mode_pins, GPIO.OUT)

    def digital_write(self, pin, value):
        GPIO.output(pin, value)

    def Stop(self):
        print("Stop motor")
        self.digital_write(self.enable_pin, 0)
        GPIO.cleanup()

    def SetMicroStep(self, mode, stepformat):
        """
        (1) mode
            'hardward' :    Use the switch on the module to control the microstep
            'software' :    Use software to control microstep pin levels
                Need to put the All switch to 0
        (2) stepformat
            ('fullstep', 'halfstep', '1/4step', '1/8step', '1/16step', '1/32step')
        """
        microstep = {
            'fullstep': (0, 0, 0),
			'halfstep': (1, 0, 0),
			'1/4step': (0, 1, 0),
			'1/8step': (1, 1, 0),
			'1/16step': (0, 0, 1),
			'1/32step': (1, 0, 1)
        }

        print("Control mode:", mode)
        if mode == self.ControlMode[1]:
            print("set pins")
            self.digital_write(self.mode_pins, microstep[stepformat])

    def TurnStep(self, Dir, steps, stepdelay: float =0.005):
        if Dir == self.MotorDir[0]:
            print("forward")
            self.digital_write(self.enable_pin, 1)
            self.digital_write(self.dir_pin, 0)
        elif Dir == self.MotorDir[1]:
            print("backward")
            self.digital_write(self.enable_pin, 1)
            self.digital_write(self.dir_pin, 1)
        else:
            print("the dir must be : 'forward' or 'backward'")
            self.digital_write(self.enable_pin, 0)
            return

        if steps == 0:
            return

        print("turn step:", steps)
        for i in range(steps):
            self.digital_write(self.step_pin, True)
            sleep(stepdelay)
            self.digital_write(self.step_pin, False)
            sleep(stepdelay)

class Motor(DRV8825):
    def __init__(self, dir_pin: int, step_pin: int, enable_pin: int, mode_pins: tuple, steps: int = 200):
        super().__init__(dir_pin, step_pin, enable_pin, mode_pins)
        self.steps = steps
        self.steps_degree = float(360 / self.steps)
        self.current_angle = 0.0  # Angle actuel en degrés
        self.cumulative_delta = 0.0  # Pour cumuler les deltas trop petits


    def move_to_angle(self, target_angle: float):
        """
        Déplacer le moteur à l'angle cible (en degrés).
        Calcule le delta et ajuste le nombre de steps.
        """
        # Normaliser l'angle cible entre 0° et 360°
        target_angle = target_angle % 360
        # Calculer le delta entre l'angle cible et l'angle actuel
        delta = self.current_angle - target_angle
        # Ajouter le delta cumulé précédent
        self.cumulative_delta += abs(delta)
        # Calculer le nombre de steps nécessaires
        #steps_needed = abs(self.cumulative_delta / self.steps_degree)
        # Mettre à jour le delta cumulé
        #self.cumulative_delta = delta - (steps_needed * self.steps_degree)


        if self.cumulative_delta >= self.steps_degree:
            direction = 'forward' if delta < 0 else 'backward'
            self.TurnStep(direction, int(round(self.cumulative_delta / self.steps_degree)))
            self.cumulative_delta = 0.0
            print(f"Moteur déplacé à {target_angle:.2f}°.")
        else:
            print(f"Delta trop petit ({self.cumulative_delta:.2f}°), cumulé pour le prochain mouvement.")

        self.current_angle = target_angle

    def get_current_angle(self) -> float:
        """Retourne l'angle actuel du moteur."""
        return self.current_angle

#gps = GPS()
#current_position = gps.get_position()
lat_src, long_src, haut_src = float(48.85), float(2.34), float(0)
iss = Satellite()
iss.set_tle_api('https://tle.ivanstanojevic.me/api/tle/25544')


#azimut_motor = DRV8825(dir_pin=13, step_pin=19, enable_pin=12, mode_pins=(16, 17, 20))
azimut_motor = Motor(steps=200, dir_pin=24, step_pin=18, enable_pin=4, mode_pins=(21, 22, 27))

try:
    while True:
        iss.get_position(0)
        azimut = iss.get_azimut(lat_src, long_src)
        print("ISS: ", azimut)
        azimut_motor.move_to_angle(azimut)
        print("######################")
        sleep(1)
except KeyboardInterrupt:
    azimut_motor.Stop()
    exit(0)
