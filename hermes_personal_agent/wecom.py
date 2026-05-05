from __future__ import annotations

from base64 import b64decode, b64encode
from dataclasses import dataclass
from hashlib import sha1
from typing import Any
from xml.etree import ElementTree as ET
import os

from Crypto.Cipher import AES

from hermes_personal_agent.config import WeComCallbackConfig
from hermes_personal_agent.messaging import MessagingGateway


class WeComCallbackError(ValueError):
    pass


def _pkcs7_pad(data: bytes, block_size: int = 32) -> bytes:
    pad_len = block_size - (len(data) % block_size)
    if pad_len == 0:
        pad_len = block_size
    return data + bytes([pad_len]) * pad_len


def _pkcs7_unpad(data: bytes, block_size: int = 32) -> bytes:
    if not data:
        raise WeComCallbackError("Invalid PKCS7 payload.")
    pad_len = data[-1]
    if pad_len < 1 or pad_len > block_size:
        raise WeComCallbackError("Invalid PKCS7 padding.")
    if data[-pad_len:] != bytes([pad_len]) * pad_len:
        raise WeComCallbackError("Invalid PKCS7 padding bytes.")
    return data[:-pad_len]


def parse_xml_fields(xml_text: str) -> dict[str, str]:
    root = ET.fromstring(xml_text)
    return {child.tag: (child.text or "") for child in root}


@dataclass
class WeComInboundMessage:
    message_id: str
    text: str
    sender: str
    metadata: dict[str, Any]

    def to_payload(self) -> dict[str, Any]:
        return {
            "message_id": self.message_id,
            "text": self.text,
            "sender": self.sender,
            "metadata": self.metadata,
        }


class WeComCrypto:
    def __init__(self, config: WeComCallbackConfig) -> None:
        if len(config.encoding_aes_key) != 43:
            raise WeComCallbackError("WECOM_ENCODING_AES_KEY must be 43 characters.")
        self.config = config
        self.aes_key = b64decode(f"{config.encoding_aes_key}=")
        if len(self.aes_key) != 32:
            raise WeComCallbackError("Decoded WECOM_ENCODING_AES_KEY must be 32 bytes.")
        self.iv = self.aes_key[:16]

    def verify_url(self, msg_signature: str, timestamp: str, nonce: str, echostr: str) -> str:
        self._verify_signature(msg_signature, timestamp, nonce, echostr)
        return self._decrypt(echostr)

    def decrypt_message(self, msg_signature: str, timestamp: str, nonce: str, xml_body: str) -> str:
        fields = parse_xml_fields(xml_body)
        encrypted = fields.get("Encrypt", "")
        if not encrypted:
            raise WeComCallbackError("Missing Encrypt field in callback XML.")
        self._verify_signature(msg_signature, timestamp, nonce, encrypted)
        return self._decrypt(encrypted)

    def encrypt_message(self, plaintext_xml: str, timestamp: str, nonce: str) -> str:
        encrypted = self._encrypt(plaintext_xml)
        signature = self._signature(timestamp, nonce, encrypted)
        root = ET.Element("xml")
        ET.SubElement(root, "Encrypt").text = encrypted
        ET.SubElement(root, "MsgSignature").text = signature
        ET.SubElement(root, "TimeStamp").text = timestamp
        ET.SubElement(root, "Nonce").text = nonce
        return ET.tostring(root, encoding="unicode")

    def _signature(self, timestamp: str, nonce: str, encrypted: str) -> str:
        payload = "".join(sorted([self.config.token, timestamp, nonce, encrypted]))
        return sha1(payload.encode("utf-8")).hexdigest()

    def _verify_signature(self, msg_signature: str, timestamp: str, nonce: str, encrypted: str) -> None:
        if self._signature(timestamp, nonce, encrypted) != msg_signature:
            raise WeComCallbackError("Invalid WeCom callback signature.")

    def _encrypt(self, plaintext_xml: str) -> str:
        random_prefix = os.urandom(16)
        plaintext = plaintext_xml.encode("utf-8")
        msg_len = len(plaintext).to_bytes(4, byteorder="big")
        full = random_prefix + msg_len + plaintext + self.config.corp_id.encode("utf-8")
        cipher = AES.new(self.aes_key, AES.MODE_CBC, self.iv)
        encrypted = cipher.encrypt(_pkcs7_pad(full))
        return b64encode(encrypted).decode("utf-8")

    def _decrypt(self, encrypted: str) -> str:
        cipher = AES.new(self.aes_key, AES.MODE_CBC, self.iv)
        decrypted = cipher.decrypt(b64decode(encrypted))
        unpadded = _pkcs7_unpad(decrypted)
        if len(unpadded) < 20:
            raise WeComCallbackError("Invalid WeCom payload length.")
        msg_len = int.from_bytes(unpadded[16:20], byteorder="big")
        message = unpadded[20 : 20 + msg_len]
        receive_id = unpadded[20 + msg_len :].decode("utf-8")
        if receive_id != self.config.corp_id:
            raise WeComCallbackError("WeCom receive_id does not match configured corp_id.")
        return message.decode("utf-8")


class WeComCallbackService:
    def __init__(self, config: WeComCallbackConfig, messaging: MessagingGateway) -> None:
        self.config = config
        self.messaging = messaging
        self.crypto = WeComCrypto(config) if config.is_configured else None

    @property
    def is_configured(self) -> bool:
        return self.crypto is not None

    def verify_url(self, query: dict[str, str]) -> str:
        crypto = self._require_crypto()
        return crypto.verify_url(
            msg_signature=query["msg_signature"],
            timestamp=query["timestamp"],
            nonce=query["nonce"],
            echostr=query["echostr"],
        )

    def handle_callback(self, query: dict[str, str], xml_body: str) -> dict[str, Any]:
        crypto = self._require_crypto()
        plaintext = crypto.decrypt_message(
            msg_signature=query["msg_signature"],
            timestamp=query["timestamp"],
            nonce=query["nonce"],
            xml_body=xml_body,
        )
        inbound = self._build_inbound_message(plaintext)
        if inbound is None:
            return {"handled": True, "ignored": True}
        result = self.messaging.ingest("wecom", inbound.to_payload())
        return {
            "handled": True,
            "ignored": False,
            "job_id": result.get("job_id"),
            "reply": result.get("reply", ""),
        }

    def _require_crypto(self) -> WeComCrypto:
        if self.crypto is None:
            raise WeComCallbackError(
                "WeCom callback is not configured. Set WECOM_TOKEN, WECOM_ENCODING_AES_KEY, and WECOM_CORP_ID."
            )
        return self.crypto

    def _build_inbound_message(self, plaintext: str) -> WeComInboundMessage | None:
        fields = parse_xml_fields(plaintext)
        msg_type = fields.get("MsgType", "").strip().lower()
        sender = fields.get("FromUserName", "unknown").strip() or "unknown"
        create_time = fields.get("CreateTime", "").strip()
        event = fields.get("Event", "").strip().lower()
        event_key = fields.get("EventKey", "").strip()
        agent_id = fields.get("AgentID", "").strip()

        metadata: dict[str, Any] = {
            "channel": "wecom_callback",
            "sender": sender,
            "wecom_msg_type": msg_type,
            "wecom_event": event,
            "wecom_event_key": event_key,
            "wecom_agent_id": agent_id,
            "wecom_corp_id": self.config.corp_id,
            "wecom_fields": fields,
        }

        text = ""
        if msg_type == "text":
            text = fields.get("Content", "").strip()
        elif msg_type == "voice" and fields.get("Recognition", "").strip():
            text = fields.get("Recognition", "").strip()
            metadata["transcript_source"] = "voice_recognition"
        elif msg_type == "event":
            if event == "click" and event_key:
                text = event_key
            elif event == "view" and event_key:
                text = f"link: {event_key}"
            elif event in {"scancode_push", "scancode_waitmsg"}:
                text = event_key or f"event: {event}"
            else:
                return None
        else:
            return None

        if not text:
            return None

        message_id = fields.get("MsgId", "").strip()
        if not message_id:
            message_id = ":".join(part for part in [sender, create_time, msg_type or event, event_key] if part)

        return WeComInboundMessage(
            message_id=message_id,
            text=text,
            sender=sender,
            metadata=metadata,
        )
