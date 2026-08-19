"""Static airline lookups shared by the dashboard, the API and the JSON export: ICAO code -> display name.

IATA -> ICAO for callsign matching (`CPA261` <-> `CX 261`) is derived from the db at export time (flight_no prefix vs `airline`)
and written to web/public/data/meta.json; IATA_TO_ICAO below is the static seed for airlines with few rows.
"""
from __future__ import annotations

AIRLINE_NAMES = {
    "CPA": "Cathay Pacific", "HKE": "HK Express", "CRK": "Hong Kong Airlines", "HGB": "Greater Bay Airlines",
    "CES": "China Eastern", "CSN": "China Southern", "CCA": "Air China", "CSZ": "Shenzhen Airlines", "CXA": "Xiamen Air",
    "CHH": "Hainan Airlines", "CSH": "Shanghai Airlines", "CQH": "Spring Airlines", "SIA": "Singapore Airlines",
    "UAE": "Emirates", "QTR": "Qatar Airways", "THA": "Thai Airways", "MAS": "Malaysia Airlines", "CAL": "China Airlines",
    "EVA": "EVA Air", "SJX": "Starlux", "KAL": "Korean Air", "AAR": "Asiana", "JAL": "Japan Airlines", "ANA": "ANA",
    "PAL": "Philippine Airlines", "CEB": "Cebu Pacific", "GIA": "Garuda", "VJC": "VietJet", "HVN": "Vietnam Airlines",
    "AXM": "AirAsia", "BAW": "British Airways", "QFA": "Qantas", "UAL": "United", "AAL": "American", "ACA": "Air Canada",
    "DLH": "Lufthansa", "AFR": "Air France", "KLM": "KLM", "SWR": "SWISS", "ETD": "Etihad", "TGW": "Scoot", "JJP": "Jetstar Japan",
    "AIC": "Air India", "ETH": "Ethiopian", "FIN": "Finnair", "TAP": "TAP", "VIR": "Virgin Atlantic", "APJ": "Peach",
    "ESR": "Eastar Jet", "JJA": "Jeju Air", "ASV": "Air Seoul", "AAX": "AirAsia X", "TVJ": "Thai VietJet", "NOK": "Nok Air", "TLM": "Thai Lion", "JNA": "Jin Air", "TWB": "T'way", "ABL": "Air Busan", "JSA": "Jetstar Asia", "AHK": "Air Hong Kong",
    "MDA": "Mandarin Airlines", "UIA": "Uni Air", "BKP": "Bangkok Airways", "MXD": "Malindo/Batik", "RBA": "Royal Brunei",
    "MMA": "Myanmar Airways Intl", "DRK": "Druk Air", "RNA": "Nepal Airlines", "BBC": "Biman", "ALK": "SriLankan",
    "IGO": "IndiGo", "TUA": "Turkmenistan Airlines", "THY": "Turkish Airlines", "SVA": "Saudia", "GFA": "Gulf Air",
    "OMA": "Oman Air", "ELY": "El Al", "SAS": "SAS", "AZA": "ITA", "IBE": "Iberia", "AUA": "Austrian", "LOT": "LOT",
    "ANZ": "Air New Zealand", "FJI": "Fiji Airways", "PIA": "PIA", "KZR": "Air Astana", "MGL": "MIAT", "AVN": "Air Vanuatu",
    "SBI": "S7", "AFL": "Aeroflot", "PAC": "Polar Air Cargo", "CLX": "Cargolux", "FDX": "FedEx", "UPS": "UPS", "GEC": "Lufthansa Cargo",
    "SQC": "Singapore Airlines Cargo", "CKK": "China Cargo", "CSC": "Sichuan Airlines", "CDG": "Shandong Airlines",
    "OKA": "Okay Airways", "CBJ": "Capital Airlines", "GCR": "Tianjin Airlines", "LKE": "Lucky Air", "CUA": "China United",
    "DKH": "Juneyao", "CHB": "West Air", "CQN": "Chongqing Airlines", "CYZ": "China Postal", "KNA": "Kunming Airlines",
    "GDC": "Air Guilin", "CGZ": "Loong Air", "UEA": "Urumqi Air", "HXA": "China Express", "CDC": "Air Changan",
    "FZA": "Fuzhou Airlines", "CSS": "SF Airlines", "TBA": "Tibet Airlines", "MMZ": "Air Macau", "AMU": "Air Macau",
}


# seed map IATA -> ICAO (the db-derived map in hkia.export_json overrides/extends it)
IATA_TO_ICAO = {
    "CX": "CPA", "UO": "HKE", "HX": "CRK", "HB": "HGB", "MU": "CES", "CZ": "CSN", "CA": "CCA", "ZH": "CSZ", "MF": "CXA",
    "HU": "CHH", "FM": "CSH", "9C": "CQH", "SQ": "SIA", "EK": "UAE", "QR": "QTR", "TG": "THA", "MH": "MAS", "CI": "CAL",
    "BR": "EVA", "JX": "SJX", "KE": "KAL", "OZ": "AAR", "JL": "JAL", "NH": "ANA", "PR": "PAL", "5J": "CEB", "GA": "GIA",
    "VJ": "VJC", "VN": "HVN", "AK": "AXM", "BA": "BAW", "QF": "QFA", "UA": "UAL", "AA": "AAL", "AC": "ACA", "LH": "DLH",
    "AF": "AFR", "KL": "KLM", "LX": "SWR", "EY": "ETD", "TR": "TGW", "GK": "JJP", "AI": "AIC", "ET": "ETH", "AY": "FIN",
    "TP": "TAP", "VS": "VIR", "MM": "APJ", "ZE": "ESR", "7C": "JJA", "RS": "ASV", "D7": "AAX", "VZ": "TVJ", "DD": "NOK",
    "SL": "TLM", "LJ": "JNA", "TW": "TWB", "BX": "ABL", "3K": "JSA", "LD": "AHK", "AE": "MDA", "B7": "UIA", "PG": "BKP",
    "OD": "MXD", "BI": "RBA", "8M": "MMA", "KB": "DRK", "RA": "RNA", "BG": "BBC", "UL": "ALK", "6E": "IGO", "TK": "THY",
    "SV": "SVA", "GF": "GFA", "WY": "OMA", "LY": "ELY", "SK": "SAS", "AZ": "AZA", "IB": "IBE", "OS": "AUA", "LO": "LOT",
    "NZ": "ANZ", "FJ": "FJI", "PK": "PIA", "KC": "KZR", "OM": "MGL", "S7": "SBI", "SU": "AFL", "3U": "CSC", "SC": "CDG",
    "BK": "OKA", "JD": "CBJ", "GS": "GCR", "8L": "LKE", "KN": "CUA", "HO": "DKH", "PN": "CHB", "OQ": "CQN", "KY": "KNA",
    "GT": "CGZ", "UQ": "UEA", "G5": "HXA", "9H": "CDC", "FU": "FZA", "TV": "TBA", "NX": "AMU", "DL": "DAL", "PX": "ANG",
    "KA": "HDA", "UK": "VTI", "JQ": "JST", "MS": "MSR", "WE": "THD", "RJ": "RJA", "LA": "LAN", "QV": "LAO", "IT": "TTW",
}


def airline_name(code: str | None) -> str:
    return AIRLINE_NAMES.get(code or "", code or "?")
