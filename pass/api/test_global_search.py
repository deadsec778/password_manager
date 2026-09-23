import sys
import os
import unittest
from unittest.mock import patch, MagicMock

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from api.dashboard_app import app
from db.connection import get_connection

class GlobalSearchTestCase(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True

    @patch('api.dashboard_app.query_all')
    @patch('api.dashboard_app.get_cipher_for_session')
    @patch('api.dashboard_app.get_admin_cipher')
    def test_global_search_endpoint_admin(self, mock_get_admin_cipher, mock_get_cipher, mock_query_all):
        # Mock cipher
        mock_cipher = MagicMock()
        mock_cipher.decrypt.return_value = b"decrypted_pw"
        mock_get_admin_cipher.return_value = mock_cipher
        mock_get_cipher.return_value = mock_cipher

        # Mock query return: pid, owner_uid, owner_username, service, uname, enc_user, enc_admin, url, notes, updated_at, vault_name, vault_id
        mock_query_all.return_value = [
            (1, 1, 'admin', 'Google', 'admin@google', 'encU', 'encA', 'http://google.com', 'notes1', '2025', 'Vault1', 10),
            (2, 2, 'user', 'Netflix', 'user@netflix', 'encU', 'encA', 'http://netflix.com', 'notes2', '2025', 'Vault2', 20)
        ]

        with self.app.session_transaction() as sess:
            sess["sid"] = "test_sid"
            sess["user_id"] = 1
            sess["role"] = "admin"
            sess["username"] = "admin"

        response = self.app.get('/search?q=netflix')
        self.assertEqual(response.status_code, 200)
        
        html = response.data.decode('utf-8')
        
        # It should filter for 'netflix' and show Vault2
        self.assertIn("Netflix", html)
        self.assertIn("Vault2", html)
        
        # Google should be excluded because of 'q=netflix' filter if implemented correctly
        # Wait, the search endpoint might just return Google if filtering happens only on DB or in Python
        # Let's verify filtering works
        self.assertNotIn("Google", html)

    @patch('api.dashboard_app.query_all')
    @patch('api.dashboard_app.get_cipher_for_session')
    @patch('api.dashboard_app.get_admin_cipher')
    def test_global_search_endpoint_user(self, mock_get_admin_cipher, mock_get_cipher, mock_query_all):
        # Mock cipher
        mock_cipher = MagicMock()
        mock_cipher.decrypt.return_value = b"decrypted_pw"
        mock_get_admin_cipher.side_effect = FileNotFoundError()
        mock_get_cipher.return_value = mock_cipher

        # User only gets their data
        mock_query_all.return_value = [
            (3, 2, 'user', 'Spotify', 'user@spotify', 'encU', 'encA', '', '', '2025', 'Personal', 30)
        ]

        with self.app.session_transaction() as sess:
            sess["sid"] = "test_sid"
            sess["user_id"] = 2
            sess["role"] = "user"
            sess["username"] = "user"

        response = self.app.get('/search?q=spotify')
        self.assertEqual(response.status_code, 200)
        
        html = response.data.decode('utf-8')
        self.assertIn("Spotify", html)

    def test_global_search_no_query_empty_passwords(self):
        with self.app.session_transaction() as sess:
            sess["sid"] = "test_sid"
            sess["user_id"] = 1
            sess["role"] = "admin"
            sess["username"] = "admin"
            
        response = self.app.get('/search')
        self.assertEqual(response.status_code, 200)
        html = response.data.decode('utf-8')
        self.assertIn("Please enter a search query.", html)


    @patch('api.dashboard_app.query_all')
    @patch('api.dashboard_app.get_cipher_for_session')
    @patch('api.dashboard_app.get_admin_cipher')
    @patch('api.dashboard_app.get_connection')
    def test_global_search_migration_fallback(self, mock_get_conn, mock_get_admin_cipher, mock_get_cipher, mock_query_all):
        mock_user_cipher = MagicMock()
        mock_user_cipher.decrypt.side_effect = Exception("User cipher failed")
        mock_user_cipher.encrypt.return_value = b"reencrypted_by_user"

        mock_admin_cipher = MagicMock()
        mock_admin_cipher.decrypt.return_value = b"recovered_pw"
        
        mock_get_admin_cipher.return_value = mock_admin_cipher
        mock_get_cipher.return_value = mock_user_cipher

        # User route with migration fallback condition
        mock_query_all.return_value = [
            (5, 2, 'user', 'Slack', 'user@slack', 'badU', 'encA', '', '', '2025', 'Vault3', 40)
        ]

        # Mock DB connection for re-encryption update
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_conn.cursor.return_value = mock_cur
        mock_get_conn.return_value = mock_conn

        with self.app.session_transaction() as sess:
            sess["sid"] = "test_sid"
            sess["user_id"] = 2
            sess["role"] = "user"
            sess["username"] = "user"

        response = self.app.get('/search?q=slack')
        self.assertEqual(response.status_code, 200)
        
        html = response.data.decode('utf-8')
        self.assertIn("recovered_pw", html)
        self.assertIn("Slack", html)
        
        # Verify db update was called
        mock_cur.execute.assert_called_once()
        args = mock_cur.execute.call_args[0]
        self.assertIn("UPDATE passwords SET password_user_enc", args[0])

    @patch('api.dashboard_app.query_all')
    @patch('api.dashboard_app.get_cipher_for_session')
    @patch('api.dashboard_app.get_admin_cipher')
    def test_global_search_ajax_returns_vault_id(self, mock_get_admin_cipher, mock_get_cipher, mock_query_all):
        mock_cipher = MagicMock()
        mock_cipher.decrypt.return_value = b"decrypted_pw"
        mock_get_admin_cipher.return_value = mock_cipher
        mock_get_cipher.return_value = mock_cipher

        # To avoid breaking until GREEN phase, we'll just return what dashboard_app currently expects or what we will make it expect.
        # Currently it unpacks: pid, owner_uid, owner_username, service, uname, enc_user, enc_admin, url, notes, updated_at, vault_name = r
        # We will change it to return 12 items. So during RED phase this test might crash unpacking, or it might just fail the assert.
        # Let's provide 12 items. For the old code, it will crash because it expects 11 items. 
        # Actually in TDD, if we get a crash (Exception), it's still a failing test (RED)!
        mock_query_all.return_value = [
            (1, 1, 'admin', 'Github', 'admin@github', 'encU', 'encA', 'http://github.com', 'notes', '2025', 'Vault1', 99)
        ]

        with self.app.session_transaction() as sess:
            sess["sid"] = "test_sid"
            sess["user_id"] = 1
            sess["role"] = "admin"
            sess["username"] = "admin"

        response = self.app.get('/search?q=github', headers={"X-Requested-With": "XMLHttpRequest"})
        self.assertEqual(response.status_code, 200)
        
        data = response.get_json()
        self.assertTrue("passwords" in data)
        self.assertEqual(len(data["passwords"]), 1)
        self.assertIn("vault_id", data["passwords"][0])
        self.assertEqual(data["passwords"][0]["vault_id"], 99)

    @patch('api.dashboard_app.query_all')
    @patch('api.dashboard_app.get_cipher_for_session')
    @patch('api.dashboard_app.get_admin_cipher')
    def test_global_search_locked(self, mock_get_admin_cipher, mock_get_cipher, mock_query_all):
        mock_user_cipher = MagicMock()
        mock_user_cipher.decrypt.side_effect = Exception("Failed")
        
        mock_get_admin_cipher.side_effect = Exception("No admin")
        mock_get_cipher.return_value = mock_user_cipher

        mock_query_all.return_value = [
            (6, 2, 'user', 'Discord', 'user@discord', 'badU', 'badA', '', '', '2025', 'Vault4', 50)
        ]

        with self.app.session_transaction() as sess:
            sess["sid"] = "test_sid"
            sess["user_id"] = 2
            sess["role"] = "user"
            sess["username"] = "user"

        response = self.app.get('/search?q=discord')
        self.assertEqual(response.status_code, 200)
        
        html = response.data.decode('utf-8')
        self.assertIn("🔒", html)

if __name__ == '__main__':
    unittest.main()
