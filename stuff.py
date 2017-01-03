import os
from math import radians, cos, sin, asin, sqrt
from urllib import request
import csv
import requests

STATION_INV_FILENAME = 'Station Inventory.csv'
STATION_INV_FTP = 'ftp://client_climate@ftp.tor.ec.gc.ca/Pub/Get_More_Data_Plus_de_donnees/Station%20Inventory%20EN.csv'
STATION_INFO = {}
TIMEFRAMES = {'hourly': 1, 'daily': 2, 'monthly': 3}
AVG_EARTH_RADIUS = 6371  # km

DATE_TIME_TITLE = 'Date/Time'
TEMP_TITLE = 'Temp (°C)'
MEAN_TEMP_TITLE = 'Mean Temp (°C)'
TOTAL_PRECIP_TITLE = 'Total Precip (mm)'


def get_station_inventory():
    if not os.path.isfile(STATION_INV_FILENAME):
        print('getting station inventory')
        request.urlretrieve(STATION_INV_FTP, STATION_INV_FILENAME)

    with open(STATION_INV_FILENAME, encoding='utf8') as stations_file:
        modified_date = stations_file.readline().strip()
        print(modified_date)

        # skip disclaimers
        for _ in range(2):
            stations_file.readline()

        global STATION_INFO
        STATION_INFO = {station['Name']: station for station in csv.DictReader(stations_file)}


def stations_by_proximity(lat: float, long: float, distance=25):
    stations = []
    lat, long = map(radians, (lat, long))

    for station in STATION_INFO:
        s_lat = radians(float(STATION_INFO[station]['Latitude (Decimal Degrees)']))
        s_long = radians(float(STATION_INFO[station]['Longitude (Decimal Degrees)']))

        # haversine
        d = sin((s_lat - lat) / 2) ** 2 + cos(lat) * cos(s_lat) * sin((s_long - long) / 2) ** 2
        h = 2 * AVG_EARTH_RADIUS * asin(sqrt(d))

        if h <= distance:
            stations.append(station)

    return stations


def station_dates(station_name: str):
    info = STATION_INFO[station_name]
    first_year, last_year = info['First Year'], info['Last Year']
    hourly_fy, hourly_ly = info['HLY First Year'], info['HLY Last Year']
    daily_fy, daily_ly = info['DLY First Year'], info['DLY Last Year']
    monthly_fy, monthly_ly = info['MLY First Year'], info['MLY Last Year']

    print(station_name, first_year, last_year)
    print('hourly', hourly_fy, hourly_ly)
    print('daily', daily_fy, daily_ly)
    print('monthly', monthly_fy, monthly_ly)

    if monthly_fy == '' or monthly_fy > first_year:
        print('gotta check earlier daily')
        if daily_fy == '' or daily_fy > first_year:
            print('gotta check earlier hourly')

    if monthly_ly == '' or monthly_ly < last_year:
        print('gotta check later daily')
        if daily_ly == '' or daily_ly < last_year:
            print('gotta check later hourly')

    print()


def full_monthly(station_name):
    info = STATION_INFO[station_name]
    return info['MLY First Year'] == info['First Year'] and info['MLY Last Year'] == info['Last Year']


def full_daily(station_name):
    info = STATION_INFO[station_name]
    return info['DLY First Year'] == info['First Year'] and info['DLY Last Year'] == info['Last Year']


# timeframes: monthly -> all data, daily -> full year, hourly -> full month
def bulk_data(station_id, year, month, timeframe):
    return 'http://climate.weather.gc.ca/climate_data/bulk_data_e.html?format=csv&' \
           f'stationID={station_id}&' \
           f'Year={year}&' \
           f'Month={month}&' \
           f'Day={1}&' \
           f'timeframe={timeframe}&' \
           'submit=Download+Data'


def data_rows(response_text: str):
    all_data = response_text.split('\n')

    # remove extraneous info
    current = all_data[0]
    while DATE_TIME_TITLE not in current:
        all_data.remove(current)
        current = all_data[0]

    return csv.DictReader(all_data)


def get_temp(record):
    temp = None

    if TEMP_TITLE in record:
        temp = record[TEMP_TITLE]
    elif MEAN_TEMP_TITLE in record:
        temp = record[MEAN_TEMP_TITLE]

    return temp if temp != '' else None


def get_precip(record):
    precip = None

    if TOTAL_PRECIP_TITLE in record:
        precip = record[TOTAL_PRECIP_TITLE]

    return precip if precip != '' else None


def get_data(station):
    r = requests.get((bulk_data(STATION_INFO[station]['Station ID'], 1970, 1, TIMEFRAMES['monthly'])))

    if r.status_code != 200:
        print('nope')
        return

    temp_data, precip_data = {}, {}

    for record in data_rows(r.text):
        temp_data[record[DATE_TIME_TITLE]] = get_temp(record)
        precip_data[record[DATE_TIME_TITLE]] = get_precip(record)

    return temp_data, precip_data


def go():
    get_station_inventory()

    stations = stations_by_proximity(44, -79)
    print('found', len(stations))

    for station in stations:
        station_dates(station)
        # temp_data, precip_data = get_data(station)


if __name__ == '__main__':
    go()
    print('done')
