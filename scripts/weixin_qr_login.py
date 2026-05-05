from __future__ import annotations

import argparse
import asyncio
import json
import time
from pathlib import Path

import qrcode

from gateway.platforms.weixin import (
    EP_GET_BOT_QR,
    EP_GET_QR_STATUS,
    ILINK_BASE_URL,
    QR_TIMEOUT_MS,
    _api_get,
    _make_ssl_connector,
    save_weixin_account,
)
from hermes_cli.config import get_hermes_home, save_env_value

import aiohttp


def _state_path(explicit: str | None) -> Path:
    if explicit:
        return Path(explicit).expanduser().resolve()
    return Path("/mnt/f/AGENT/data/weixin-login-state.json")


def _png_path(explicit: str | None) -> Path:
    if explicit:
        return Path(explicit).expanduser().resolve()
    return Path("/mnt/f/AGENT/data/weixin-qr.png")


async def fetch_qr(state_file: Path, png_file: Path, bot_type: str = "3") -> None:
    state_file.parent.mkdir(parents=True, exist_ok=True)
    png_file.parent.mkdir(parents=True, exist_ok=True)

    async with aiohttp.ClientSession(trust_env=True, connector=_make_ssl_connector()) as session:
        qr_resp = await _api_get(
            session,
            base_url=ILINK_BASE_URL,
            endpoint=f"{EP_GET_BOT_QR}?bot_type={bot_type}",
            timeout_ms=QR_TIMEOUT_MS,
        )

    qrcode_value = str(qr_resp.get("qrcode") or "")
    qrcode_url = str(qr_resp.get("qrcode_img_content") or "")
    if not qrcode_value:
        raise RuntimeError("QR response did not include qrcode token.")

    qrcode.make(qrcode_url or qrcode_value).save(str(png_file))
    payload = {
        "created_at": int(time.time()),
        "bot_type": bot_type,
        "qrcode": qrcode_value,
        "qrcode_url": qrcode_url,
        "png_file": str(png_file),
    }
    state_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))


async def poll_qr(state_file: Path, timeout_seconds: int = 480) -> None:
    if not state_file.exists():
        raise FileNotFoundError(f"State file not found: {state_file}")

    state = json.loads(state_file.read_text(encoding="utf-8"))
    qrcode_value = str(state.get("qrcode") or "")
    if not qrcode_value:
        raise RuntimeError("State file missing qrcode token.")

    deadline = time.time() + timeout_seconds
    current_base_url = ILINK_BASE_URL
    refresh_count = 0

    async with aiohttp.ClientSession(trust_env=True, connector=_make_ssl_connector()) as session:
        while time.time() < deadline:
            status_resp = await _api_get(
                session,
                base_url=current_base_url,
                endpoint=f"{EP_GET_QR_STATUS}?qrcode={qrcode_value}",
                timeout_ms=QR_TIMEOUT_MS,
            )
            status = str(status_resp.get("status") or "wait")
            print(status, flush=True)

            if status == "wait":
                await asyncio.sleep(2)
                continue

            if status == "scaned":
                await asyncio.sleep(2)
                continue

            if status == "scaned_but_redirect":
                redirect_host = str(status_resp.get("redirect_host") or "")
                if redirect_host:
                    current_base_url = f"https://{redirect_host}"
                await asyncio.sleep(1)
                continue

            if status == "expired":
                refresh_count += 1
                raise RuntimeError(f"QR code expired before confirmation (refresh_count={refresh_count}).")

            if status == "confirmed":
                account_id = str(status_resp.get("ilink_bot_id") or "")
                token = str(status_resp.get("bot_token") or "")
                base_url = str(status_resp.get("baseurl") or ILINK_BASE_URL)
                user_id = str(status_resp.get("ilink_user_id") or "")
                if not account_id or not token:
                    raise RuntimeError("Confirmation response missing account_id or token.")

                hermes_home = str(get_hermes_home())
                save_weixin_account(
                    hermes_home,
                    account_id=account_id,
                    token=token,
                    base_url=base_url,
                    user_id=user_id,
                )
                save_env_value("WEIXIN_ACCOUNT_ID", account_id)
                save_env_value("WEIXIN_TOKEN", token)
                save_env_value("WEIXIN_BASE_URL", base_url)
                save_env_value("WEIXIN_CDN_BASE_URL", "https://novac2c.cdn.weixin.qq.com/c2c")
                save_env_value("WEIXIN_DM_POLICY", "open")

                result = {
                    "status": status,
                    "account_id": account_id,
                    "base_url": base_url,
                    "user_id": user_id,
                    "state_file": str(state_file),
                }
                state.update(result)
                state_file.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
                print(json.dumps(result, ensure_ascii=False, indent=2))
                return

            await asyncio.sleep(2)

    raise TimeoutError(f"Weixin QR login timed out after {timeout_seconds} seconds.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Non-interactive Weixin QR login helper for Hermes.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    fetch_parser = subparsers.add_parser("fetch", help="Fetch a Weixin QR code and save it locally.")
    fetch_parser.add_argument("--state-file", default=None)
    fetch_parser.add_argument("--png-file", default=None)
    fetch_parser.add_argument("--bot-type", default="3")

    poll_parser = subparsers.add_parser("poll", help="Poll a previously fetched Weixin QR until confirmed.")
    poll_parser.add_argument("--state-file", default=None)
    poll_parser.add_argument("--timeout-seconds", type=int, default=480)

    args = parser.parse_args()
    if args.command == "fetch":
        asyncio.run(fetch_qr(_state_path(args.state_file), _png_path(args.png_file), bot_type=args.bot_type))
        return
    if args.command == "poll":
        asyncio.run(poll_qr(_state_path(args.state_file), timeout_seconds=args.timeout_seconds))
        return


if __name__ == "__main__":
    main()
