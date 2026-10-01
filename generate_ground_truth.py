import csv
import re

# Comprehensive extraction of all observations from Photos of observations (Pages 1 to 8 + Sticky Notes)
raw_entries = [
    # Page 1 (IMG_8050.jpeg)
    {"page": 1, "date": "2021-05-29", "time": "", "time_qualifier": "", "ware_stage": 5.10, "depth": 14.0, "wind_dir": "", "wind_spd": "", "wind_gust": "", "weather": "", "astro": "", "notes": ""},
    {"page": 1, "date": "2021-07-08", "time": "", "time_qualifier": "", "ware_stage": 4.45, "depth": 8.0, "wind_dir": "NNE", "wind_spd": "20", "wind_gust": "", "weather": "", "astro": "", "notes": "20 NNE"},
    {"page": 1, "date": "2021-10-06", "time": "", "time_qualifier": "", "ware_stage": 4.44, "depth": 6.0, "wind_dir": "", "wind_spd": "", "wind_gust": "", "weather": "", "astro": "", "notes": ""},
    {"page": 1, "date": "2021-10-07", "time": "", "time_qualifier": "", "ware_stage": 4.58, "depth": 7.0, "wind_dir": "", "wind_spd": "", "wind_gust": "", "weather": "", "astro": "", "notes": ""},
    {"page": 1, "date": "2021-10-08", "time": "", "time_qualifier": "", "ware_stage": 4.10, "depth": 3.0, "wind_dir": "", "wind_spd": "", "wind_gust": "", "weather": "", "astro": "", "notes": ""},
    {"page": 1, "date": "2021-10-09", "time": "", "time_qualifier": "", "ware_stage": 4.30, "depth": 6.0, "wind_dir": "NNE", "wind_spd": "4.6", "wind_gust": "", "weather": "", "astro": "", "notes": "4.6 NNE"},
    {"page": 1, "date": "2021-10-10", "time": "", "time_qualifier": "", "ware_stage": 4.75, "depth": 10.0, "wind_dir": "NNE", "wind_spd": "10-20", "wind_gust": "", "weather": "", "astro": "", "notes": "10-20 NNE"},
    {"page": 1, "date": "2021-10-11", "time": "", "time_qualifier": "", "ware_stage": 4.80, "depth": 9.0, "wind_dir": "NNW", "wind_spd": "16", "wind_gust": "", "weather": "", "astro": "", "notes": "16 NNW"},
    {"page": 1, "date": "2021-10-12", "time": "", "time_qualifier": "", "ware_stage": 4.20, "depth": 2.0, "wind_dir": "N", "wind_spd": "25", "wind_gust": "", "weather": "", "astro": "", "notes": "25 N"},
    {"page": 1, "date": "2021-10-16", "time": "", "time_qualifier": "", "ware_stage": 4.22, "depth": 4.0, "wind_dir": "NNW", "wind_spd": "20", "wind_gust": "", "weather": "", "astro": "", "notes": "20 NNW"},
    {"page": 1, "date": "2021-10-28", "time": "", "time_qualifier": "", "ware_stage": 4.58, "depth": 7.0, "wind_dir": "E", "wind_spd": "", "wind_gust": "", "weather": "", "astro": "", "notes": "E"},
    {"page": 1, "date": "2021-10-28", "time": "", "time_qualifier": "", "ware_stage": 4.77, "depth": 10.0, "wind_dir": "E", "wind_spd": "", "wind_gust": "", "weather": "", "astro": "", "notes": "E"},
    {"page": 1, "date": "2021-10-28", "time": "", "time_qualifier": "", "ware_stage": 4.87, "depth": 5.0, "wind_dir": "ESE", "wind_spd": "", "wind_gust": "", "weather": "", "astro": "", "notes": "ESE"},
    {"page": 1, "date": "2021-10-30", "time": "", "time_qualifier": "", "ware_stage": 3.80, "depth": 0.5, "wind_dir": "ESE-SE", "wind_spd": "", "wind_gust": "", "weather": "", "astro": "", "notes": "ESE to SE"},
    {"page": 1, "date": "2021-10-30", "time": "", "time_qualifier": "", "ware_stage": 4.20, "depth": 2.0, "wind_dir": "SE", "wind_spd": "24", "wind_gust": "", "weather": "", "astro": "", "notes": "SE 24"},
    {"page": 1, "date": "2021-12-31", "time": "", "time_qualifier": "", "ware_stage": 3.87, "depth": 0.0, "wind_dir": "", "wind_spd": "", "wind_gust": "", "weather": "", "astro": "", "notes": ""},
    {"page": 1, "date": "2022-01-03", "time": "", "time_qualifier": "", "ware_stage": 5.22, "depth": 11.0, "wind_dir": "N", "wind_spd": "", "wind_gust": "", "weather": "Snow", "astro": "", "notes": "11 SNOW N"},
    {"page": 1, "date": "2022-01-04", "time": "", "time_qualifier": "", "ware_stage": 4.10, "depth": 1.5, "wind_dir": "N", "wind_spd": "9.2", "wind_gust": "", "weather": "", "astro": "", "notes": "N 9.2"},
    {"page": 1, "date": "2022-01-16", "time": "", "time_qualifier": "", "ware_stage": 4.80, "depth": 8.0, "wind_dir": "ESE", "wind_spd": "19-25", "wind_gust": "", "weather": "", "astro": "", "notes": "ESE 19-25"},

    # Page 2 (IMG_8051.jpeg)
    {"page": 2, "date": "2022-05-08", "time": "", "time_qualifier": "", "ware_stage": 4.72, "depth": 8.0, "wind_dir": "", "wind_spd": "", "wind_gust": "", "weather": "", "astro": "", "notes": ""},
    {"page": 2, "date": "2022-05-09", "time": "", "time_qualifier": "", "ware_stage": 4.50, "depth": 6.0, "wind_dir": "", "wind_spd": "", "wind_gust": "", "weather": "", "astro": "", "notes": ""},
    {"page": 2, "date": "2022-05-10", "time": "", "time_qualifier": "", "ware_stage": 5.02, "depth": 12.0, "wind_dir": "NNE", "wind_spd": "10-21", "wind_gust": "", "weather": "", "astro": "", "notes": "NNE 10-21"},
    {"page": 2, "date": "2022-05-11", "time": "", "time_qualifier": "", "ware_stage": 4.10, "depth": 6.0, "wind_dir": "NNE", "wind_spd": "16", "wind_gust": "", "weather": "", "astro": "", "notes": "NNE 16"},
    {"page": 2, "date": "2022-06-14", "time": "", "time_qualifier": "", "ware_stage": 4.13, "depth": 0.5, "wind_dir": "", "wind_spd": "", "wind_gust": "", "weather": "", "astro": "", "notes": ""},
    {"page": 2, "date": "2022-09-07", "time": "", "time_qualifier": "", "ware_stage": 4.33, "depth": 1.5, "wind_dir": "NE", "wind_spd": "17", "wind_gust": "", "weather": "Hurricane Earl", "astro": "", "notes": "Hurricane Earl; NE 17"},
    {"page": 2, "date": "2022-09-08", "time": "", "time_qualifier": "", "ware_stage": 4.82, "depth": 10.0, "wind_dir": "", "wind_spd": "", "wind_gust": "", "weather": "Hurricane Earl", "astro": "", "notes": "Hurricane Earl"},
    {"page": 2, "date": "2022-09-08", "time": "", "time_qualifier": "", "ware_stage": 4.39, "depth": 3.25, "wind_dir": "NNE", "wind_spd": "8", "wind_gust": "", "weather": "Hurricane Earl", "astro": "", "notes": "Hurricane Earl; NNE 8"},
    {"page": 2, "date": "2022-09-09", "time": "", "time_qualifier": "", "ware_stage": 4.30, "depth": 2.5, "wind_dir": "", "wind_spd": "", "wind_gust": "", "weather": "Hurricane Earl", "astro": "", "notes": "Hurricane Earl"},
    {"page": 2, "date": "2022-09-09", "time": "", "time_qualifier": "", "ware_stage": 4.60, "depth": 8.0, "wind_dir": "NNE", "wind_spd": "5.7", "wind_gust": "", "weather": "Hurricane Earl", "astro": "", "notes": "Hurricane Earl; NNE 5.7"},
    {"page": 2, "date": "2022-09-10", "time": "", "time_qualifier": "", "ware_stage": 4.20, "depth": 0.5, "wind_dir": "NNE", "wind_spd": "8.1", "wind_gust": "", "weather": "Hurricane Earl", "astro": "", "notes": "Hurricane Earl; NNE 8.1"},
    {"page": 2, "date": "2022-09-10", "time": "", "time_qualifier": "", "ware_stage": 4.20, "depth": 0.5, "wind_dir": "SSE", "wind_spd": "6.9", "wind_gust": "", "weather": "Hurricane Earl", "astro": "", "notes": "Hurricane Earl; SSE 6.9"},
    {"page": 2, "date": "2022-09-30", "time": "", "time_qualifier": "", "ware_stage": 4.66, "depth": 7.0, "wind_dir": "N", "wind_spd": "12-24", "wind_gust": "", "weather": "Hurricane Ian", "astro": "", "notes": "Hurricane Ian; N 12-24"},
    {"page": 2, "date": "2022-10-01", "time": "", "time_qualifier": "", "ware_stage": 4.50, "depth": 5.0, "wind_dir": "NNW", "wind_spd": "17-25", "wind_gust": "", "weather": "Hurricane Ian", "astro": "", "notes": "Hurricane Ian; NNW 17-25"},
    {"page": 2, "date": "2022-10-03", "time": "", "time_qualifier": "", "ware_stage": 4.25, "depth": 1.0, "wind_dir": "NW", "wind_spd": "12-18", "wind_gust": "", "weather": "Hurricane Ian", "astro": "", "notes": "Hurricane Ian; NW 12-18"},
    {"page": 2, "date": "2022-11-07", "time": "", "time_qualifier": "", "ware_stage": 4.25, "depth": 2.0, "wind_dir": "SSW", "wind_spd": "20", "wind_gust": "", "weather": "", "astro": "", "notes": "SSW 20"},
    {"page": 2, "date": "2023-03-12", "time": "", "time_qualifier": "", "ware_stage": 4.30, "depth": 4.0, "wind_dir": "NNE", "wind_spd": "4.3", "wind_gust": "", "weather": "SC Low", "astro": "", "notes": "NNE 4.3; SC Low"},
    {"page": 2, "date": "2023-03-14", "time": "", "time_qualifier": "", "ware_stage": 4.30, "depth": 4.0, "wind_dir": "NW", "wind_spd": "17", "wind_gust": "", "weather": "SC Low", "astro": "", "notes": "NW 17; SC Low"},

    # Page 3 (IMG_8052.jpeg)
    {"page": 3, "date": "2023-03-13", "time": "", "time_qualifier": "", "ware_stage": 4.30, "depth": 4.0, "wind_dir": "", "wind_spd": "", "wind_gust": "", "weather": "NC/VA Low", "astro": "", "notes": "NC/va Low"},
    {"page": 3, "date": "2023-03-13", "time": "", "time_qualifier": "", "ware_stage": 4.33, "depth": 4.0, "wind_dir": "", "wind_spd": "", "wind_gust": "", "weather": "", "astro": "", "notes": ""},
    {"page": 3, "date": "2023-04-30", "time": "", "time_qualifier": "", "ware_stage": 3.94, "depth": 0.0, "wind_dir": "", "wind_spd": "", "wind_gust": "", "weather": "", "astro": "", "notes": "No flood recorded"},

    # Page 4 (IMG_8053.jpeg)
    {"page": 4, "date": "2023-06-02", "time": "", "time_qualifier": "", "ware_stage": 4.38, "depth": 3.0, "wind_dir": "ENE", "wind_spd": "12.8", "wind_gust": "", "weather": "", "astro": "", "notes": "ENE 12.8"},
    {"page": 4, "date": "2023-06-03", "time": "", "time_qualifier": "", "ware_stage": 4.61, "depth": 7.5, "wind_dir": "", "wind_spd": "", "wind_gust": "", "weather": "", "astro": "Full moon", "notes": "Full moon"},
    {"page": 4, "date": "2023-06-05", "time": "", "time_qualifier": "", "ware_stage": 4.20, "depth": 0.0, "wind_dir": "", "wind_spd": "", "wind_gust": "", "weather": "", "astro": "", "notes": "0 inches"},
    {"page": 4, "date": "2023-06-20", "time": "", "time_qualifier": "", "ware_stage": 4.20, "depth": 1.5, "wind_dir": "", "wind_spd": "", "wind_gust": "", "weather": "Rain", "astro": "", "notes": "Rain Rain"},
    {"page": 4, "date": "2023-06-21", "time": "", "time_qualifier": "", "ware_stage": 4.62, "depth": 7.0, "wind_dir": "NE", "wind_spd": "16-25", "wind_gust": "", "weather": "Rain", "astro": "", "notes": "Rain; NE 16/25"},
    {"page": 4, "date": "2023-06-21", "time": "", "time_qualifier": "", "ware_stage": 4.50, "depth": 5.0, "wind_dir": "", "wind_spd": "0", "wind_gust": "", "weather": "", "astro": "", "notes": "calm"},
    {"page": 4, "date": "2023-08-28", "time": "", "time_qualifier": "", "ware_stage": 4.07, "depth": None, "wind_dir": "", "wind_spd": "", "wind_gust": "", "weather": "Hurricane Idalia", "astro": "Full moon", "notes": "Hurricane Idalia + full moon"},
    {"page": 4, "date": "2023-08-29", "time": "", "time_qualifier": "", "ware_stage": 4.15, "depth": None, "wind_dir": "", "wind_spd": "", "wind_gust": "", "weather": "Hurricane Franklin", "astro": "Full moon", "notes": "Hurricane franklin + full m"},
    {"page": 4, "date": "2023-08-30", "time": "", "time_qualifier": "", "ware_stage": 4.10, "depth": None, "wind_dir": "", "wind_spd": "5", "wind_gust": "", "weather": "", "astro": "", "notes": "wind 5 mph"},
    {"page": 4, "date": "2023-08-31", "time": "09:49", "time_qualifier": "AM", "ware_stage": 4.49, "depth": 4.0, "wind_dir": "NNE", "wind_spd": "15-25", "wind_gust": "", "weather": "", "astro": "", "notes": "NNE 15-25; 9:49 AM"},
    {"page": 4, "date": "2023-08-31", "time": "", "time_qualifier": "", "ware_stage": 4.30, "depth": 2.0, "wind_dir": "", "wind_spd": "0", "wind_gust": "", "weather": "", "astro": "", "notes": "wind 0"},
    {"page": 4, "date": "2023-09-01", "time": "", "time_qualifier": "", "ware_stage": 4.30, "depth": None, "wind_dir": "NE", "wind_spd": "light", "wind_gust": "", "weather": "", "astro": "", "notes": "NE light"},
    {"page": 4, "date": "2023-09-01", "time": "", "time_qualifier": "", "ware_stage": 4.20, "depth": None, "wind_dir": "", "wind_spd": "", "wind_gust": "", "weather": "", "astro": "", "notes": ""},
    {"page": 4, "date": "2023-09-02", "time": "", "time_qualifier": "", "ware_stage": 4.00, "depth": None, "wind_dir": "", "wind_spd": "", "wind_gust": "", "weather": "", "astro": "", "notes": ""},
    {"page": 4, "date": "2023-09-22", "time": "", "time_qualifier": "", "ware_stage": 4.70, "depth": 10.0, "wind_dir": "", "wind_spd": "", "wind_gust": "", "weather": "Ophelia", "astro": "Lunar perigee", "notes": "Ophelia; Lunar perigee"},
    {"page": 4, "date": "2023-09-23", "time": "", "time_qualifier": "", "ware_stage": 4.68, "depth": 10.0, "wind_dir": "", "wind_spd": "", "wind_gust": "", "weather": "Ophelia", "astro": "", "notes": "Ophelia"},
    {"page": 4, "date": "2023-09-23", "time": "", "time_qualifier": "", "ware_stage": 5.00, "depth": 12.0, "wind_dir": "", "wind_spd": "", "wind_gust": "", "weather": "Ophelia", "astro": "", "notes": "Ophelia"},
    {"page": 4, "date": "2023-09-24", "time": "", "time_qualifier": "", "ware_stage": 4.00, "depth": None, "wind_dir": "", "wind_spd": "", "wind_gust": "", "weather": "Ophelia", "astro": "", "notes": "Ophelia"},
    {"page": 4, "date": "2023-09-24", "time": "", "time_qualifier": "", "ware_stage": 4.17, "depth": None, "wind_dir": "", "wind_spd": "", "wind_gust": "", "weather": "Ophelia", "astro": "", "notes": "Ophelia"},

    # Page 5 (IMG_8054.jpeg)
    {"page": 5, "date": "2023-09-26", "time": "", "time_qualifier": "PM", "ware_stage": 4.60, "depth": 8.0, "wind_dir": "", "wind_spd": "", "wind_gust": "", "weather": "", "astro": "", "notes": "4.6 PM"},
    {"page": 5, "date": "2023-09-27", "time": "", "time_qualifier": "", "ware_stage": 4.68, "depth": 8.0, "wind_dir": "", "wind_spd": "", "wind_gust": "", "weather": "", "astro": "", "notes": ""},
    {"page": 5, "date": "2023-09-27", "time": "", "time_qualifier": "", "ware_stage": 4.93, "depth": 11.0, "wind_dir": "", "wind_spd": "", "wind_gust": "", "weather": "", "astro": "", "notes": ""},
    {"page": 5, "date": "2023-09-28", "time": "", "time_qualifier": "", "ware_stage": 4.70, "depth": 10.0, "wind_dir": "", "wind_spd": "", "wind_gust": "", "weather": "", "astro": "", "notes": ""},
    {"page": 5, "date": "2023-09-28", "time": "", "time_qualifier": "", "ware_stage": 4.80, "depth": 9.0, "wind_dir": "", "wind_spd": "", "wind_gust": "", "weather": "", "astro": "", "notes": ""},
    {"page": 5, "date": "2023-09-29", "time": "", "time_qualifier": "", "ware_stage": 4.38, "depth": 6.0, "wind_dir": "", "wind_spd": "", "wind_gust": "", "weather": "", "astro": "", "notes": ""},
    {"page": 5, "date": "2023-09-29", "time": "", "time_qualifier": "", "ware_stage": 4.20, "depth": None, "wind_dir": "", "wind_spd": "", "wind_gust": "", "weather": "", "astro": "", "notes": ""},
    {"page": 5, "date": "2023-09-30", "time": "", "time_qualifier": "", "ware_stage": 4.50, "depth": 3.0, "wind_dir": "", "wind_spd": "", "wind_gust": "", "weather": "", "astro": "", "notes": ""},
    {"page": 5, "date": "2023-09-30", "time": "", "time_qualifier": "", "ware_stage": 4.00, "depth": None, "wind_dir": "", "wind_spd": "", "wind_gust": "", "weather": "", "astro": "", "notes": ""},
    {"page": 5, "date": "2023-10-01", "time": "", "time_qualifier": "", "ware_stage": 4.45, "depth": 4.0, "wind_dir": "", "wind_spd": "", "wind_gust": "", "weather": "", "astro": "", "notes": ""},
    {"page": 5, "date": "2023-10-01", "time": "", "time_qualifier": "", "ware_stage": 4.00, "depth": None, "wind_dir": "", "wind_spd": "", "wind_gust": "", "weather": "", "astro": "", "notes": ""},
    {"page": 5, "date": "2023-10-02", "time": "", "time_qualifier": "", "ware_stage": 4.50, "depth": 4.0, "wind_dir": "", "wind_spd": "", "wind_gust": "", "weather": "", "astro": "", "notes": ""},
    {"page": 5, "date": "2023-10-02", "time": "", "time_qualifier": "", "ware_stage": 3.80, "depth": 0.0, "wind_dir": "", "wind_spd": "", "wind_gust": "", "weather": "", "astro": "", "notes": "(3.8) 0"},
    {"page": 5, "date": "2023-10-03", "time": "", "time_qualifier": "", "ware_stage": 4.20, "depth": None, "wind_dir": "", "wind_spd": "", "wind_gust": "", "weather": "", "astro": "", "notes": ""},
    {"page": 5, "date": "2023-10-15", "time": "", "time_qualifier": "", "ware_stage": 4.50, "depth": None, "wind_dir": "N", "wind_spd": "16", "wind_gust": "", "weather": "", "astro": "", "notes": "N 16 mph"},
    {"page": 5, "date": "2023-10-16", "time": "", "time_qualifier": "", "ware_stage": 4.00, "depth": None, "wind_dir": "N, SSE", "wind_spd": "5, 16.1", "wind_gust": "19", "weather": "", "astro": "", "notes": "N 5mph; SSE 16.1 19 gusts"},
    {"page": 5, "date": "2023-12-18", "time": "", "time_qualifier": "", "ware_stage": 4.22, "depth": None, "wind_dir": "", "wind_spd": "", "wind_gust": "", "weather": "", "astro": "", "notes": "?"},
    {"page": 5, "date": "2023-12-18", "time": "", "time_qualifier": "", "ware_stage": 4.64, "depth": 8.0, "wind_dir": "W", "wind_spd": "8", "wind_gust": "", "weather": "", "astro": "", "notes": "W 8"},

    # Page 6 (IMG_8055.jpeg)
    {"page": 6, "date": "2024-01-09", "time": "", "time_qualifier": "", "ware_stage": 4.00, "depth": 0.0, "wind_dir": "ESE, SSE, S", "wind_spd": "21, 24, 23, 15", "wind_gust": "39, 34, 40.3, 27", "weather": "", "astro": "", "notes": "21 ESE 39, 24 SSE 34, 23 SSE 40.3, 15 S 27"},
    {"page": 6, "date": "2024-01-13", "time": "", "time_qualifier": "", "ware_stage": 4.09, "depth": 0.5, "wind_dir": "W", "wind_spd": "16.1", "wind_gust": "30", "weather": "", "astro": "", "notes": "16.1 W 30"},
    {"page": 6, "date": "2024-02-06", "time": "", "time_qualifier": "", "ware_stage": 4.46, "depth": 5.0, "wind_dir": "", "wind_spd": "", "wind_gust": "", "weather": "", "astro": "", "notes": ""},
    {"page": 6, "date": "2024-02-07", "time": "", "time_qualifier": "", "ware_stage": 4.51, "depth": 6.0, "wind_dir": "N", "wind_spd": "", "wind_gust": "", "weather": "", "astro": "", "notes": "N"},
    {"page": 6, "date": "2024-02-08", "time": "", "time_qualifier": "", "ware_stage": 4.30, "depth": 1.0, "wind_dir": "N", "wind_spd": "", "wind_gust": "", "weather": "", "astro": "", "notes": "N"},
    {"page": 6, "date": "2024-02-11", "time": "", "time_qualifier": "", "ware_stage": 4.08, "depth": 0.0, "wind_dir": "S", "wind_spd": "", "wind_gust": "34-39", "weather": "", "astro": "", "notes": "S gusts 34-39"},
    {"page": 6, "date": "2024-02-14", "time": "", "time_qualifier": "", "ware_stage": 4.40, "depth": 2.0, "wind_dir": "", "wind_spd": "", "wind_gust": "", "weather": "", "astro": "", "notes": ""},
    {"page": 6, "date": "2024-03-09", "time": "", "time_qualifier": "AM", "ware_stage": 4.61, "depth": 7.0, "wind_dir": "ESE", "wind_spd": "19.5", "wind_gust": "", "weather": "", "astro": "", "notes": "4.61 A; ESE 19.5"},
    {"page": 6, "date": "2024-03-09", "time": "", "time_qualifier": "", "ware_stage": 4.20, "depth": 3.0, "wind_dir": "SSE", "wind_spd": "19.5", "wind_gust": "", "weather": "", "astro": "", "notes": "4.20 ?; SSE 19.5"},
    {"page": 6, "date": "2024-03-10", "time": "", "time_qualifier": "", "ware_stage": 4.74, "depth": 9.0, "wind_dir": "WNW", "wind_spd": "10", "wind_gust": "", "weather": "", "astro": "", "notes": "WNW 10"},
    {"page": 6, "date": "2024-03-25", "time": "", "time_qualifier": "", "ware_stage": 4.22, "depth": 1.5, "wind_dir": "", "wind_spd": "", "wind_gust": "", "weather": "", "astro": "", "notes": ""},
    {"page": 6, "date": "2024-03-26", "time": "", "time_qualifier": "", "ware_stage": 4.15, "depth": 5.0, "wind_dir": "NE", "wind_spd": "6.9", "wind_gust": "", "weather": "", "astro": "", "notes": "NE 6.9"},
    {"page": 6, "date": "2024-03-26", "time": "", "time_qualifier": "", "ware_stage": 4.60, "depth": 6.0, "wind_dir": "E", "wind_spd": "6", "wind_gust": "", "weather": "", "astro": "", "notes": "E 6"},
    {"page": 6, "date": "2024-03-27", "time": "", "time_qualifier": "", "ware_stage": 4.19, "depth": 1.0, "wind_dir": "", "wind_spd": "", "wind_gust": "", "weather": "", "astro": "", "notes": ""},
    {"page": 6, "date": "2024-03-27", "time": "", "time_qualifier": "", "ware_stage": 4.00, "depth": None, "wind_dir": "", "wind_spd": "", "wind_gust": "", "weather": "", "astro": "", "notes": ""},
    {"page": 6, "date": "2024-04-04", "time": "", "time_qualifier": "", "ware_stage": 4.54, "depth": 5.0, "wind_dir": "", "wind_spd": "0", "wind_gust": "", "weather": "", "astro": "", "notes": "calm"},
    {"page": 6, "date": "2024-04-08", "time": "", "time_qualifier": "", "ware_stage": 4.00, "depth": None, "wind_dir": "", "wind_spd": "", "wind_gust": "", "weather": "", "astro": "Solar Eclipse", "notes": "* Eclipse (2:04 Begin, 3:20 Max, 4:32 Ends)"},
    {"page": 6, "date": "2024-04-09", "time": "", "time_qualifier": "AM", "ware_stage": 4.00, "depth": None, "wind_dir": "", "wind_spd": "", "wind_gust": "", "weather": "", "astro": "", "notes": "4.0 AM"},

    # Page 7 (IMG_8056.jpeg)
    {"page": 7, "date": "2024-04-09", "time": "", "time_qualifier": "PM", "ware_stage": 4.10, "depth": 0.0, "wind_dir": "", "wind_spd": "", "wind_gust": "", "weather": "", "astro": "", "notes": "4.1 PM"},
    {"page": 7, "date": "2024-04-10", "time": "", "time_qualifier": "", "ware_stage": 4.10, "depth": 0.0, "wind_dir": "", "wind_spd": "", "wind_gust": "", "weather": "", "astro": "", "notes": ""},
    {"page": 7, "date": "2024-04-10", "time": "", "time_qualifier": "", "ware_stage": 4.10, "depth": 0.0, "wind_dir": "", "wind_spd": "", "wind_gust": "", "weather": "", "astro": "", "notes": ""},
    {"page": 7, "date": "2024-04-11", "time": "", "time_qualifier": "", "ware_stage": 4.10, "depth": 0.0, "wind_dir": "", "wind_spd": "", "wind_gust": "", "weather": "", "astro": "", "notes": ""},
    {"page": 7, "date": "2024-04-11", "time": "", "time_qualifier": "", "ware_stage": 4.10, "depth": 0.0, "wind_dir": "", "wind_spd": "", "wind_gust": "", "weather": "", "astro": "", "notes": ""},
    {"page": 7, "date": "2024-04-11", "time": "", "time_qualifier": "", "ware_stage": 4.10, "depth": 0.0, "wind_dir": "S", "wind_spd": "", "wind_gust": "", "weather": "", "astro": "", "notes": "4.1 11th S"},
    {"page": 7, "date": "2024-04-12", "time": "00:16", "time_qualifier": "AM", "ware_stage": 4.62, "depth": None, "wind_dir": "S", "wind_spd": "", "wind_gust": "34-39", "weather": "", "astro": "", "notes": "4.62 12th 12:16AM; S gusts 34-39"},
    {"page": 7, "date": "2024-05-03", "time": "", "time_qualifier": "", "ware_stage": 4.00, "depth": 0.0, "wind_dir": "", "wind_spd": "", "wind_gust": "", "weather": "", "astro": "", "notes": ""},
    {"page": 7, "date": "2024-05-04", "time": "", "time_qualifier": "AM", "ware_stage": 4.09, "depth": 0.0, "wind_dir": "", "wind_spd": "", "wind_gust": "", "weather": "", "astro": "", "notes": "4.09 A"},
    {"page": 7, "date": "2024-05-04", "time": "", "time_qualifier": "PM", "ware_stage": 4.02, "depth": 0.0, "wind_dir": "", "wind_spd": "", "wind_gust": "", "weather": "", "astro": "", "notes": "4.02 P"},
    {"page": 7, "date": "2024-05-05", "time": "", "time_qualifier": "PM", "ware_stage": 4.06, "depth": 0.0, "wind_dir": "", "wind_spd": "", "wind_gust": "", "weather": "", "astro": "", "notes": "4.06 P"},
    {"page": 7, "date": "2024-05-06", "time": "", "time_qualifier": "PM", "ware_stage": 4.02, "depth": 0.0, "wind_dir": "", "wind_spd": "", "wind_gust": "", "weather": "", "astro": "", "notes": "4.02 P"},
    {"page": 7, "date": "2024-05-08", "time": "", "time_qualifier": "PM", "ware_stage": 4.06, "depth": 0.0, "wind_dir": "", "wind_spd": "", "wind_gust": "", "weather": "", "astro": "", "notes": "4.06 P"},
    {"page": 7, "date": "2024-05-09", "time": "", "time_qualifier": "PM", "ware_stage": 4.13, "depth": 0.0, "wind_dir": "", "wind_spd": "", "wind_gust": "", "weather": "", "astro": "", "notes": "4.13 P"},
    {"page": 7, "date": "2024-05-11", "time": "", "time_qualifier": "AM", "ware_stage": 4.92, "depth": 0.0, "wind_dir": "", "wind_spd": "", "wind_gust": "", "weather": "", "astro": "", "notes": "4.92 A 0"},
    {"page": 7, "date": "2024-05-11", "time": "", "time_qualifier": "PM", "ware_stage": 4.05, "depth": 0.0, "wind_dir": "", "wind_spd": "", "wind_gust": "", "weather": "", "astro": "", "notes": "4.05 P"},
    {"page": 7, "date": "2024-05-12", "time": "", "time_qualifier": "", "ware_stage": 4.30, "depth": 0.0, "wind_dir": "", "wind_spd": "", "wind_gust": "", "weather": "", "astro": "", "notes": ""},
    {"page": 7, "date": "2024-05-15", "time": "", "time_qualifier": "", "ware_stage": 4.20, "depth": 0.0, "wind_dir": "", "wind_spd": "", "wind_gust": "", "weather": "", "astro": "", "notes": ""},
    {"page": 7, "date": "2024-05-20", "time": "", "time_qualifier": "PM", "ware_stage": 3.93, "depth": None, "wind_dir": "ESE, N", "wind_spd": "3.4", "wind_gust": "", "weather": "", "astro": "", "notes": "3.93 P; ESE N 3.4mph"},

    # Page 8 (IMG_8058.jpeg)
    {"page": 8, "date": "2024-09-15", "time": "19:39", "time_qualifier": "PM", "ware_stage": 4.08, "depth": 0.0, "wind_dir": "NNE-NE", "wind_spd": "10-15", "wind_gust": "", "weather": "", "astro": "", "notes": "7:39p; NNE NE 10-15"},
    {"page": 8, "date": "2024-09-16", "time": "08:00", "time_qualifier": "AM", "ware_stage": 4.12, "depth": 0.0, "wind_dir": "NNE-NE", "wind_spd": "10-15", "wind_gust": "", "weather": "", "astro": "", "notes": "8A; NNE NE 10-15"},
    {"page": 8, "date": "2024-09-16", "time": "20:31", "time_qualifier": "PM", "ware_stage": 4.52, "depth": 5.0, "wind_dir": "SE", "wind_spd": "5-10", "wind_gust": "", "weather": "", "astro": "", "notes": "8:31p; 5\""},
    {"page": 8, "date": "2024-09-17", "time": "08:52", "time_qualifier": "AM", "ware_stage": 4.31, "depth": 3.0, "wind_dir": "SE", "wind_spd": "5-10", "wind_gust": "", "weather": "", "astro": "Full moon, King tide", "notes": "8:52A; Full moon / King tide"},
    {"page": 8, "date": "2024-09-17", "time": "21:20", "time_qualifier": "PM", "ware_stage": 4.57, "depth": 5.5, "wind_dir": "SE", "wind_spd": "5-10", "wind_gust": "", "weather": "", "astro": "King tide", "notes": "9:20p; 5 1/2\"; King tide"},
    {"page": 8, "date": "2024-09-18", "time": "09:41", "time_qualifier": "AM", "ware_stage": 4.52, "depth": 5.0, "wind_dir": "SE", "wind_spd": "5-10", "wind_gust": "", "weather": "", "astro": "", "notes": "9:41A; 5\""},
    {"page": 8, "date": "2024-09-18", "time": "22:08", "time_qualifier": "PM", "ware_stage": 4.50, "depth": 5.0, "wind_dir": "SE", "wind_spd": "5-10", "wind_gust": "", "weather": "", "astro": "", "notes": "10:08p; 5\""},
    {"page": 8, "date": "2024-09-19", "time": "10:30", "time_qualifier": "AM", "ware_stage": 4.64, "depth": 8.0, "wind_dir": "SE", "wind_spd": "5-10", "wind_gust": "", "weather": "", "astro": "", "notes": "10:30A; 8\""},
    {"page": 8, "date": "2024-09-19", "time": "22:56", "time_qualifier": "PM", "ware_stage": 4.38, "depth": 3.0, "wind_dir": "SE", "wind_spd": "5-10", "wind_gust": "", "weather": "", "astro": "", "notes": "10:56p; 3\""},
    {"page": 8, "date": "2024-09-20", "time": "10:20", "time_qualifier": "AM", "ware_stage": 4.78, "depth": 9.5, "wind_dir": "SE", "wind_spd": "5-10", "wind_gust": "", "weather": "", "astro": "", "notes": "10:20A; 9.5\""},
    {"page": 8, "date": "2024-09-20", "time": "22:45", "time_qualifier": "PM", "ware_stage": 4.48, "depth": 4.0, "wind_dir": "SE", "wind_spd": "5-10", "wind_gust": "", "weather": "", "astro": "", "notes": "10:45p; 4\""},
    {"page": 8, "date": "2024-09-21", "time": "12:12", "time_qualifier": "PM", "ware_stage": 4.96, "depth": 11.75, "wind_dir": "SE", "wind_spd": "5-10", "wind_gust": "", "weather": "", "astro": "", "notes": "12:12p; 11 3/4\""},
    {"page": 8, "date": "2024-09-22", "time": "00:36", "time_qualifier": "AM", "ware_stage": 4.36, "depth": 6.0, "wind_dir": "SE", "wind_spd": "5-10", "wind_gust": "", "weather": "", "astro": "", "notes": "12:36A; 6\""},
    {"page": 8, "date": "2024-09-22", "time": "13:06", "time_qualifier": "PM", "ware_stage": 5.20, "depth": 14.5, "wind_dir": "SE", "wind_spd": "5-10", "wind_gust": "", "weather": "", "astro": "", "notes": "1:06P; 14.5\""},
    {"page": 8, "date": "2024-09-23", "time": "01:31", "time_qualifier": "AM", "ware_stage": 4.51, "depth": 5.0, "wind_dir": "SE", "wind_spd": "5-10", "wind_gust": "", "weather": "", "astro": "", "notes": "1:31A; 5\""},
    {"page": 8, "date": "2024-09-23", "time": "14:05", "time_qualifier": "PM", "ware_stage": 4.83, "depth": 10.75, "wind_dir": "SE", "wind_spd": "5-10", "wind_gust": "", "weather": "", "astro": "", "notes": "2:05p; 10 3/4\""},
    {"page": 8, "date": "2024-09-24", "time": "02:31", "time_qualifier": "AM", "ware_stage": 4.28, "depth": 3.0, "wind_dir": "SE", "wind_spd": "5-10", "wind_gust": "", "weather": "", "astro": "", "notes": "2:31A; 3\""},
    {"page": 8, "date": "2024-09-24", "time": "15:11", "time_qualifier": "PM", "ware_stage": 4.57, "depth": 7.0, "wind_dir": "SE", "wind_spd": "5-10", "wind_gust": "", "weather": "", "astro": "", "notes": "3:11p; 7\""},
    {"page": 8, "date": "2024-09-25", "time": "03:38", "time_qualifier": "AM", "ware_stage": 4.23, "depth": 2.0, "wind_dir": "SE", "wind_spd": "5-10", "wind_gust": "", "weather": "", "astro": "", "notes": "3:38A; 2\""},
    {"page": 8, "date": "2024-09-25", "time": "16:20", "time_qualifier": "PM", "ware_stage": 4.38, "depth": 2.25, "wind_dir": "SE", "wind_spd": "5-10", "wind_gust": "", "weather": "", "astro": "", "notes": "4:20p; 2.25\""},
    {"page": 8, "date": "2024-09-26", "time": "04:47", "time_qualifier": "AM", "ware_stage": 3.79, "depth": 0.0, "wind_dir": "", "wind_spd": "", "wind_gust": "", "weather": "", "astro": "", "notes": "4:47A; 0\""},
    {"page": 8, "date": "2024-09-26", "time": "17:27", "time_qualifier": "PM", "ware_stage": 4.09, "depth": 0.0, "wind_dir": "", "wind_spd": "", "wind_gust": "", "weather": "", "astro": "", "notes": "5:27p; 0 (2-3\" in rd + ditches)"},
    {"page": 8, "date": "2024-09-27", "time": "05:52", "time_qualifier": "AM", "ware_stage": 3.55, "depth": 0.0, "wind_dir": "", "wind_spd": "", "wind_gust": "", "weather": "", "astro": "", "notes": "5:52A; 0\""},
    {"page": 8, "date": "2024-09-27", "time": "18:26", "time_qualifier": "PM", "ware_stage": 4.70, "depth": 9.75, "wind_dir": "SE", "wind_spd": "25.3", "wind_gust": "", "weather": "Hurricane Helene", "astro": "", "notes": "6:26p; 9 3/4\"; SE 25.3 mph; Hurricane Helene"},

    # Sticky Note (IMG_8057.jpeg) - Detailed time series of Helene peak
    {"page": "sticky_helene", "date": "2024-09-27", "time": "18:20", "time_qualifier": "PM", "ware_stage": None, "depth": 3.0, "wind_dir": "SE", "wind_spd": "25.3", "wind_gust": "", "weather": "Hurricane Helene", "astro": "", "notes": "Helene: 6:20pm 3\""},
    {"page": "sticky_helene", "date": "2024-09-27", "time": "19:30", "time_qualifier": "PM", "ware_stage": 4.70, "depth": 9.75, "wind_dir": "SE", "wind_spd": "25.3", "wind_gust": "", "weather": "Hurricane Helene", "astro": "", "notes": "Helene: 7:30pm 9 3/4\" (peak); Ware River 4.7; winds 25.3 mph SE"},
    {"page": "sticky_helene", "date": "2024-09-27", "time": "20:20", "time_qualifier": "PM", "ware_stage": None, "depth": 2.5, "wind_dir": "SE", "wind_spd": "25.3", "wind_gust": "", "weather": "Hurricane Helene", "astro": "", "notes": "Helene: @ 8:20pm tide down 7 1/4\" to 2.5\""}
]

fieldnames = [
    "observation_id",
    "date",
    "time_local",
    "time_qualifier",
    "page_source",
    "ware_river_stage_ft",
    "flood_depth_in",
    "is_flooded",
    "wind_direction",
    "wind_speed_mph",
    "wind_gust_mph",
    "weather_system",
    "astronomical_event",
    "raw_notes"
]

with open("ground_truth_observations.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    for idx, e in enumerate(raw_entries, 1):
        is_flooded = None
        if e["depth"] is not None:
            is_flooded = "TRUE" if e["depth"] > 0 else "FALSE"

        writer.writerow({
            "observation_id": idx,
            "date": e["date"],
            "time_local": e["time"],
            "time_qualifier": e["time_qualifier"],
            "page_source": f"notebook_page_{e['page']}" if isinstance(e['page'], int) else str(e['page']),
            "ware_river_stage_ft": f"{e['ware_stage']:.2f}" if e["ware_stage"] is not None else "",
            "flood_depth_in": f"{e['depth']:.2f}" if e["depth"] is not None else "",
            "is_flooded": is_flooded if is_flooded is not None else "",
            "wind_direction": e["wind_dir"],
            "wind_speed_mph": e["wind_spd"],
            "wind_gust_mph": e["wind_gust"],
            "weather_system": e["weather"],
            "astronomical_event": e["astro"],
            "raw_notes": e["notes"]
        })

print(f"Successfully generated ground_truth_observations.csv with {len(raw_entries)} records.")
