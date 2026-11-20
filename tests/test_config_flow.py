"""Optional entity selectors in the options flow must accept an empty value.

Regression: the base EntitySelector rejects "" ("neither a valid entity ID nor a
valid UUID"), so a whole options section could not be saved whenever any optional
entity field was left blank. The _OptEntity wrapper fixes that while keeping the
selector type (so the UI still renders an entity picker)."""

import voluptuous as vol

from custom_components.ampx import config_flow as cf


def test_optional_entity_accepts_empty_string():
    from custom_components.ampx.const import CONF_MODE, CONF_SOC

    schema = cf.section_schema("energy", {})
    # The MCP options path submits "" for untouched entity fields; this must validate.
    out = schema({CONF_SOC: "", CONF_MODE: ""})
    assert out[CONF_SOC] == ""
    assert out[CONF_MODE] == ""


def test_optional_entity_still_validates_real_id():
    sel = cf._entity("sensor")
    assert sel("sensor.ness_battery_percentage") == "sensor.ness_battery_percentage"
    assert sel("") == ""
    assert sel(None) == ""


def test_multiple_entity_empty_is_list():
    sel = cf._entity("calendar", multiple=True)
    assert sel([]) == []
    assert sel("") == []
