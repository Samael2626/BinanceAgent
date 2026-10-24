import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi import HTTPException
from backend import main


def test_paper_registration_needs_no_binance_keys():
    class FakeDb:
        def __init__(self):
            self.settings = {}
            self.created = None

        def get_user_by_username(self, username):
            return None

        def create_user(self, username, api_key, api_secret, is_testnet):
            self.created = (username, api_key, api_secret, is_testnet)
            return 7

        def save_setting(self, key, value, user_id):
            self.settings[key] = value

        def set_user_session(self, user_id, token):
            assert user_id == 7 and token

    class FakeManager:
        def get_or_create_bot(self, user_id, api_key, api_secret, is_testnet):
            assert (user_id, api_key, api_secret, is_testnet) == (7, "", "", True)
            return object()

    original_db, original_manager = main.db, main.bot_manager
    try:
        db = FakeDb()
        main.db, main.bot_manager = db, FakeManager()
        response = main.register({"username": "paper_user", "execution_mode": "PAPER",
                                  "paper_initial_usdt": "47"})
        assert response["status"] == "success"
        assert response["user"]["execution_mode"] == "PAPER"
        assert db.created == ("paper_user", "", "", True)
        assert db.settings == {"execution_mode": "PAPER", "paper_initial_usdt": "47"}
    finally:
        main.db, main.bot_manager = original_db, original_manager


def test_invalid_virtual_capital_is_rejected():
    for value in ("0", "NaN", "1000001", "invalid"):
        try:
            main.register({"username": "bad", "execution_mode": "PAPER",
                           "paper_initial_usdt": value})
        except HTTPException as exc:
            assert exc.status_code == 400
        else:
            raise AssertionError(f"accepted invalid capital: {value}")


if __name__ == "__main__":
    test_paper_registration_needs_no_binance_keys()
    test_invalid_virtual_capital_is_rejected()
    print("paper registration tests ok")
