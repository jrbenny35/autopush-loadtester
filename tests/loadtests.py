import base64
import os
import uuid
from urllib.parse import urlparse, urljoin

import aiohttp
import asyncio

from molotov import scenario, get_var


@scenario(weight=80)
async def test_basic(session):
    """Basic test
    
    Connect to websocket
    Register
    Send a Notification
    Check notification matches
    Disconnect
    """
    URLS = get_var("config")
    encrypted_data = "aLongStringOfEncryptedThings"
    headers = {"TTL": "60", "Content-Encoding": "aes128gcm"}
    channel_id = str(uuid.uuid4())
    async with session.ws_connect(
        f'{URLS["push_server"]}:443',
        headers={"Origin": "http://localhost:1337"},
        ssl=False,
    ) as ws:
        await ws.send_json(dict(messageType="hello", use_webpush=True))
        hello_msg = await ws.receive_json()
        assert hello_msg["messageType"] == "hello"
        await ws.send_json(dict(messageType="register", channelID=channel_id))
        msg1 = await ws.receive_json()
        # switch to rust endpoint
        if os.getenv("AUTOPUSH_RUST_SERVER") and (os.getenv("AUTOPUSH_ENV") != "dev"):
            path = urlparse(msg1["pushEndpoint"]).path
            endpoint_url = urljoin(URLS["rs_server_url"], path)
        else:
            endpoint_url = msg1["pushEndpoint"]
        # Send a notification
        async with session.post(
            endpoint_url,
            headers=headers,
            data=base64.urlsafe_b64decode(encrypted_data),
            ssl=False,
        ) as conn:
            assert conn.status == 201
        # Receive notification
        msg2 = await ws.receive_json()
        assert msg2["data"] == encrypted_data
        # Acknowledge notification
        await ws.send_json(dict(messageType="ack", updates=dict(channelID=channel_id)))
        assert ws.exception() == None
        await ws.close()


@scenario(weight=80)
async def test_basic_topic(session):
    """Basic test with a topic
    
    Connect to websocket
    Register
    Send a Notification
    Send another Notification
    Check 2nd notification matches
    Disconnect
    """
    URLS = get_var("config")
    encrypted_data = ["aLongStringOfEncryptedThings", "aDiffferentStringFullOfStuff"]
    topic_one = "aaaa"
    headers = {"TTL": "60", "Content-Encoding": "aes128gcm", "Topic": topic_one}
    channel_id = str(uuid.uuid4())
    async with session.ws_connect(
        f'{URLS["push_server"]}:443',
        headers={"Origin": "http://localhost:1337"},
        ssl=False,
    ) as ws:
        await ws.send_json(dict(messageType="hello", use_webpush=True))
        uaid = await ws.receive_json()
        await ws.send_json(dict(messageType="register", channelID=channel_id))
        msg1 = await ws.receive_json()
        await ws.close()
    # switch to rust endpoint
    if os.getenv("AUTOPUSH_RUST_SERVER"):
        path = urlparse(msg1["pushEndpoint"]).path
        endpoint_url = urljoin(URLS["rs_server_url"], path)
    else:
        endpoint_url = msg1["pushEndpoint"]
    # Send Notification
    async with session.post(
        endpoint_url,
        headers=headers,
        data=base64.urlsafe_b64decode(encrypted_data[0]),
        ssl=False,
    ) as conn:
        assert conn.status == 201 or 202
    # Send a second Notification with different data
    async with session.post(
        endpoint_url,
        headers=headers,
        data=base64.urlsafe_b64decode(encrypted_data[1]),
        ssl=False,
    ) as conn:
        assert conn.status == 201 or 202
    # Connect and check notifications
    async with session.ws_connect(
        f'{URLS["push_server"]}:443',
        headers={"Origin": "http://localhost:1337"},
        ssl=False,
    ) as ws:
        await ws.send_json(
            dict(messageType="hello", use_webpush=True, uaid=uaid["uaid"])
        )
        await ws.receive_json()
        # Wait for notification
        msg = await ws.receive_json()
        # Check data matches
        assert msg["data"] == encrypted_data[1]
        await ws.send_json(dict(messageType="ack", updates=dict(channelID=channel_id)))
        assert ws.exception() == None
        await ws.close()


@scenario(weight=20)
async def test_connect_and_hold(session):
    """Connects and waits for 60 seconds
    
    Connect
    Wait for 60 seconds
    Disconnect
    """
    URLS = get_var("config")
    headers = {"TTL": "60", "Content-Encoding": "aes128gcm"}
    channel_id = str(uuid.uuid4())
    async with session.ws_connect(
        f'{URLS["push_server"]}:443',
        headers={"Origin": "http://localhost:1337"},
        ssl=False,
    ) as ws:
        await ws.send_json(dict(messageType="hello", use_webpush=True))
        hello_msg = await ws.receive_json()
        assert hello_msg["messageType"] == "hello"
        await asyncio.sleep(60)
        await ws.close()
