"""Offline persistence contract checks; never import the application or connect.

Run directly with unittest so the API-oriented pytest conftest is not loaded.
These checks do not replace the required disposable PostgreSQL migration proofs.
"""

import unittest
import re

from sqlalchemy import CHAR, CheckConstraint, UniqueConstraint
from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateTable

from app.models import AuthSession, Base, Notification, SupportRequest, WelfareCaseAction


class Stage2OrmContractTests(unittest.TestCase):
    def test_approved_current_and_legacy_case_status_vocabulary(self):
        table = WelfareCaseAction.__table__
        self.assertTrue(table.c.case_status.nullable)
        self.assertEqual(table.c.case_status.type.length, 40)
        check = next(c for c in table.constraints if c.name == "welfare_case_actions_case_status_check")
        self.assertEqual(set(re.findall("'([^']*)'", str(check.sqltext))), {
            "OPEN", "ASSIGNED", "IN_PROGRESS", "CLOSED", "WITHDRAWN", "PENDING", "RESOLVED",
        })

    def test_notification_reference_and_read_state(self):
        table = Notification.__table__
        self.assertEqual(set(table.c.keys()), {
            "id", "recipient_user_id", "notification_type", "message",
            "resource_type", "resource_id", "created_at", "read_at", "dedupe_key",
        })
        self.assertFalse(table.c.resource_id.foreign_keys)
        self.assertTrue(table.c.read_at.nullable)
        self.assertIsNone(table.c.read_at.default)
        self.assertEqual(next(iter(table.c.recipient_user_id.foreign_keys)).ondelete, "RESTRICT")
        self.assertFalse(any(isinstance(c, CheckConstraint) for c in table.constraints))
        uniques = [tuple(c.columns.keys()) for c in table.constraints if isinstance(c, UniqueConstraint)]
        self.assertEqual(uniques, [("recipient_user_id", "dedupe_key")])

    def test_nullable_hashes_have_no_automatic_generation(self):
        for column in (SupportRequest.__table__.c.request_key_hash,
                       SupportRequest.__table__.c.request_hash,
                       AuthSession.__table__.c.refresh_secret_hash):
            self.assertIsInstance(column.type, CHAR)
            self.assertEqual(column.type.length, 64)
            self.assertTrue(column.nullable)
            self.assertIsNone(column.default)
            self.assertIsNone(column.server_default)
        index = next(i for i in SupportRequest.__table__.indexes
                     if i.name == "uq_support_requests_personnel_request_key")
        self.assertTrue(index.unique)
        self.assertEqual(tuple(index.columns.keys()), ("personnel_id", "request_key_hash"))
        self.assertEqual(str(index.dialect_options["postgresql"]["where"]), "request_key_hash IS NOT NULL")

    def test_welfare_independent_constraints(self):
        table = WelfareCaseAction.__table__
        for name in ("case_id", "actor_user_id", "assigned_to_user_id"):
            self.assertEqual(next(iter(table.c[name].foreign_keys)).ondelete, "RESTRICT")
        checks = {c.name: str(c.sqltext) for c in table.constraints if isinstance(c, CheckConstraint)}
        self.assertEqual(checks["welfare_case_actions_visibility_check"], "visibility IN ('PERSONNEL','OFFICER')")
        self.assertEqual(checks["welfare_case_actions_note_length_check"], "char_length(note) <= 2000")
        self.assertNotIn("payload_json", table.c)
        self.assertNotIn("updated_at", table.c)

    def test_single_metadata_and_postgresql_defaults(self):
        for model in (Notification, WelfareCaseAction, SupportRequest, AuthSession):
            self.assertIs(model.__table__.metadata, Base.metadata)
            str(CreateTable(model.__table__).compile(dialect=postgresql.dialect()))
        for model in (Notification, WelfareCaseAction):
            self.assertEqual(str(model.__table__.c.id.server_default.arg), "gen_random_uuid()")
            self.assertEqual(str(model.__table__.c.created_at.server_default.arg), "CURRENT_TIMESTAMP")
            self.assertTrue(model.__table__.c.created_at.type.timezone)


if __name__ == "__main__":
    unittest.main()
