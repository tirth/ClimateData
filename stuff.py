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

# station info column names
STATION_NAME = 'Name'
STATION_ID = 'Station ID'
STATION_LATITUDE = 'Latitude (Decimal Degrees)'
STATION_LONGITUDE = 'Longitude (Decimal Degrees)'
STATION_FY = 'First Year'
STATION_LY = 'Last Year'
STATION_HLY_FY = 'HLY First Year'
STATION_HLY_LY = 'HLY Last Year'
STATION_DLY_FY = 'DLY First Year'
STATION_DLY_LY = 'DLY Last Year'
STATION_MLY_FY = 'MLY First Year'
STATION_MLY_LY = 'MLY Last Year'

# data column names
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
        s_lat = radians(float(STATION_INFO[station][STATION_LATITUDE]))
        s_long = radians(float(STATION_INFO[station][STATION_LONGITUDE]))

        # haversine
        d = sin((s_lat - lat) / 2) ** 2 + cos(lat) * cos(s_lat) * sin((s_long - long) / 2) ** 2
        h = 2 * AVG_EARTH_RADIUS * asin(sqrt(d))

        if h <= distance:
            stations.append(station)

    return stations


def station_dates(station_name: str):
    info = STATION_INFO[station_name]

    monthly_range = range(0)
    if info[STATION_MLY_FY] != '':
        monthly_range = range(int(info[STATION_MLY_FY]), int(info[STATION_MLY_LY]) + 1)

    daily_range = range(0)
    if info[STATION_DLY_FY] != '':
        daily_range = range(int(info[STATION_DLY_FY]), int(info[STATION_DLY_LY]) + 1)

    hourly_range = range(0)
    if info[STATION_HLY_FY] != '':
        hourly_range = range(int(info[STATION_HLY_FY]), int(info[STATION_HLY_LY]) + 1)

    dates = {}
    for year in range(int(info[STATION_FY]), int(info[STATION_LY]) + 1):
        if year in monthly_range:
            dates[year] = 'monthly'
        elif year in daily_range:
            dates[year] = 'daily'
        elif year in hourly_range:
            dates[year] = 'hourly'
        else:
            dates[year] = 'nope'

    return dates


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


def get_monthly_data(station):
    r = requests.get((bulk_data(STATION_INFO[station][STATION_ID], 1970, 1, TIMEFRAMES['monthly'])))

    return data_rows(r.text) if r.status_code == 200 else []


def get_daily_data(station: str, year: int):
    r = requests.get((bulk_data(STATION_INFO[station][STATION_ID], year, 1, TIMEFRAMES['daily'])))

    return data_rows(r.text) if r.status_code == 200 else []


def get_hourly_data(station: str, year: int, month: int):
    r = requests.get((bulk_data(STATION_INFO[station][STATION_ID], year, month, TIMEFRAMES['hourly'])))

    return data_rows(r.text) if r.status_code == 200 else []


def get_data(station, dates):
    print('data for', station)

    temp_data, precip_data = {}, {}

    # if 'monthly' in dates.values():
    #     monthly_data = get_monthly_data(station)
    #
    #     for record in monthly_data:
    #         temp_data[record[DATE_TIME_TITLE]] = get_temp(record)
    #         precip_data[record[DATE_TIME_TITLE]] = get_precip(record)

    if 'daily' in dates.values():
        for year in dates:
            if dates[year] != 'daily':
                continue

            daily_data = get_daily_data(station, year)
            daily_temps = {}
            for record in daily_data:
                daily_temps[record[DATE_TIME_TITLE]] = get_temp(record)

            # average by month
            for month in range(1, 13):
                pass

            print(len(daily_temps))

    return temp_data, precip_data


def go():
    get_station_inventory()

    stations = stations_by_proximity(44, -79)
    print('found', len(stations))

    for station in stations:
        if station == 'BLACKSTOCK':
            dates = station_dates(station)
            temp_data, precip_data = get_data(station, dates)
            print(len(temp_data))


if __name__ == '__main__':
    go()
    print('done')
