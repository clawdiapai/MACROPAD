import asyncio
import json
import logging
import os
import sys
import time
import requests

try:
    from winsdk.windows.ui.notifications.management import UserNotificationListener, UserNotificationListenerAccessStatus
    from winsdk.windows.ui.notifications import NotificationKinds
    WINSDK_AVAILABLE = True
except ImportError:
    WINSDK_AVAILABLE = False

# ==============================================================================
# CONFIGURATION
# ==============================================================================
PI_HUB_URL = os.getenv("PI_HUB_URL", "http://192.168.1.62:5000/api/notify")
POLL_INTERVAL = 1.0  # seconds

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("NotificationBridge")

# Cache to prevent duplicate notification triggers
processed_ids = set()

def dispatch_notification_to_pi(sender: str, message: str, notif_type: str = "message", source: str = "whatsapp"):
    payload = {
        "type": notif_type,
        "source": source,
        "sender": sender,
        "message": message,
        "duration_ms": 4500
    }
    try:
        resp = requests.post(PI_HUB_URL, json=payload, timeout=2.0)
        logger.info(f"Dispatched alert to Pi Hub ({resp.status_code}): {sender} - {message}")
    except Exception as e:
        logger.warning(f"Could not forward notification to Pi Hub: {e}")

async def monitor_windows_notifications():
    global processed_ids
    if not WINSDK_AVAILABLE:
        logger.error("winsdk library not found. Install with: pip install winsdk")
        logger.info("Manual/Webhook notifications via HTTP POST to http://192.168.1.62:5000/api/notify are still active.")
        return

    listener = UserNotificationListener.current
    status = await listener.request_access_async()
    if status != UserNotificationListenerAccessStatus.ALLOWED:
        logger.error(f"Access to Windows UserNotificationListener denied: {status}")
        return

    logger.info("==================================================================")
    logger.info("  MacroPad Windows Notification Bridge (WhatsApp / Alerts) Live")
    logger.info("==================================================================")
    logger.info(f"Target Pi Hub: {PI_HUB_URL}")

    while True:
        try:
            notifs = await listener.get_notifications_async(NotificationKinds.TOAST)
            current_ids = set()

            for n in notifs:
                nid = n.id
                current_ids.add(nid)
                if nid in processed_ids:
                    continue
                
                processed_ids.add(nid)
                app_name = getattr(n.app_info.display_info, 'display_name', '').lower() if n.app_info else ''
                
                # Filter for WhatsApp, Phone Link, Discord or Communication apps
                is_whatsapp = "whatsapp" in app_name
                is_discord = "discord" in app_name
                is_phone = "phone" in app_name or "link" in app_name
                
                if is_whatsapp or is_discord or is_phone:
                    binding = n.notification.visual.get_binding("ToastGeneric")
                    if binding:
                        texts = [t.text for t in binding.get_text_elements()]
                        sender = texts[0] if len(texts) > 0 else "WhatsApp"
                        msg = texts[1] if len(texts) > 1 else ""
                        
                        notif_type = "call" if "call" in msg.lower() or "incoming" in msg.lower() else "message"
                        source = "whatsapp" if is_whatsapp else ("discord" if is_discord else "phone")
                        
                        logger.info(f"[{source.upper()}] {sender}: {msg} (Type: {notif_type})")
                        dispatch_notification_to_pi(sender, msg, notif_type=notif_type, source=source)

            # Prune cache
            processed_ids = {i for i in processed_ids if i in current_ids}
            
        except Exception as e:
            logger.debug(f"Notification poll error: {e}")
            
        await asyncio.sleep(POLL_INTERVAL)

def main():
    asyncio.run(monitor_windows_notifications())

if __name__ == "__main__":
    main()
