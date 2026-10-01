from copy import deepcopy


CATEGORY_LABELS = {
    "universal": "Universal Emergency",
    "police": "Police",
    "ambulance": "Ambulance",
    "fire": "Fire",
    "women_safety": "Women Safety",
    "tourist": "Tourist Helpline",
}

CATEGORY_ALIASES = {
    "emergency": "universal",
    "sos": "universal",
    "all": "universal",
    "police": "police",
    "crime": "police",
    "ambulance": "ambulance",
    "medical": "ambulance",
    "hospital": "ambulance",
    "fire": "fire",
    "fire force": "fire",
    "women": "women_safety",
    "woman": "women_safety",
    "women safety": "women_safety",
    "women help": "women_safety",
    "tourist": "tourist",
    "tourist helpline": "tourist",
}

DEFAULT_PROFILE = {
    "country": "Global fallback",
    "aliases": [],
    "universal": "112",
    "police": "112",
    "ambulance": "112",
    "fire": "112",
    "women_safety": "112",
    "tourist": "112",
    "source": "Global GSM emergency fallback; confirm locally where possible",
    "updated": "2026-07",
    "states": {},
}

COUNTRY_PROFILES = {
    "india": {
        "country": "India",
        "aliases": ["in", "bharat", "hindustan"],
        "universal": "112",
        "police": "100",
        "ambulance": "108",
        "fire": "101",
        "women_safety": "181 / 1091",
        "tourist": "1363",
        "source": "India national emergency and public helpline directory",
        "updated": "2026-07",
        "states": {
            "karnataka": {"police": "100", "ambulance": "108", "fire": "101", "women_safety": "1091 / 181"},
            "maharashtra": {"police": "100", "ambulance": "108 / 102", "fire": "101", "women_safety": "103 / 181"},
            "delhi": {"police": "112 / 100", "ambulance": "102 / 108", "fire": "101", "women_safety": "181 / 1091"},
            "tamil nadu": {"police": "100", "ambulance": "108", "fire": "101", "women_safety": "181 / 1091"},
            "kerala": {"police": "112 / 100", "ambulance": "108", "fire": "101", "women_safety": "181 / 1091"},
            "goa": {"police": "112 / 100", "ambulance": "108", "fire": "101", "women_safety": "1091 / 181"},
        },
    },
    "united states": {
        "country": "United States",
        "aliases": ["usa", "us", "u.s.", "america", "united states of america", "california", "new york", "texas"],
        "universal": "911",
        "police": "911",
        "ambulance": "911",
        "fire": "911",
        "women_safety": "911 / 1-800-799-7233",
        "tourist": "911",
        "source": "US emergency services and national domestic violence hotline",
        "updated": "2026-07",
        "states": {
            "california": {},
            "new york": {},
            "texas": {},
            "florida": {},
            "washington": {},
        },
    },
    "united kingdom": {
        "country": "United Kingdom",
        "aliases": ["uk", "u.k.", "great britain", "england", "scotland", "wales", "northern ireland"],
        "universal": "999 / 112",
        "police": "999 / 112",
        "ambulance": "999 / 112",
        "fire": "999 / 112",
        "women_safety": "999 / 112",
        "tourist": "999 / 112",
        "source": "UK emergency services",
        "updated": "2026-07",
        "states": {},
    },
    "canada": {
        "country": "Canada",
        "aliases": ["ontario", "quebec", "british columbia", "alberta"],
        "universal": "911",
        "police": "911",
        "ambulance": "911",
        "fire": "911",
        "women_safety": "911",
        "tourist": "911",
        "source": "Canada emergency services",
        "updated": "2026-07",
        "states": {},
    },
    "australia": {
        "country": "Australia",
        "aliases": ["new south wales", "victoria", "queensland", "western australia"],
        "universal": "000 / 112",
        "police": "000",
        "ambulance": "000",
        "fire": "000",
        "women_safety": "000",
        "tourist": "000",
        "source": "Australia emergency services",
        "updated": "2026-07",
        "states": {},
    },
    "new zealand": {
        "country": "New Zealand",
        "aliases": ["nz"],
        "universal": "111",
        "police": "111",
        "ambulance": "111",
        "fire": "111",
        "women_safety": "111",
        "tourist": "111",
        "source": "New Zealand emergency services",
        "updated": "2026-07",
        "states": {},
    },
    "japan": {
        "country": "Japan",
        "aliases": ["tokyo", "osaka", "kyoto"],
        "universal": "110 / 119",
        "police": "110",
        "ambulance": "119",
        "fire": "119",
        "women_safety": "110",
        "tourist": "050-3816-2787",
        "source": "Japan emergency and visitor hotline directory",
        "updated": "2026-07",
        "states": {},
    },
    "france": {
        "country": "France",
        "aliases": ["paris"],
        "universal": "112",
        "police": "17",
        "ambulance": "15",
        "fire": "18",
        "women_safety": "17 / 112",
        "tourist": "112",
        "source": "France emergency services",
        "updated": "2026-07",
        "states": {},
    },
    "germany": {
        "country": "Germany",
        "aliases": ["berlin", "bavaria", "munich"],
        "universal": "112",
        "police": "110",
        "ambulance": "112",
        "fire": "112",
        "women_safety": "110 / 112",
        "tourist": "112",
        "source": "Germany emergency services",
        "updated": "2026-07",
        "states": {},
    },
    "italy": {
        "country": "Italy",
        "aliases": ["rome", "milan"],
        "universal": "112",
        "police": "112 / 113",
        "ambulance": "118",
        "fire": "115",
        "women_safety": "112 / 1522",
        "tourist": "112",
        "source": "Italy emergency services",
        "updated": "2026-07",
        "states": {},
    },
    "spain": {
        "country": "Spain",
        "aliases": ["madrid", "barcelona"],
        "universal": "112",
        "police": "112 / 091",
        "ambulance": "112 / 061",
        "fire": "112 / 080",
        "women_safety": "112 / 016",
        "tourist": "112",
        "source": "Spain emergency services",
        "updated": "2026-07",
        "states": {},
    },
    "united arab emirates": {
        "country": "United Arab Emirates",
        "aliases": ["uae", "dubai", "abu dhabi"],
        "universal": "999",
        "police": "999",
        "ambulance": "998",
        "fire": "997",
        "women_safety": "999",
        "tourist": "8004438",
        "source": "UAE emergency services",
        "updated": "2026-07",
        "states": {},
    },
    "singapore": {
        "country": "Singapore",
        "aliases": ["sg"],
        "universal": "999 / 995",
        "police": "999",
        "ambulance": "995",
        "fire": "995",
        "women_safety": "999",
        "tourist": "999",
        "source": "Singapore emergency services",
        "updated": "2026-07",
        "states": {},
    },
    "malaysia": {
        "country": "Malaysia",
        "aliases": ["kuala lumpur"],
        "universal": "999 / 112",
        "police": "999",
        "ambulance": "999",
        "fire": "994",
        "women_safety": "999 / 15999",
        "tourist": "999",
        "source": "Malaysia emergency services",
        "updated": "2026-07",
        "states": {},
    },
    "thailand": {
        "country": "Thailand",
        "aliases": ["bangkok", "phuket"],
        "universal": "191 / 1669",
        "police": "191",
        "ambulance": "1669",
        "fire": "199",
        "women_safety": "191 / 1300",
        "tourist": "1155",
        "source": "Thailand emergency and tourist police directory",
        "updated": "2026-07",
        "states": {},
    },
    "indonesia": {
        "country": "Indonesia",
        "aliases": ["bali", "jakarta"],
        "universal": "112",
        "police": "110",
        "ambulance": "118 / 119",
        "fire": "113",
        "women_safety": "110 / 112",
        "tourist": "112",
        "source": "Indonesia emergency services",
        "updated": "2026-07",
        "states": {},
    },
    "philippines": {
        "country": "Philippines",
        "aliases": ["manila", "cebu"],
        "universal": "911",
        "police": "911",
        "ambulance": "911",
        "fire": "911",
        "women_safety": "911",
        "tourist": "911",
        "source": "Philippines emergency services",
        "updated": "2026-07",
        "states": {},
    },
    "china": {
        "country": "China",
        "aliases": ["beijing", "shanghai", "guangzhou"],
        "universal": "110 / 119 / 120",
        "police": "110",
        "ambulance": "120",
        "fire": "119",
        "women_safety": "110",
        "tourist": "110",
        "source": "China emergency services",
        "updated": "2026-07",
        "states": {},
    },
    "south korea": {
        "country": "South Korea",
        "aliases": ["korea", "republic of korea", "seoul"],
        "universal": "112 / 119",
        "police": "112",
        "ambulance": "119",
        "fire": "119",
        "women_safety": "112",
        "tourist": "1330",
        "source": "South Korea emergency and visitor hotline directory",
        "updated": "2026-07",
        "states": {},
    },
    "bangladesh": {
        "country": "Bangladesh",
        "aliases": ["dhaka"],
        "universal": "999",
        "police": "999",
        "ambulance": "999 / 16263",
        "fire": "999",
        "women_safety": "999 / 109",
        "tourist": "999",
        "source": "Bangladesh emergency services",
        "updated": "2026-07",
        "states": {},
    },
    "nepal": {
        "country": "Nepal",
        "aliases": ["kathmandu"],
        "universal": "100 / 102 / 101",
        "police": "100",
        "ambulance": "102",
        "fire": "101",
        "women_safety": "100 / 1145",
        "tourist": "1144",
        "source": "Nepal emergency services",
        "updated": "2026-07",
        "states": {},
    },
    "sri lanka": {
        "country": "Sri Lanka",
        "aliases": ["colombo"],
        "universal": "119 / 110",
        "police": "119 / 118",
        "ambulance": "1990 / 110",
        "fire": "110",
        "women_safety": "119 / 1938",
        "tourist": "1912",
        "source": "Sri Lanka emergency services",
        "updated": "2026-07",
        "states": {},
    },
    "south africa": {
        "country": "South Africa",
        "aliases": ["cape town", "johannesburg"],
        "universal": "112",
        "police": "10111",
        "ambulance": "10177",
        "fire": "10177",
        "women_safety": "112 / 10111",
        "tourist": "112",
        "source": "South Africa emergency services",
        "updated": "2026-07",
        "states": {},
    },
    "brazil": {
        "country": "Brazil",
        "aliases": ["rio de janeiro", "sao paulo"],
        "universal": "190 / 192 / 193",
        "police": "190",
        "ambulance": "192",
        "fire": "193",
        "women_safety": "190 / 180",
        "tourist": "190",
        "source": "Brazil emergency services",
        "updated": "2026-07",
        "states": {},
    },
    "mexico": {
        "country": "Mexico",
        "aliases": ["mexico city", "cancun"],
        "universal": "911",
        "police": "911",
        "ambulance": "911",
        "fire": "911",
        "women_safety": "911",
        "tourist": "911",
        "source": "Mexico emergency services",
        "updated": "2026-07",
        "states": {},
    },
    "turkey": {
        "country": "Turkey",
        "aliases": ["turkiye", "istanbul"],
        "universal": "112",
        "police": "112",
        "ambulance": "112",
        "fire": "112",
        "women_safety": "112 / 183",
        "tourist": "112",
        "source": "Turkey emergency services",
        "updated": "2026-07",
        "states": {},
    },
    "saudi arabia": {
        "country": "Saudi Arabia",
        "aliases": ["riyadh", "jeddah"],
        "universal": "911 / 999",
        "police": "999",
        "ambulance": "997",
        "fire": "998",
        "women_safety": "999 / 1919",
        "tourist": "930",
        "source": "Saudi Arabia emergency services",
        "updated": "2026-07",
        "states": {},
    },
    "qatar": {
        "country": "Qatar",
        "aliases": ["doha"],
        "universal": "999",
        "police": "999",
        "ambulance": "999",
        "fire": "999",
        "women_safety": "999",
        "tourist": "106",
        "source": "Qatar emergency services",
        "updated": "2026-07",
        "states": {},
    },
}

WORLD_COUNTRY_ROWS = [
    ("afghanistan", "Afghanistan", "102 / 119", "102", "103", "101", "102", ["kabul"]),
    ("albania", "Albania", "112 / 129", "129", "127", "128", "112", ["tirana"]),
    ("algeria", "Algeria", "112 / 1548", "1548", "14", "14", "1548", ["algiers"]),
    ("andorra", "Andorra", "112", "110", "116", "118", "112", []),
    ("angola", "Angola", "112 / 113", "113", "112 / 116", "115", "113", ["luanda"]),
    ("antigua and barbuda", "Antigua and Barbuda", "911 / 999", "911 / 999", "911 / 999", "911 / 999", "911", []),
    ("argentina", "Argentina", "911", "101 / 911", "107 / 911", "100 / 911", "911 / 144", ["buenos aires"]),
    ("armenia", "Armenia", "112 / 911", "102", "103", "101", "112", ["yerevan"]),
    ("austria", "Austria", "112", "133", "144", "122", "112", ["vienna"]),
    ("azerbaijan", "Azerbaijan", "112", "102", "103", "101", "112", ["baku"]),
    ("bahamas", "Bahamas", "911 / 919", "911 / 919", "911 / 919", "911 / 919", "911", ["nassau"]),
    ("bahrain", "Bahrain", "999", "999", "999", "999", "999", ["manama"]),
    ("barbados", "Barbados", "211 / 511 / 311", "211", "511", "311", "211", ["bridgetown"]),
    ("belarus", "Belarus", "112", "102", "103", "101", "112", ["minsk"]),
    ("belgium", "Belgium", "112", "101", "100 / 112", "100 / 112", "112", ["brussels"]),
    ("belize", "Belize", "911", "911", "911", "90 / 911", "911", ["belmopan"]),
    ("benin", "Benin", "112 / 117", "117", "112", "118", "117", ["porto novo", "cotonou"]),
    ("bhutan", "Bhutan", "112", "113", "112", "110", "113", ["thimphu"]),
    ("bolivia", "Bolivia", "911", "110 / 911", "118 / 911", "119 / 911", "911", ["la paz", "sucre"]),
    ("bosnia and herzegovina", "Bosnia and Herzegovina", "112", "122", "124", "123", "112", ["sarajevo"]),
    ("botswana", "Botswana", "999 / 911", "999", "997", "998", "999", ["gaborone"]),
    ("brunei", "Brunei", "993 / 991 / 995", "993", "991", "995", "993", ["brunei darussalam", "bandar seri begawan"]),
    ("bulgaria", "Bulgaria", "112", "112 / 166", "112 / 150", "112 / 160", "112", ["sofia"]),
    ("burkina faso", "Burkina Faso", "112 / 17", "17", "112", "18", "17", ["ouagadougou"]),
    ("burundi", "Burundi", "117 / 112", "117", "112", "118", "117", ["bujumbura", "gitega"]),
    ("cabo verde", "Cabo Verde", "132 / 130 / 131", "132", "130", "131", "132", ["cape verde", "praia"]),
    ("cambodia", "Cambodia", "117 / 119 / 118", "117", "119", "118", "117", ["phnom penh"]),
    ("cameroon", "Cameroon", "117 / 112 / 118", "117", "112", "118", "117", ["yaounde", "douala"]),
    ("central african republic", "Central African Republic", "117 / 1220 / 118", "117", "1220", "118", "117", ["bangui"]),
    ("chad", "Chad", "17 / 15 / 18", "17", "15", "18", "17", ["ndjamena", "n djamena"]),
    ("chile", "Chile", "133 / 131 / 132", "133", "131", "132", "133", ["santiago"]),
    ("colombia", "Colombia", "123", "123 / 112", "123 / 125", "123 / 119", "123", ["bogota"]),
    ("comoros", "Comoros", "17 / 18", "17", "772-03-73", "18", "17", ["moroni"]),
    ("congo", "Republic of the Congo", "117 / 118", "117", "112", "118", "117", ["brazzaville"]),
    ("costa rica", "Costa Rica", "911", "911", "911", "911", "911", ["san jose"]),
    ("croatia", "Croatia", "112", "192 / 112", "194 / 112", "193 / 112", "112", ["zagreb"]),
    ("cuba", "Cuba", "106 / 104 / 105", "106", "104", "105", "106", ["havana"]),
    ("cyprus", "Cyprus", "112 / 199", "112 / 199", "112 / 199", "112 / 199", "112", ["nicosia"]),
    ("czechia", "Czechia", "112", "158", "155", "150", "112", ["czech republic", "prague"]),
    ("democratic republic of the congo", "Democratic Republic of the Congo", "112 / 117 / 118", "117", "112", "118", "117", ["drc", "kinshasa"]),
    ("denmark", "Denmark", "112", "112", "112", "112", "112", ["copenhagen"]),
    ("djibouti", "Djibouti", "17 / 19 / 18", "17", "19", "18", "17", []),
    ("dominica", "Dominica", "999 / 911", "999 / 911", "999 / 911", "999 / 911", "999", []),
    ("dominican republic", "Dominican Republic", "911", "911", "911", "911", "911", ["santo domingo"]),
    ("ecuador", "Ecuador", "911", "101 / 911", "131 / 911", "102 / 911", "911", ["quito"]),
    ("egypt", "Egypt", "112 / 122", "122", "123", "180", "122", ["cairo"]),
    ("el salvador", "El Salvador", "911", "911", "132", "913", "911", ["san salvador"]),
    ("equatorial guinea", "Equatorial Guinea", "112", "112", "112", "112", "112", ["malabo"]),
    ("eritrea", "Eritrea", "113 / 114 / 116", "113", "114", "116", "113", ["asmara"]),
    ("estonia", "Estonia", "112", "112", "112", "112", "112", ["tallinn"]),
    ("eswatini", "Eswatini", "999 / 977 / 933", "999", "977", "933", "999", ["swaziland", "mbabane"]),
    ("ethiopia", "Ethiopia", "911 / 991 / 907 / 939", "991 / 911", "907 / 911", "939 / 911", "911", ["addis ababa"]),
    ("fiji", "Fiji", "911 / 917 / 910", "911 / 917", "911", "910", "911", ["suva"]),
    ("finland", "Finland", "112", "112", "112", "112", "112", ["helsinki"]),
    ("gabon", "Gabon", "1730 / 1300 / 18", "1730", "1300", "18", "1730", ["libreville"]),
    ("gambia", "Gambia", "117 / 116 / 118", "117", "116", "118", "117", ["banjul"]),
    ("georgia", "Georgia", "112", "112", "112", "112", "112", ["tbilisi"]),
    ("ghana", "Ghana", "112 / 999", "999 / 112", "193 / 112", "192 / 112", "112", ["accra"]),
    ("greece", "Greece", "112", "100 / 112", "166 / 112", "199 / 112", "112", ["athens"]),
    ("grenada", "Grenada", "911", "911", "911", "911", "911", []),
    ("guatemala", "Guatemala", "110 / 128 / 122", "110", "128", "122", "110", ["guatemala city"]),
    ("guinea", "Guinea", "117 / 18", "117", "442-020", "18", "117", ["conakry"]),
    ("guinea bissau", "Guinea-Bissau", "117 / 119 / 118", "117", "119", "118", "117", ["bissau"]),
    ("guyana", "Guyana", "911 / 913 / 912", "911", "913", "912", "911", ["georgetown"]),
    ("haiti", "Haiti", "114 / 116 / 115", "114", "116", "115", "114", ["port au prince"]),
    ("honduras", "Honduras", "911", "911", "195", "198", "911", ["tegucigalpa"]),
    ("hungary", "Hungary", "112", "107 / 112", "104 / 112", "105 / 112", "112", ["budapest"]),
    ("iceland", "Iceland", "112", "112", "112", "112", "112", ["reykjavik"]),
    ("iran", "Iran", "110 / 115 / 125", "110", "115", "125", "110", ["tehran"]),
    ("iraq", "Iraq", "112 / 911", "104 / 911", "122 / 911", "115 / 911", "911", ["baghdad"]),
    ("ireland", "Ireland", "112 / 999", "112 / 999", "112 / 999", "112 / 999", "112", ["dublin"]),
    ("israel", "Israel", "100 / 101 / 102", "100", "101", "102", "100", ["tel aviv", "jerusalem"]),
    ("ivory coast", "Cote d'Ivoire", "111 / 180 / 185", "111", "185", "180", "111", ["cote d ivoire", "abidjan", "yamoussoukro"]),
    ("jamaica", "Jamaica", "119 / 110", "119", "110", "110", "119", ["kingston"]),
    ("jordan", "Jordan", "911", "911", "911", "911", "911", ["amman"]),
    ("kazakhstan", "Kazakhstan", "112", "102", "103", "101", "112", ["astana", "almaty"]),
    ("kenya", "Kenya", "999 / 112 / 911", "999 / 112 / 911", "999 / 112 / 911", "999 / 112 / 911", "999", ["nairobi"]),
    ("kiribati", "Kiribati", "999", "999", "994", "993", "999", ["tarawa"]),
    ("kosovo", "Kosovo", "112", "192", "194", "193", "112", ["pristina"]),
    ("kuwait", "Kuwait", "112", "112", "112", "112", "112", ["kuwait city"]),
    ("kyrgyzstan", "Kyrgyzstan", "112", "102", "103", "101", "112", ["bishkek"]),
    ("laos", "Laos", "1191 / 1195 / 1190", "1191", "1195", "1190", "1191", ["vientiane"]),
    ("latvia", "Latvia", "112", "110 / 112", "113 / 112", "112", "112", ["riga"]),
    ("lebanon", "Lebanon", "112 / 140 / 175", "112", "140", "175", "112", ["beirut"]),
    ("lesotho", "Lesotho", "112 / 123 / 121", "123", "121", "122", "123", ["maseru"]),
    ("liberia", "Liberia", "911", "911", "911", "911", "911", ["monrovia"]),
    ("libya", "Libya", "1515 / 193 / 190", "1515 / 193", "190", "1515", "193", ["tripoli"]),
    ("liechtenstein", "Liechtenstein", "112", "117", "144", "118", "112", ["vaduz"]),
    ("lithuania", "Lithuania", "112", "112", "112", "112", "112", ["vilnius"]),
    ("luxembourg", "Luxembourg", "112", "113", "112", "112", "112", []),
    ("madagascar", "Madagascar", "117 / 124 / 118", "117", "124", "118", "117", ["antananarivo"]),
    ("malawi", "Malawi", "997 / 998 / 999", "997", "998", "999", "997", ["lilongwe"]),
    ("maldives", "Maldives", "119 / 102 / 118", "119", "102", "118", "119", ["male"]),
    ("mali", "Mali", "17 / 15 / 18", "17", "15", "18", "17", ["bamako"]),
    ("malta", "Malta", "112", "112", "112", "112", "112", ["valletta"]),
    ("marshall islands", "Marshall Islands", "911", "911", "911", "911", "911", ["majuro"]),
    ("mauritania", "Mauritania", "117 / 101 / 118", "117", "101", "118", "117", ["nouakchott"]),
    ("mauritius", "Mauritius", "999 / 114 / 115", "999", "114", "115", "999", ["port louis"]),
    ("micronesia", "Micronesia", "911", "911", "911", "911", "911", ["federated states of micronesia", "palikir"]),
    ("moldova", "Moldova", "112", "902 / 112", "903 / 112", "901 / 112", "112", ["chisinau"]),
    ("monaco", "Monaco", "112", "17", "18", "18", "112", []),
    ("mongolia", "Mongolia", "102 / 103 / 101", "102", "103", "101", "102", ["ulaanbaatar"]),
    ("montenegro", "Montenegro", "112", "122", "124", "123", "112", ["podgorica"]),
    ("morocco", "Morocco", "19 / 15", "19 / 177", "15", "15", "19", ["rabat", "casablanca"]),
    ("mozambique", "Mozambique", "119 / 117 / 198", "119", "117", "198", "119", ["maputo"]),
    ("myanmar", "Myanmar", "199 / 192 / 191", "199", "192", "191", "199", ["burma", "yangon", "naypyidaw"]),
    ("namibia", "Namibia", "10111 / 211111", "10111", "211111", "211111", "10111", ["windhoek"]),
    ("nauru", "Nauru", "110 / 111 / 112", "110", "111", "112", "110", []),
    ("netherlands", "Netherlands", "112", "112", "112", "112", "112", ["holland", "amsterdam"]),
    ("nicaragua", "Nicaragua", "118 / 128 / 115", "118", "128", "115", "118", ["managua"]),
    ("niger", "Niger", "17 / 15 / 18", "17", "15", "18", "17", ["niamey"]),
    ("nigeria", "Nigeria", "112 / 199", "112 / 199", "112 / 199", "112 / 199", "112", ["abuja", "lagos"]),
    ("north korea", "North Korea", "110 / 119", "110", "119", "119", "110", ["dprk", "pyongyang"]),
    ("north macedonia", "North Macedonia", "112", "192", "194", "193", "112", ["skopje", "macedonia"]),
    ("norway", "Norway", "112 / 113 / 110", "112", "113", "110", "112", ["oslo"]),
    ("oman", "Oman", "9999", "9999", "9999", "9999", "9999", ["muscat"]),
    ("pakistan", "Pakistan", "15 / 1122 / 16", "15", "1122", "16", "15", ["islamabad", "karachi", "lahore"]),
    ("palau", "Palau", "911", "911", "911", "911", "911", ["ngerulmud"]),
    ("palestine", "Palestine", "100 / 101 / 102", "100", "101", "102", "100", ["west bank", "gaza"]),
    ("panama", "Panama", "911", "911 / 104", "911", "103", "911", ["panama city"]),
    ("papua new guinea", "Papua New Guinea", "000 / 111", "000 / 112", "111", "110", "000", ["port moresby"]),
    ("paraguay", "Paraguay", "911", "912 / 911", "141 / 911", "132 / 911", "911", ["asuncion"]),
    ("peru", "Peru", "911 / 105 / 106 / 116", "105 / 911", "106 / 911", "116 / 911", "911", ["lima"]),
    ("poland", "Poland", "112", "997 / 112", "999 / 112", "998 / 112", "112", ["warsaw"]),
    ("portugal", "Portugal", "112", "112", "112", "112", "112", ["lisbon"]),
    ("romania", "Romania", "112", "112", "112", "112", "112", ["bucharest"]),
    ("russia", "Russia", "112", "102", "103", "101", "112", ["russian federation", "moscow"]),
    ("rwanda", "Rwanda", "112 / 912", "112", "912", "112", "112", ["kigali"]),
    ("saint kitts and nevis", "Saint Kitts and Nevis", "911", "911", "911", "911", "911", []),
    ("saint lucia", "Saint Lucia", "911 / 999", "911 / 999", "911 / 999", "911 / 999", "911", []),
    ("saint vincent and the grenadines", "Saint Vincent and the Grenadines", "911 / 999", "911 / 999", "911 / 999", "911 / 999", "911", []),
    ("samoa", "Samoa", "999", "999", "996", "994", "999", ["apia"]),
    ("san marino", "San Marino", "112", "113", "118", "115", "112", []),
    ("sao tome and principe", "Sao Tome and Principe", "112 / 2222222", "112", "112", "112", "112", ["sao tome"]),
    ("senegal", "Senegal", "17 / 15 / 18", "17", "15", "18", "17", ["dakar"]),
    ("serbia", "Serbia", "112", "192", "194", "193", "112", ["belgrade"]),
    ("seychelles", "Seychelles", "999 / 151", "999", "151", "999", "999", ["victoria"]),
    ("sierra leone", "Sierra Leone", "999 / 112", "999", "999", "999", "999", ["freetown"]),
    ("slovakia", "Slovakia", "112", "158", "155", "150", "112", ["bratislava"]),
    ("slovenia", "Slovenia", "112", "113", "112", "112", "112", ["ljubljana"]),
    ("solomon islands", "Solomon Islands", "999", "999", "911", "988", "999", ["honiara"]),
    ("somalia", "Somalia", "888 / 999", "888 / 999", "999", "999", "999", ["mogadishu"]),
    ("south sudan", "South Sudan", "999 / 777", "777", "999", "999", "777", ["juba"]),
    ("sudan", "Sudan", "999", "999", "999", "999", "999", ["khartoum"]),
    ("suriname", "Suriname", "115 / 113 / 110", "115", "113", "110", "115", ["paramaribo"]),
    ("sweden", "Sweden", "112", "112", "112", "112", "112", ["stockholm"]),
    ("switzerland", "Switzerland", "112", "117", "144", "118", "112", ["zurich", "bern", "geneva"]),
    ("syria", "Syria", "112 / 110 / 113", "112 / 110", "110", "113", "112", ["damascus"]),
    ("taiwan", "Taiwan", "110 / 119", "110", "119", "119", "110", ["taipei"]),
    ("tajikistan", "Tajikistan", "112", "102", "103", "101", "112", ["dushanbe"]),
    ("tanzania", "Tanzania", "112 / 999", "112 / 999", "112 / 999", "112 / 999", "112", ["dar es salaam", "dodoma"]),
    ("timor leste", "Timor-Leste", "112 / 110 / 115", "112 / 110", "115", "115", "112", ["east timor", "dili"]),
    ("togo", "Togo", "117 / 118", "117", "8200", "118", "117", ["lome"]),
    ("tonga", "Tonga", "911", "911", "911", "911", "911", ["nukualofa"]),
    ("trinidad and tobago", "Trinidad and Tobago", "999 / 990 / 811", "999", "811", "990", "999", ["port of spain"]),
    ("tunisia", "Tunisia", "197 / 190 / 198", "197", "190", "198", "197", ["tunis"]),
    ("turkmenistan", "Turkmenistan", "112 / 02 / 03 / 01", "02", "03", "01", "112", ["ashgabat"]),
    ("tuvalu", "Tuvalu", "911", "911", "911", "911", "911", ["funafuti"]),
    ("uganda", "Uganda", "999 / 112", "999 / 112", "999 / 112", "999 / 112", "999", ["kampala"]),
    ("ukraine", "Ukraine", "112", "102", "103", "101", "112", ["kyiv", "kiev"]),
    ("uruguay", "Uruguay", "911", "911 / 109", "105 / 911", "104 / 911", "911", ["montevideo"]),
    ("uzbekistan", "Uzbekistan", "112", "102", "103", "101", "112", ["tashkent"]),
    ("vanuatu", "Vanuatu", "112 / 111", "111", "112", "113", "111", ["port vila"]),
    ("vatican city", "Vatican City", "112", "112", "118", "115", "112", ["holy see", "vatican"]),
    ("venezuela", "Venezuela", "911 / 171", "911 / 171", "911 / 171", "911 / 171", "911", ["caracas"]),
    ("vietnam", "Vietnam", "113 / 115 / 114", "113", "115", "114", "113", ["hanoi", "ho chi minh"]),
    ("yemen", "Yemen", "194 / 191", "194", "191", "191", "194", ["sanaa"]),
    ("zambia", "Zambia", "999 / 991 / 992", "999", "991", "993", "999", ["lusaka"]),
    ("zimbabwe", "Zimbabwe", "999 / 995 / 993", "995", "994", "993", "995", ["harare"]),
]

for key, country, universal, police, ambulance, fire, women_safety, aliases in WORLD_COUNTRY_ROWS:
    COUNTRY_PROFILES.setdefault(
        key,
        {
            "country": country,
            "aliases": aliases,
            "universal": universal,
            "police": police,
            "ambulance": ambulance,
            "fire": fire,
            "women_safety": women_safety,
            "tourist": universal,
            "source": "World emergency telephone directory; state/region searches use national numbers unless an override is available",
            "updated": "2026-07",
            "states": {},
        },
    )

STATE_REGION_COUNTRY = {
    **{
        state: "united states"
        for state in [
            "alabama", "alaska", "arizona", "arkansas", "california", "colorado", "connecticut", "delaware",
            "florida", "georgia", "hawaii", "idaho", "illinois", "indiana", "iowa", "kansas", "kentucky",
            "louisiana", "maine", "maryland", "massachusetts", "michigan", "minnesota", "mississippi",
            "missouri", "montana", "nebraska", "nevada", "new hampshire", "new jersey", "new mexico",
            "new york", "north carolina", "north dakota", "ohio", "oklahoma", "oregon", "pennsylvania",
            "rhode island", "south carolina", "south dakota", "tennessee", "texas", "utah", "vermont",
            "virginia", "washington", "west virginia", "wisconsin", "wyoming", "district of columbia",
        ]
    },
    **{
        state: "india"
        for state in [
            "andhra pradesh", "arunachal pradesh", "assam", "bihar", "chhattisgarh", "goa", "gujarat",
            "haryana", "himachal pradesh", "jharkhand", "karnataka", "kerala", "madhya pradesh",
            "maharashtra", "manipur", "meghalaya", "mizoram", "nagaland", "odisha", "punjab",
            "rajasthan", "sikkim", "tamil nadu", "telangana", "tripura", "uttar pradesh",
            "uttarakhand", "west bengal", "delhi", "jammu and kashmir", "ladakh", "puducherry",
            "chandigarh", "andaman and nicobar islands", "lakshadweep", "dadra and nagar haveli",
            "daman and diu",
        ]
    },
    **{
        province: "canada"
        for province in [
            "alberta", "british columbia", "manitoba", "new brunswick", "newfoundland and labrador",
            "northwest territories", "nova scotia", "nunavut", "ontario", "prince edward island",
            "quebec", "saskatchewan", "yukon",
        ]
    },
    **{
        region: "australia"
        for region in [
            "new south wales", "queensland", "south australia", "tasmania", "victoria",
            "western australia", "australian capital territory", "northern territory",
        ]
    },
    **{
        region: "germany"
        for region in [
            "baden wurttemberg", "baden-wurttemberg", "bavaria", "bayern", "berlin", "brandenburg",
            "bremen", "hamburg", "hesse", "hessen", "lower saxony", "mecklenburg vorpommern",
            "north rhine westphalia", "rheinland pfalz", "saarland", "saxony", "saxony anhalt",
            "schleswig holstein", "thuringia",
        ]
    },
    **{
        region: "brazil"
        for region in [
            "acre", "alagoas", "amapa", "amazonas", "bahia", "ceara", "distrito federal",
            "espirito santo", "goias", "maranhao", "mato grosso", "mato grosso do sul",
            "minas gerais", "para", "paraiba", "parana", "pernambuco", "piaui", "rio de janeiro",
            "rio grande do norte", "rio grande do sul", "rondonia", "roraima", "santa catarina",
            "sao paulo", "sergipe", "tocantins",
        ]
    },
    **{
        region: "mexico"
        for region in [
            "aguascalientes", "baja california", "baja california sur", "campeche", "chiapas",
            "chihuahua", "coahuila", "colima", "durango", "guanajuato", "guerrero", "hidalgo",
            "jalisco", "mexico state", "michoacan", "morelos", "nayarit", "nuevo leon", "oaxaca",
            "puebla", "queretaro", "quintana roo", "san luis potosi", "sinaloa", "sonora", "tabasco",
            "tamaulipas", "tlaxcala", "veracruz", "yucatan", "zacatecas",
        ]
    },
    "england": "united kingdom",
    "scotland": "united kingdom",
    "wales": "united kingdom",
    "northern ireland": "united kingdom",
    "dubai": "united arab emirates",
    "abu dhabi": "united arab emirates",
    "sharjah": "united arab emirates",
    "ajman": "united arab emirates",
    "umm al quwain": "united arab emirates",
    "ras al khaimah": "united arab emirates",
    "fujairah": "united arab emirates",
}

COORDINATE_REGIONS = [
    (11.3, 18.8, 74.0, 78.8, "India", "Karnataka"),
    (6.0, 37.5, 68.0, 98.5, "India", ""),
    (24.0, 49.5, -125.0, -66.0, "United States", ""),
    (41.0, 84.0, -141.0, -52.0, "Canada", ""),
    (49.5, 59.0, -8.6, 2.2, "United Kingdom", ""),
    (41.0, 51.5, -5.5, 9.8, "France", ""),
    (47.0, 55.5, 5.5, 15.5, "Germany", ""),
    (35.0, 47.5, 6.0, 19.0, "Italy", ""),
    (27.5, 44.5, -18.5, 4.5, "Spain", ""),
    (20.0, 46.0, 122.0, 154.0, "Japan", ""),
    (33.0, 39.5, 124.0, 132.0, "South Korea", ""),
    (18.0, 54.0, 73.0, 135.5, "China", ""),
    (1.1, 1.6, 103.5, 104.1, "Singapore", ""),
    (2.0, 7.5, 99.5, 120.5, "Malaysia", ""),
    (5.0, 21.5, 97.0, 106.5, "Thailand", ""),
    (-11.0, 6.5, 95.0, 141.5, "Indonesia", ""),
    (22.0, 26.5, 51.0, 57.5, "United Arab Emirates", ""),
    (-44.0, -10.0, 112.0, 154.0, "Australia", ""),
    (-48.0, -33.0, 165.0, 179.9, "New Zealand", ""),
    (-35.0, -22.0, 16.0, 33.0, "South Africa", ""),
    (-34.0, 5.5, -74.0, -34.0, "Brazil", ""),
    (14.0, 33.5, -118.5, -86.0, "Mexico", ""),
]


def clean_key(value):
    return " ".join(str(value or "").strip().lower().replace("_", " ").replace("-", " ").split())


def normalize_category(category):
    key = clean_key(category)
    return CATEGORY_ALIASES.get(key, key if key in CATEGORY_LABELS else "universal")


def country_options():
    return sorted(profile["country"] for profile in COUNTRY_PROFILES.values())


def infer_region_from_coordinates(lat, lon):
    try:
        lat = float(lat)
        lon = float(lon)
    except (TypeError, ValueError):
        return {}

    for min_lat, max_lat, min_lon, max_lon, country, state in COORDINATE_REGIONS:
        if min_lat <= lat <= max_lat and min_lon <= lon <= max_lon:
            return {"country": country, "state": state}
    return {}


def resolve_country_key(country=None, state=None):
    country_key = clean_key(country)
    state_key = clean_key(state)
    haystacks = [country_key, state_key]

    if country_key in STATE_REGION_COUNTRY:
        return STATE_REGION_COUNTRY[country_key]
    if state_key in STATE_REGION_COUNTRY:
        return STATE_REGION_COUNTRY[state_key]

    for key, profile in COUNTRY_PROFILES.items():
        names = [key, clean_key(profile["country"]), *[clean_key(alias) for alias in profile.get("aliases", [])]]
        if country_key and country_key in names:
            return key
        if state_key and (state_key in names or state_key in profile.get("states", {})):
            return key

    for text in haystacks:
        if not text:
            continue
        for key, profile in COUNTRY_PROFILES.items():
            names = [key, clean_key(profile["country"]), *[clean_key(alias) for alias in profile.get("aliases", [])]]
            if any(name and (name in text or text in name) for name in names):
                return key

    return None


def emergency_profile(country=None, state=None, category=None):
    country_key = resolve_country_key(country, state)
    base = deepcopy(DEFAULT_PROFILE)
    confidence = "fallback"
    if country_key:
        selected_country = deepcopy(COUNTRY_PROFILES[country_key])
        base.update({k: v for k, v in selected_country.items() if k != "aliases"})
        confidence = "country"

    state_key = clean_key(state)
    state_match = None
    if state_key:
        states = base.get("states") or {}
        for key, override in states.items():
            if state_key == key or state_key in key or key in state_key:
                base.update(override)
                state_match = key.title()
                confidence = "state"
                break
        if country_key and not state_match:
            state_match = state
            confidence = "state_inherited"

    category_key = normalize_category(category)
    helplines = {key: base.get(key) or base["universal"] for key in CATEGORY_LABELS}
    selected_number = helplines.get(category_key) or helplines["universal"]

    return {
        "country": base["country"],
        "country_key": country_key,
        "state": state_match or (state or ""),
        "category": category_key,
        "category_label": CATEGORY_LABELS[category_key],
        "number": selected_number,
        "helplines": helplines,
        "categories": CATEGORY_LABELS,
        "source": base.get("source", DEFAULT_PROFILE["source"]),
        "updated": base.get("updated", DEFAULT_PROFILE["updated"]),
        "confidence": confidence,
        "realtime": False,
        "note": "Use the phone dialer immediately in life-threatening danger. State/region searches use national emergency numbers unless a verified local override is available.",
    }


def lookup_emergency_number(country=None, state=None, category=None):
    return emergency_profile(country=country, state=state, category=category)["number"]


def emergency_contacts_for_category(category=None, country=None, state=None):
    profile = emergency_profile(country=country, state=state, category=category)
    category_key = profile["category"]
    contacts = [
        {
            "name": profile["category_label"],
            "phone": profile["number"],
            "category": category_key,
            "source": profile["source"],
        }
    ]
    universal = profile["helplines"]["universal"]
    if universal != profile["number"]:
        contacts.append(
            {
                "name": "Universal Emergency",
                "phone": universal,
                "category": "universal",
                "source": profile["source"],
            }
        )
    return contacts
