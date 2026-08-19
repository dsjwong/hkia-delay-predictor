"""IATA airport code -> (city, country) for the destinations HKIA serves (display only; regions.py is the model's map).

Unknown codes map to (code, "") so the UI still shows something. Extend when a new destination appears in the db
(`python -m hkia.export_json` logs the unmapped codes).
"""
from __future__ import annotations

_A = {
    # mainland China
    "PEK": ("Beijing Capital", "China"), "PKX": ("Beijing Daxing", "China"), "PVG": ("Shanghai Pudong", "China"),
    "SHA": ("Shanghai Hongqiao", "China"), "CAN": ("Guangzhou", "China"), "SZX": ("Shenzhen", "China"), "CTU": ("Chengdu Shuangliu", "China"),
    "TFU": ("Chengdu Tianfu", "China"), "CKG": ("Chongqing", "China"), "HGH": ("Hangzhou", "China"), "NKG": ("Nanjing", "China"),
    "WUH": ("Wuhan", "China"), "XIY": ("Xi'an", "China"), "KMG": ("Kunming", "China"), "CSX": ("Changsha", "China"), "CGO": ("Zhengzhou", "China"),
    "XMN": ("Xiamen", "China"), "FOC": ("Fuzhou", "China"), "TAO": ("Qingdao", "China"), "TSN": ("Tianjin", "China"), "DLC": ("Dalian", "China"),
    "SYX": ("Sanya", "China"), "HAK": ("Haikou", "China"), "NGB": ("Ningbo", "China"), "TNA": ("Jinan", "China"), "HRB": ("Harbin", "China"),
    "SHE": ("Shenyang", "China"), "CGQ": ("Changchun", "China"), "KWL": ("Guilin", "China"), "NNG": ("Nanning", "China"), "WNZ": ("Wenzhou", "China"),
    "HFE": ("Hefei", "China"), "TYN": ("Taiyuan", "China"), "URC": ("Urumqi", "China"), "LHW": ("Lanzhou", "China"), "SJW": ("Shijiazhuang", "China"),
    "WUX": ("Wuxi", "China"), "CZX": ("Changzhou", "China"), "YIW": ("Yiwu", "China"), "HSN": ("Zhoushan", "China"), "DYG": ("Zhangjiajie", "China"),
    "LJG": ("Lijiang", "China"), "INC": ("Yinchuan", "China"), "XNN": ("Xining", "China"), "YIH": ("Yichang", "China"), "ENH": ("Enshi", "China"),
    "DAT": ("Datong", "China"), "DNH": ("Dunhuang", "China"), "HLD": ("Hulunbuir", "China"), "YCU": ("Yuncheng", "China"), "KTI": ("Kratie", "Cambodia"),
    "NQZ": ("Astana", "Kazakhstan"),
    # Hong Kong / Macau / Taiwan
    "HKG": ("Hong Kong", "Hong Kong"), "MFM": ("Macau", "Macau"), "TPE": ("Taipei Taoyuan", "Taiwan"), "KHH": ("Kaohsiung", "Taiwan"),
    "RMQ": ("Taichung", "Taiwan"), "TSA": ("Taipei Songshan", "Taiwan"),
    # Japan / Korea
    "NRT": ("Tokyo Narita", "Japan"), "HND": ("Tokyo Haneda", "Japan"), "KIX": ("Osaka Kansai", "Japan"), "NGO": ("Nagoya", "Japan"),
    "FUK": ("Fukuoka", "Japan"), "CTS": ("Sapporo", "Japan"), "OKA": ("Okinawa", "Japan"), "SDJ": ("Sendai", "Japan"), "HIJ": ("Hiroshima", "Japan"),
    "TAK": ("Takamatsu", "Japan"), "KMQ": ("Komatsu", "Japan"), "ISG": ("Ishigaki", "Japan"), "KOJ": ("Kagoshima", "Japan"), "KMJ": ("Kumamoto", "Japan"),
    "ICN": ("Seoul Incheon", "South Korea"), "GMP": ("Seoul Gimpo", "South Korea"), "PUS": ("Busan", "South Korea"), "CJU": ("Jeju", "South Korea"),
    "TAE": ("Daegu", "South Korea"),
    # SE Asia
    "BKK": ("Bangkok Suvarnabhumi", "Thailand"), "DMK": ("Bangkok Don Mueang", "Thailand"), "HKT": ("Phuket", "Thailand"), "CNX": ("Chiang Mai", "Thailand"),
    "USM": ("Koh Samui", "Thailand"), "SIN": ("Singapore", "Singapore"), "KUL": ("Kuala Lumpur", "Malaysia"), "SZB": ("Kuala Lumpur Subang", "Malaysia"),
    "PEN": ("Penang", "Malaysia"), "BKI": ("Kota Kinabalu", "Malaysia"), "MNL": ("Manila", "Philippines"), "CEB": ("Cebu", "Philippines"),
    "CRK": ("Clark", "Philippines"), "DVO": ("Davao", "Philippines"), "ILO": ("Iloilo", "Philippines"), "SGN": ("Ho Chi Minh City", "Vietnam"),
    "HAN": ("Hanoi", "Vietnam"), "DAD": ("Da Nang", "Vietnam"), "PQC": ("Phu Quoc", "Vietnam"), "CGK": ("Jakarta", "Indonesia"),
    "DPS": ("Bali Denpasar", "Indonesia"), "SUB": ("Surabaya", "Indonesia"), "BWN": ("Bandar Seri Begawan", "Brunei"), "PNH": ("Phnom Penh", "Cambodia"),
    "REP": ("Siem Reap", "Cambodia"), "RGN": ("Yangon", "Myanmar"), "VTE": ("Vientiane", "Laos"), "PKZ": ("Pakse", "Laos"),
    # South Asia
    "DEL": ("Delhi", "India"), "BOM": ("Mumbai", "India"), "MAA": ("Chennai", "India"), "BLR": ("Bengaluru", "India"), "HYD": ("Hyderabad", "India"),
    "CCU": ("Kolkata", "India"), "CMB": ("Colombo", "Sri Lanka"), "DAC": ("Dhaka", "Bangladesh"), "KTM": ("Kathmandu", "Nepal"), "MLE": ("Malé", "Maldives"),
    "PBH": ("Paro", "Bhutan"),
    # Oceania / Pacific
    "SYD": ("Sydney", "Australia"), "MEL": ("Melbourne", "Australia"), "BNE": ("Brisbane", "Australia"), "PER": ("Perth", "Australia"),
    "AKL": ("Auckland", "New Zealand"), "NAN": ("Nadi", "Fiji"), "POM": ("Port Moresby", "Papua New Guinea"), "SPN": ("Saipan", "N. Mariana Is."),
    "ROR": ("Koror", "Palau"), "HNL": ("Honolulu", "USA"), "UBN": ("Ulaanbaatar", "Mongolia"),
    # Middle East / Central Asia / Africa
    "DXB": ("Dubai", "UAE"), "DWC": ("Dubai Al Maktoum", "UAE"), "AUH": ("Abu Dhabi", "UAE"), "DOH": ("Doha", "Qatar"), "RUH": ("Riyadh", "Saudi Arabia"),
    "IST": ("Istanbul", "Türkiye"), "ADD": ("Addis Ababa", "Ethiopia"), "JNB": ("Johannesburg", "South Africa"),
    # Europe
    "LHR": ("London Heathrow", "UK"), "MAN": ("Manchester", "UK"), "CDG": ("Paris CDG", "France"), "AMS": ("Amsterdam", "Netherlands"),
    "FRA": ("Frankfurt", "Germany"), "MUC": ("Munich", "Germany"), "ZRH": ("Zürich", "Switzerland"), "FCO": ("Rome Fiumicino", "Italy"),
    "MXP": ("Milan Malpensa", "Italy"), "MAD": ("Madrid", "Spain"), "BCN": ("Barcelona", "Spain"), "HEL": ("Helsinki", "Finland"),
    "BRU": ("Brussels", "Belgium"), "SVO": ("Moscow Sheremetyevo", "Russia"),
    # North America
    "LAX": ("Los Angeles", "USA"), "SFO": ("San Francisco", "USA"), "JFK": ("New York JFK", "USA"), "ORD": ("Chicago O'Hare", "USA"),
    "SEA": ("Seattle", "USA"), "BOS": ("Boston", "USA"), "DFW": ("Dallas/Fort Worth", "USA"), "YVR": ("Vancouver", "Canada"), "YYZ": ("Toronto", "Canada"),
}


def airport(iata: str | None) -> tuple[str, str]:
    code = (iata or "").split(",")[0].strip().upper()
    return _A.get(code, (code, ""))


def known(iata: str | None) -> bool:
    return (iata or "").split(",")[0].strip().upper() in _A
