import requests
import logging


class TelegramNotifier:
    def __init__(self, token=None, chat_id=None, enabled=True):
        """
        :param token: Telegram Bot Token (defaults to None, should be provided from config)
        :param chat_id: Can be a single ID (str/int), a list of IDs, or a comma-separated string
        """
        self.token = token
        self.chat_ids = self._parse_chat_ids(chat_id)
        self.enabled = enabled

    def _parse_chat_ids(self, chat_id):
        if not chat_id:
            return []
        if isinstance(chat_id, list):
            return [str(i).strip() for i in chat_id if i]
        if isinstance(chat_id, str):
            return [i.strip() for i in chat_id.split(",") if i.strip()]
        return [str(chat_id)]

    def update_config(self, token, chat_id, enabled=True):
        self.token = token
        self.chat_ids = self._parse_chat_ids(chat_id)
        self.enabled = enabled

    def send_message(self, text):
        if not self.enabled:
            return False
        if not self.token or not self.chat_ids:
            logging.warning(
                "Telegram Notifier: Token or Chat IDs not configured.")
            return False

        success_count = 0
        for cid in self.chat_ids:
            api_url = f"https://api.telegram.org/bot{self.token}/sendMessage"
            payload = {
                "chat_id": cid,
                "text": text,
                "parse_mode": "Markdown"
            }

            max_retries = 3
            retry_count = 0
            sent = False

            while retry_count < max_retries and not sent:
                try:
                    logging.info(
                        f"Attempting to send Telegram message to {cid} (Attempt {retry_count + 1}/{max_retries})")
                    response = requests.post(api_url, json=payload, timeout=10)
                    if response.status_code == 200:
                        logging.info(
                            f"✅ Telegram message sent to {cid} successfully.")
                        success_count += 1
                        sent = True
                    else:
                        logging.error(
                            f"❌ Telegram API Error for {cid} (Status {response.status_code}): {response.text}")
                        retry_count += 1
                        if retry_count < max_retries:
                            import time
                            time.sleep(2)  # Wait before retry
                except Exception as e:
                    logging.error(
                        f"⚠️ Telegram connection error for {cid}: {e}")
                    retry_count += 1
                    if retry_count < max_retries:
                        import time
                        time.sleep(2)

        return success_count > 0
