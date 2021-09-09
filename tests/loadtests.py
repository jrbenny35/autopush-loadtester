import base64
import os
import random
import string
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
            assert conn.status == 201, f'connection returned code {conn.status}'
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
        assert conn.status == 201 or 202, f'connection returned code {conn.status}'
    # Send a second Notification with different data
    async with session.post(
        endpoint_url,
        headers=headers,
        data=base64.urlsafe_b64decode(encrypted_data[1]),
        ssl=False,
    ) as conn:
        assert conn.status == 201 or 202, f'connection returned code {conn.status}'
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


@scenario(weight=80)
async def test_connect_direct_store(session):
    """Basic test
    
    Connect to websocket
    Register
    Send a Notification
    Disconnect
    Check notification matches
    Disconnect
    """
    URLS = get_var("config")
    encrypted_data = "aLongStringOfEncryptedThings"
    headers = {"TTL": "60", "Content-Encoding": "aes128gcm"}
    channel_id = str(uuid.uuid4())
    uaid = None
    async with session.ws_connect(
        f'{URLS["push_server"]}:443',
        headers={"Origin": "http://localhost:1337"},
        ssl=False,
    ) as ws:
        await ws.send_json(dict(messageType="hello", use_webpush=True))
        hello_msg = await ws.receive_json()
        assert hello_msg["messageType"] == "hello"
        uaid = hello_msg["uaid"]
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
            assert conn.status == 201, f'connection returned code {conn.status}'
        # Receive notification
        msg2 = await ws.receive_json()
        assert msg2["data"] == encrypted_data
        await ws.close()
    # wait and connect again
    await asyncio.sleep(10)
    # Connect again
    async with session.ws_connect(
        f'{URLS["push_server"]}:443',
        headers={"Origin": "http://localhost:1337"},
        ssl=False,
    ) as ws:
        await ws.send_json(dict(messageType="hello", use_webpush=True, uaid=uaid))
        hello_msg_2 = await ws.receive_json()
        assert hello_msg_2["messageType"] == "hello"
        assert uaid == hello_msg_2["uaid"]
        
        notification = await ws.receive_json()
        assert notification is not None
        assert notification["channelID"] == channel_id
        
        await ws.send_json(dict(messageType="ack", updates=dict(channelID=channel_id)))
        assert ws.exception() == None
        
        await ws.send_json(dict(messageType="unregister", channelID=channel_id))
        assert ws.exception() == None
        await ws.close()


@scenario(weight=80)
async def test_connect_stored(session):
    """Basic test
    
    Connect to websocket
    Register
    Send 10 Notifications
    Check number of notifications sent is equal to what is received
    Disconnect
    """
    URLS = get_var("config")
    encrypted_data = "aLongStringOfEncryptedThings"
    headers = {"TTL": "60", "Content-Encoding": "aes128gcm"}
    channel_id = str(uuid.uuid4())
    uaid = None
    message_ids = []
    quantity = 10
    async with session.ws_connect(
        f'{URLS["push_server"]}:443',
        headers={"Origin": "http://localhost:1337"},
        ssl=False,
    ) as ws:
        await ws.send_json(dict(messageType="hello", use_webpush=True))
        hello_msg = await ws.receive_json()
        assert hello_msg["messageType"] == "hello"
        uaid = hello_msg["uaid"]
        await ws.send_json(dict(messageType="register", channelID=channel_id))
        msg1 = await ws.receive_json()
        # switch to rust endpoint
        if os.getenv("AUTOPUSH_RUST_SERVER") and (os.getenv("AUTOPUSH_ENV") != "dev"):
            path = urlparse(msg1["pushEndpoint"]).path
            endpoint_url = urljoin(URLS["rs_server_url"], path)
        else:
            endpoint_url = msg1["pushEndpoint"]
        await ws.close()
        # Send a notification
    for _ in range(quantity):
        async with session.post(
            endpoint_url,
            headers=headers,
            data=base64.urlsafe_b64decode(encrypted_data),
            ssl=False,
        ) as conn:
            assert conn.status == 201, f'connection returned code {conn.status}'
        await asyncio.sleep(1)
    await asyncio.sleep(1)
    async with session.ws_connect(
        f'{URLS["push_server"]}:443',
        headers={"Origin": "http://localhost:1337"},
        ssl=False,
    ) as ws:
        await ws.send_json(dict(messageType="hello", use_webpush=True, uaid=uaid))
        hello_msg = await ws.receive_json()
        assert hello_msg["messageType"] == "hello"
        # Receive notification
        while True:
            await asyncio.sleep(2)
            try:
                notification = await ws.receive_json()
            except TypeError:
                break
            else:
                if notification["channelID"] == channel_id:
                    message_ids.append(notification["version"])
                    await ws.send_json(dict(
                        messageType="ack",
                        updates=dict(
                            channelID=channel_id,
                            version=notification["version"])
                        )
                    )
                else:
                    break
    assert len(message_ids) == quantity


@scenario(weight=10)
async def test_basic_connect_forever(session):
    """Connect and send a notification. Disconnect and reconnect.
    Check notification. Repeat.
    
    Connect to websocket
    Register
    Send a Notification
    Check notification matches
    Disconnect
    Reconnect
    Wait for correct notification
    """
    URLS = get_var("config")
    headers = {"TTL": "60", "Content-Encoding": "aes128gcm"}
    channel_id = str(uuid.uuid4())
    uaid = None
    ws = await session.ws_connect(
        f'{URLS["push_server"]}:443',
        headers={"Origin": "http://localhost:1337"},
        ssl=False,
    )
    await ws.send_json(dict(messageType="hello", use_webpush=True))
    hello_msg = await ws.receive_json()
    assert hello_msg["messageType"] == "hello"
    uaid = hello_msg["uaid"]
    await ws.send_json(dict(messageType="register", channelID=channel_id))
    msg1 = await ws.receive_json()
    # switch to rust endpoint
    if os.getenv("AUTOPUSH_RUST_SERVER") and (os.getenv("AUTOPUSH_ENV") != "dev"):
        path = urlparse(msg1["pushEndpoint"]).path
        endpoint_url = urljoin(URLS["rs_server_url"], path)
    else:
        endpoint_url = msg1["pushEndpoint"]
    # Send a notification
    for _ in range(16):
        random_data = random.randrange(2048, 4096)
        async with session.post(
            endpoint_url,
            headers=headers,
            data=base64.urlsafe_b64decode(str(random_data)),
            ssl=False,
        ) as conn:
            if conn.status == 201:
                try:
                    msg2 = await ws.receive_json()
                except TypeError:
                    # Sometimes the message isn't a string
                    pass
                else:
                    if msg2["messageType"] == "notification":
                        # Acknowledge notification
                        await ws.send_json(
                            dict(messageType="ack",
                                updates=dict(channelID=msg2["channelID"])
                                )
                            )
            elif conn.status != 410:
                raise AssertionError(f'connection returned code {conn.status}')
        await ws.close()
        await asyncio.sleep(5)
        # Connect again to websocket
        ws = await session.ws_connect(
            f'{URLS["push_server"]}:443',
            headers={"Origin": "http://localhost:1337"},
            ssl=False,
        )
        await ws.send_json(dict(messageType="hello", use_webpush=True, uaid=uaid))
        hello_msg = await ws.receive_json()
        assert hello_msg["messageType"] == "hello"
        await asyncio.sleep(2)
        msg = await ws.receive_json()
        assert msg["channelID"] == channel_id
        await ws.send_json(
            dict(messageType="ack",
                updates=dict(channelID=channel_id)
                )
            )
        await asyncio.sleep(5)
    else:
        await ws.close()
        assert True

@scenario(weight=20)
async def test_notification_bad_token_and_endpoint(session):
    """Connects and sends a notification with a bad token.
    Repeasts for 16 times.
    
    """
    URLS = get_var("config")
    headers = {"TTL": "60", "Content-Encoding": "aes128gcm"}
    channel_id = str(uuid.uuid4())
    random_endpoint = ''.join(random.choice(string.ascii_lowercase + string.digits)
                   for _ in range(random.randint(1, 1000)))
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
    for _ in range(16):
        # switch to rust endpoint
        if os.getenv("AUTOPUSH_RUST_SERVER") and (os.getenv("AUTOPUSH_ENV") != "dev"):
            path = urlparse(msg1["pushEndpoint"]).path
            endpoint_url = urljoin(URLS["rs_server_url"], path)
        else:
            endpoint_url = msg1["pushEndpoint"]
        parts = endpoint_url.split('/')
        parts.pop()
        create_random_url = "/".join(parts) + '/' + random_endpoint
        # Send a notification
        random_data = os.urandom(random.randrange(2048, 4096, 2))
        async with session.post(
            create_random_url,
            headers=headers,
            data=base64.urlsafe_b64encode(random_data),
            ssl=False,
        ) as conn:
            assert conn.status == 404, f'Connection status code was {conn.status}'
        await asyncio.sleep(5)
    else:
        assert True