import unittest

from src.auth import hash_password, has_permission, verify_password, verify_user_login


class TestAuthentication(unittest.TestCase):
    def test_password_hash_verifies_only_matching_password(self):
        encoded_hash = hash_password("correct horse battery staple")

        self.assertTrue(verify_password("correct horse battery staple", encoded_hash))
        self.assertFalse(verify_password("incorrect password", encoded_hash))

    def test_password_hash_rejects_malformed_hash(self):
        with self.assertRaises(ValueError):
            verify_password("password", "not-a-valid-hash")

    def test_roles_grant_only_expected_permissions(self):
        self.assertTrue(has_permission("hr", "read"))
        self.assertTrue(has_permission("hr", "write"))
        self.assertTrue(has_permission("manager", "read"))
        self.assertFalse(has_permission("manager", "write"))
        self.assertTrue(has_permission("employee", "read"))
        self.assertFalse(has_permission("employee", "write"))
        self.assertFalse(has_permission("unknown", "read"))

    def test_selected_role_must_match_configured_account(self):
        account = {
            "role": "hr",
            "password_hash": hash_password("private password"),
        }

        self.assertFalse(verify_user_login(account, "private password", "manager"))
        self.assertTrue(verify_user_login(account, "private password", "hr"))


if __name__ == "__main__":
    unittest.main()
