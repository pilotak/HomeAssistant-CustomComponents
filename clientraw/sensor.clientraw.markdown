The `clientraw` platform is WD Clientraw parser which can read data from your online weather station such a Davis Vantage PRO 2 (tested) and other generating clientraw.txt files

To add clientraw to your installation, add the following to your `configuration.yaml` file:

```yaml
# Example configuration.yaml entry
sensor:
  - platform: clientraw
    url: "http://example.com/clientraw.txt"
    monitored_conditions:
      - temp
      - humidity
```

Configuration variables:

- **url**: full path to clientraw.txt file
- **interval**: poll interval in minutes (1-59), 15 min is default
- **monitored_conditions** array: Conditions to display in the frontend.
  - **dewpoint**: Dewpoint (°C or °F)
  - **heat_index**: Heat index (°C or °F)
  - **temp**: Temperature (°C or °F)
  - **humidex**: Humidex (°C or °F)
  - **wind_degrees**: Where the wind is coming from in degrees, with true north at 0° and progressing clockwise.
  - **wind_dir**: Wind Direction as string ie.: N, NW, etc.
  - **wind_gust**: Wind Gust (km/h or mph)
  - **wind_speed**: Wind Speed (km/h or mph)
  - **symbol**: Symbol
  - **daily_rain**: Daily Rain (mm or in)
  - **pressure**: Pressure (hPa or inHg)
  - **humidity**: Relative humidity (%)
  - **cloud_height**: Cloud Height (m or ft)
  - **forecast**: string based output ie.: night showers

A full configuration example can be found below:

```yaml
# Example configuration.yaml entry
sensor:
  - platform: clientraw
    url: "http://example.com/clientraw.txt"
    interval: 10
    monitored_conditions:
      - dewpoint
      - heat_index
      - temp
      - humidex
      - wind_degrees
      - wind_dir
      - wind_gust
      - wind_speed
      - symbol
      - rain_rate
      - pressure
      - humidity
      - cloud_height
      - forecast
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
