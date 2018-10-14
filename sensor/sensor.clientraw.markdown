The `clientraw` platform is WD Clientraw parser which can read data from your online weather station such a Davis Vantage PRO 2 (tested) and other generating clientraw.txt files

To add clientraw to your installation, add the following to your `configuration.yaml` file:

```yaml
# Example configuration.yaml entry
sensor:
  - platform: clientraw
    url: "http://example.com/clientraw.txt"
    monitored_conditions:
      - temp_c
      - humidity
```

Configuration variables:

- **url**: full path to clientraw.txt file
- **interval**: poll interval in minutes (1-59), 15 min is default
- **name**: optional string with the name of the station (if not set --> 'clientraw')
- **monitored_conditions** array: Conditions to display in the frontend.
  - **dewpoint_c**: Dewpoint (°C)
  - **heat_index_c**: Heat index (°C)
  - **temp_c**: Temperature (°C)
  - **humidex_c**: Humidex (°C)
  - **wind_degrees**: Where the wind is coming from in degrees, with true north at 0° and progressing clockwise.
  - **wind_dir**: Wind Direction as string ie.: N, NW, etc.
  - **wind_gust_kph**: Wind Gust (km/h)
  - **wind_gust_mph**: Wind Gust (mph)
  - **wind_kph**: Wind Speed (km/h)
  - **wind_mph**: Wind Speed (mph)
  - **symbol**: Symbol
  - **daily_rain**: Daily Rain (mm)
  - **rain_rate**: Rain Rate (mm)
  - **pressure**: Pressure (hPa)
  - **humidity**: Relative humidity
  - **cloud_height_m**: Cloud Height (m)
  - **cloud_height_ft**: Cloud Height (ft)

A full configuration example can be found below:

```yaml
# Example configuration.yaml entry
sensor:
  - platform: clientraw
    url: "http://example.com/clientraw.txt"
    interval: 10
    name: 'station1'
    monitored_conditions:
      - dewpoint_c
      - heat_index_c
      - temp_c
      - humidex_c
      - wind_degrees
      - wind_dir
      - wind_gust_kph
      - wind_gust_mph
      - wind_kph
      - wind_mph
      - symbol
      - daily_rain
      - rain_rate
      - pressure
      - humidity
      - cloud_height_m
      - cloud_height_ft
```
Symbol codes:
```
0 =  sunny
1 =  clearnight
2 =  cloudy
3 =  cloudy2
4 =  night cloudy
5 =  dry
6 =  fog
7 =  haze
8 =  heavyrain
9 =  mainlyfine
10 = mist
11 = night fog
12 = night heavyrain
13 = night overcast
14 = night rain
15 = night showers
16 = night snow
17 = night thunder
18 = overcast
19 = partlycloudy
20 = rain
21 = rain2
22 = showers2
23 = sleet
24 = sleetshowers
25 = snow
26 = snowmelt
27 = snowshowers2
28 = sunny
29 = thundershowers
30 = thundershowers2
31 = thunderstorms
32 = tornado
33 = windy
34 = stopped rainning
35 = wind + rain
```
