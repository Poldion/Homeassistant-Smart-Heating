import os, shutil
from datetime import timedelta
import pytest
from homeassistant.setup import async_setup_component
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import async_fire_time_changed

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

@pytest.fixture
async def env(hass, freezer):
    await hass.config.async_set_time_zone("Europe/Berlin")
    freezer.move_to("2026-10-13 12:00:00+02:00")
    d = hass.config.path("blueprints/automation/smart_heating")
    os.makedirs(d, exist_ok=True)
    shutil.copy(os.path.join(REPO, "blueprints/automation/smart_heating/room_heating.yaml"), d)
    calls = []
    async def rec(call):
        calls.append((call.service, dict(call.data)))
        for e in call.data["entity_id"]:
            st = hass.states.get(e); attrs = dict(st.attributes)
            if call.service == "turn_off":
                hass.states.async_set(e, "off", attrs)
            else:
                attrs["temperature"] = call.data["temperature"]
                hass.states.async_set(e, call.data.get("hvac_mode", st.state), attrs)
    for s in ("turn_off", "set_temperature"):
        hass.services.async_register("climate", s, rec)
    hass.states.async_set("climate.wz", "heat", {"temperature": 17})
    for e in ["binary_sensor.motion", "binary_sensor.door", "binary_sensor.bed"]:
        hass.states.async_set(e, "off")
    hass.states.async_set("person.a", "home"); hass.states.async_set("person.b", "home")
    hass.states.async_set("input_boolean.season", "on")
    home = (52.5200, 13.4050)
    hass.states.async_set("zone.home", "0", {"latitude": home[0], "longitude": home[1], "radius": 100, "friendly_name": "Home"})
    hass.states.async_set("zone.umgebung", "0", {"latitude": home[0], "longitude": home[1], "radius": 3000, "friendly_name": "Umgebung"})

    async def setup(**extra):
        inp = {
            "climate_entities": ["climate.wz"],
            "motion_sensors": ["binary_sensor.motion"],
            "door_sensors": ["binary_sensor.door"],
            "presence_entities": ["person.a", "person.b"],
            "bed_sensors": ["binary_sensor.bed"],
            "enable_entities": ["input_boolean.season"],
            "bed_window_start": "21:00:00", "bed_window_end": "09:00:00",
        }
        inp.update(extra)
        assert await async_setup_component(hass, "automation", {"automation": [{
            "id": "t1", "alias": "wz", "use_blueprint": {"path": "smart_heating/room_heating.yaml", "input": inp}}]})
        await hass.async_block_till_done()
        assert hass.states.get("automation.wz").state == "on"

    async def tick(minutes):
        freezer.tick(timedelta(minutes=minutes))
        async_fire_time_changed(hass)
        await hass.async_block_till_done()

    async def st(e, s):
        hass.states.async_set(e, s); await hass.async_block_till_done()

    def cur():
        c = hass.states.get("climate.wz")
        return "off" if c.state == "off" else c.attributes["temperature"]
    return hass, setup, tick, st, cur, calls, freezer


async def test_motion_and_door(env):
    hass, setup, tick, st, cur, calls, _ = env
    await setup()
    await st("binary_sensor.motion", "on"); assert cur() == 21
    await st("binary_sensor.motion", "off"); await tick(10); assert cur() == 21
    await st("binary_sensor.motion", "on"); await st("binary_sensor.motion", "off")
    await tick(14); assert cur() == 21
    await tick(1.5); assert cur() == 17          # hold 15 min elapsed
    await st("binary_sensor.motion", "on"); assert cur() == 21
    await st("binary_sensor.door", "on"); await tick(5); assert cur() == 21
    await st("binary_sensor.motion", "off"); await st("binary_sensor.motion", "on")
    await tick(5.5); assert cur() == 17          # door open 10 min
    await st("binary_sensor.door", "off"); assert cur() == 21  # motion still on
    n = len(calls)
    await st("binary_sensor.motion", "off"); await st("binary_sensor.motion", "on")
    assert len(calls) == n                        # no redundant calls


async def test_presence(env):
    hass, setup, tick, st, cur, calls, _ = env
    await setup()
    await st("binary_sensor.motion", "on"); assert cur() == 21
    await st("person.a", "not_home"); await tick(20); assert cur() == 21
    await st("person.b", "not_home"); await tick(5)
    await st("person.b", "Arbeit"); await tick(4); assert cur() == 21  # delay counts from leaving
    await tick(1.5); assert cur() == 16
    await st("person.a", "home"); assert cur() == 21


async def test_bed_night(env):
    hass, setup, tick, st, cur, calls, freezer = env
    freezer.move_to("2026-10-13 22:00:00+02:00")
    await setup()
    await st("binary_sensor.motion", "on"); assert cur() == 21
    await st("binary_sensor.bed", "on"); await tick(10); assert cur() == 21
    await tick(5.5); assert cur() == "off"
    await st("binary_sensor.bed", "off"); await st("binary_sensor.motion", "off"); await st("binary_sensor.motion", "on")
    await tick(2); assert cur() == "off"          # toilet grace
    await st("binary_sensor.bed", "on"); await tick(3); assert cur() == "off"
    await st("binary_sensor.bed", "off"); await tick(5.5)
    assert cur() == 21 and calls[-1][1].get("hvac_mode") == "heat"


async def test_bed_midday_ignored_and_window_start(env):
    hass, setup, tick, st, cur, calls, freezer = env
    freezer.move_to("2026-10-13 20:30:00+02:00")
    await setup()
    await st("binary_sensor.motion", "on")
    await st("binary_sensor.bed", "on"); await tick(20); assert cur() == 21
    await tick(10.5); assert cur() == "off"       # 21:00 window start
    freezer.move_to("2026-10-14 08:59:30+02:00")
    async_fire_time_changed(hass); await hass.async_block_till_done()
    await tick(1); assert cur() == 21             # 09:00 window end


async def test_night_temperature_and_disabled(env):
    hass, setup, tick, st, cur, calls, freezer = env
    freezer.move_to("2026-10-13 23:00:00+02:00")
    await setup(night_action="temperature", night_temperature=15.5)
    await st("binary_sensor.motion", "on")
    await st("binary_sensor.bed", "on"); await tick(16); assert cur() == 15.5
    await st("input_boolean.season", "off"); assert cur() == "off"
    await st("binary_sensor.bed", "off"); await tick(10); assert cur() == "off"
    await st("input_boolean.season", "on"); assert cur() == 21


async def test_minimal_inputs(env):
    hass, setup, tick, st, cur, calls, _ = env
    await setup(door_sensors=[], presence_entities=[], bed_sensors=[], enable_entities=[])
    await st("binary_sensor.motion", "on"); assert cur() == 21


def km_north(km):
    return {"latitude": 52.5200 + km / 111.195, "longitude": 13.4050, "gps_accuracy": 20}


async def test_presence_zone_gps(env):
    hass, setup, tick, st, cur, calls, _ = env
    await setup(presence_entities=["person.a"], presence_zones=["zone.umgebung"])
    await st("binary_sensor.motion", "on"); assert cur() == 21

    async def gps(state, km):
        hass.states.async_set("person.a", state, km_north(km)); await hass.async_block_till_done()

    await gps("not_home", 1); await tick(20); assert cur() == 21       # shopping nearby
    await gps("Supermarkt", 1.5); await tick(20); assert cur() == 21   # nested zone
    await gps("not_home", 5); await tick(5)                            # left Umgebung (state unchanged)
    await st("binary_sensor.motion", "off"); await st("binary_sensor.motion", "on")
    assert cur() == 21                                                 # still within delay
    await tick(5.5); assert cur() == 16                                # away after 10 min
    await st("binary_sensor.motion", "off"); await st("binary_sensor.motion", "on")
    assert cur() == 16                                                 # pet motion keeps away
    await gps("not_home", 2); assert cur() == 21                       # back in Umgebung
    await gps("home", 0); assert cur() == 21


async def test_disabled_turns_off(env):
    hass, setup, tick, st, cur, calls, _ = env
    await setup()
    await st("binary_sensor.motion", "on"); assert cur() == 21
    await st("input_boolean.season", "off"); assert cur() == "off"
    n = len(calls)
    await st("binary_sensor.motion", "off"); await st("binary_sensor.motion", "on")
    assert cur() == "off" and len(calls) == n                 # stays off, no extra calls
    await st("input_boolean.season", "on"); assert cur() == 21


async def test_disabled_keep_option(env):
    hass, setup, tick, st, cur, calls, _ = env
    await setup(disabled_turn_off=False)
    await st("binary_sensor.motion", "on"); assert cur() == 21
    await st("input_boolean.season", "off"); assert cur() == 21  # left untouched


async def test_door_only_room(env):
    hass, setup, tick, st, cur, calls, _ = env
    await setup(motion_sensors=[], door_closed_minutes=3)
    assert cur() == 17
    await tick(0.1)
    hass.states.async_set("binary_sensor.door", "on"); await hass.async_block_till_done()
    await st("binary_sensor.door", "off"); assert cur() == 17          # closed < 3 min
    await tick(2); assert cur() == 17
    await tick(1.5); assert cur() == 21                                # closed 3 min -> heat
    await st("binary_sensor.door", "on"); await tick(2)
    await st("binary_sensor.door", "off"); assert cur() == 21          # short opening ignored
    await st("binary_sensor.door", "on"); await tick(10.5); assert cur() == 17  # open 10 min
    await st("binary_sensor.door", "off"); await tick(1); assert cur() == 17
    await tick(2.5); assert cur() == 21


async def test_door_closed_delay_with_motion(env):
    hass, setup, tick, st, cur, calls, _ = env
    await setup(door_closed_minutes=2)
    await tick(2.5)
    await st("binary_sensor.motion", "on"); assert cur() == 21         # door closed > 2 min
    await st("binary_sensor.door", "on"); await tick(10.5); assert cur() == 17
    await st("binary_sensor.door", "off"); assert cur() == 17          # motion, but closed < 2 min
    await tick(2.5); assert cur() == 21
