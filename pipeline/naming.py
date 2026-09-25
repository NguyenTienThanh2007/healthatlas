from __future__ import annotations

import re


SPECIAL_NAMES = {
    "CountryID": "country_id",
    "RegionID": "region_id",
    "AntigenID": "antigen_id",
    "PersonaID": "persona_id",
    "TeamMemberID": "team_member_id",
    "economyID": "economy_id",
}


def to_snake_case(name: str) -> str:
    if name in SPECIAL_NAMES:
        return SPECIAL_NAMES[name]

    value = name.replace("-", "_").replace(" ", "_")
    value = re.sub(r"(?<!^)(?=[A-Z])", "_", value)
    value = re.sub(r"_+", "_", value)
    return value.lower().strip("_")
