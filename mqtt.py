from umqtt import simple
import settings
import time
import main

_debug_mode = False


def debug_mode(enabled):
    global _debug_mode

    _debug_mode = enabled


TOPIC_HELLO_WHOS_THERE = "hello/whos-there"
TOPIC_BASE = f"devices/{settings.MQTT_CLIENT_ID}"
TOPIC_PING = f"{TOPIC_BASE}/ping"
TOPIC_PONG = f"{TOPIC_BASE}/pong"
TOPIC_TIME_GET = f"{TOPIC_BASE}/time/get"
TOPIC_TIME_NTP = f"{TOPIC_BASE}/time/ntp"
TOPIC_REFRESH = f"{TOPIC_BASE}/refresh"
TOPIC_REFRESH_STARTED = f"{TOPIC_BASE}/refresh/started"
TOPIC_REFRESH_FINISHED = f"{TOPIC_BASE}/refresh/finished"
TOPIC_WEATHER_REFRESH = f"{TOPIC_BASE}/weather/refresh"


_client: simple.MQTTClient | None = None


def _subscribe():
    def sub(topic):
        print("Subscribe: ", topic)
        _client.subscribe(topic)

    sub(TOPIC_HELLO_WHOS_THERE)
    sub(TOPIC_PING)
    sub(TOPIC_TIME_GET)
    sub(TOPIC_TIME_NTP)
    sub(TOPIC_REFRESH)
    sub(TOPIC_WEATHER_REFRESH)


def _safe_mqtt_message(topic, msg):
    try:
        _mqtt_message(topic, msg)
    except Exception as e:
        print("Failed to process MQTT message.", topic, msg, e)


def _mqtt_message(topic, msg):
    print("Message received", topic, msg)
    topic = topic.decode()
    msg = msg.decode()
    if topic == TOPIC_HELLO_WHOS_THERE:
        _client.publish("hello", settings.MQTT_CLIENT_ID)
    elif topic == TOPIC_PING:
        _client.publish(TOPIC_PONG, f"{time.localtime()}: {msg}")
    elif topic == TOPIC_TIME_GET:
        _client.publish(msg, str(time.localtime()))
    elif topic == TOPIC_TIME_NTP:
        main.set_time(True)
        _client.publish(msg, str(time.localtime()))
    elif topic == TOPIC_REFRESH:
        main.update()
    elif topic == TOPIC_WEATHER_REFRESH:
        main.refresh_weather()
        _client.publish(msg, str(main.load_weather()))
    elif _debug_mode:
        print(f"Unknown topic: {topic}")


def pump():
    if _debug_mode:
        print("MQTT message pump", _client)

    if _client is not None:
        try:
            _client.check_msg()
        except Exception as e:
            if _debug_mode:
                print("Failed to process MQTT message pump", e)


def publish(topic: str, payload: str):
    if _debug_mode:
        print("Publish to topic", topic, payload)

    if _client is not None:
        try:
            _client.publish(topic, payload)
        except Exception as e:
            print(f"Error sending message: {e}")


def start():
    global _client

    if _client is None:
        _client = simple.MQTTClient(
            settings.MQTT_CLIENT_ID,
            settings.MQTT_HOST,
            user=settings.MQTT_USER,
            password=settings.MQTT_PASSWD,
        )
        _client.set_last_will("last-will", settings.MQTT_CLIENT_ID)
        _client.set_callback(_safe_mqtt_message)

    def connect():
        _client.connect()
        _client.publish("hello", settings.MQTT_CLIENT_ID)
        _subscribe()

    retries = 0
    while True:
        retries += 1

        try:
            connect()
            break
        except OSError as e:
            if retries >= 6:
                print(f"Failed to connect to MQTT. Error: {e}")
                break

            if e.errno != 104:
                raise e

        time.sleep(5)


def stop():
    global _client

    if _client is not None:
        _client.disconnect()
        _client = None
