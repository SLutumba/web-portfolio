"""Integration checks for the portfolio's new instant-access boundary."""
import os
from pathlib import Path
import unittest
from datetime import datetime, timedelta, timezone

os.environ["PORTFOLIO_DB_URL"] = "sqlite://"
os.environ["JWT_SECRET_KEY"] = "portfolio-test-key-not-used-outside-tests-12345"

import server
from flask_jwt_extended import create_access_token


class DemoIntegrationTests(unittest.TestCase):
    def setUp(self):
        server.Base.metadata.drop_all(server.engine)
        server.Base.metadata.create_all(server.engine)
        server.rate_buckets.clear()
        self.client = server.app.test_client()

    def session(self):
        response = self.client.post('/api/demo/session', json={})
        self.assertEqual(response.status_code, 201, response.json)
        return {'Authorization': f"Bearer {response.json['access_token']}"}

    def test_home_and_assets(self):
        page = self.client.get('/')
        self.assertEqual(page.status_code, 200)
        self.assertIn('Thoughtful code.', page.text)
        self.assertIn("frame-ancestors 'none'", page.headers['Content-Security-Policy'])
        page.close()
        for asset in ['styles.css', 'app.js', 'theme.js', 'assets/portrait.jpg', 'assets/favicon.svg', 'assets/Shekinah-Lutumba-CV.pdf']:
            with self.subTest(asset=asset):
                response = self.client.get('/static/' + asset)
                self.assertEqual(response.status_code, 200)
                response.close()

    def test_new_workspace_seeds_and_persists(self):
        headers = self.session()
        response = self.client.get('/api/tasks/', headers=headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json), 3)
        self.assertEqual(response.headers['Cache-Control'], 'no-store')
        self.assertEqual(self.client.get('/api/tasks/', headers=headers).json, response.json)

    def test_full_crud_round_trip(self):
        headers = self.session()
        response = self.client.post('/api/tasks/create', headers=headers, json={'title':'A test task','description':'Original context','status':'To-Do','priority':'Medium'})
        self.assertEqual(response.status_code, 201, response.json)
        path = f"/api/tasks/{response.json['id']}"
        edited = self.client.patch(path, headers=headers, json={'status':'Complete','description':None})
        self.assertEqual(edited.status_code, 200)
        self.assertEqual(edited.json['title'], 'A test task')
        self.assertIsNone(edited.json['description'])
        self.assertEqual(self.client.get(path, headers=headers).json['status'], 'Complete')
        deleted = self.client.delete(path, headers=headers, json={})
        self.assertEqual(deleted.status_code, 204)
        self.assertEqual(self.client.get(path, headers=headers).status_code, 404)

    def test_visitor_cannot_read_edit_or_delete_another_visitors_task(self):
        owner = self.session()
        other = self.session()
        own_task = self.client.get('/api/tasks/', headers=owner).json[0]
        path = f"/api/tasks/{own_task['id']}"
        self.assertEqual(self.client.get(path, headers=other).status_code, 404)
        self.assertEqual(self.client.patch(path, headers=other, json={'title':'Hijacked task'}).status_code, 404)
        self.assertEqual(self.client.delete(path, headers=other, json={}).status_code, 404)
        self.assertEqual(self.client.get(path, headers=owner).json, own_task)
        self.assertTrue(set(x['id'] for x in self.client.get('/api/tasks/', headers=owner).json).isdisjoint(x['id'] for x in self.client.get('/api/tasks/', headers=other).json))

    def test_invalid_update_does_not_modify_task(self):
        headers = self.session()
        task = self.client.get('/api/tasks/', headers=headers).json[0]
        path = f"/api/tasks/{task['id']}"
        for payload in [{'title':'  '},{'status':'Made up'},{'priority':None},{'title':'x' * 65}]:
            self.assertEqual(self.client.patch(path, headers=headers, json=payload).status_code, 400)
        self.assertEqual(self.client.get(path, headers=headers).json, task)

    def test_no_token_and_wrong_token_are_rejected(self):
        self.assertEqual(self.client.get('/api/tasks/').status_code, 401)
        with server.app.app_context():
            non_demo = create_access_token(identity='1')
            bad_identity = create_access_token(identity='not-a-number', additional_claims={'portfolio_demo':True})
        for token in [non_demo, bad_identity]:
            self.assertEqual(self.client.get('/api/tasks/', headers={'Authorization':f'Bearer {token}'}).status_code, 401)

    def test_expiry_denies_access_and_cleanup_removes_only_expired_data(self):
        expired = self.session()
        active = self.session()
        old_id = self.client.get('/api/tasks/', headers=expired).json[0]['id']
        with server.SessionLocal() as db:
            user_id = db.get(server.Task, old_id).user_id
            db.get(server.DemoSession, user_id).expires_at = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(minutes=1)
            db.commit()
        self.assertEqual(self.client.get('/api/tasks/', headers=expired).status_code, 401)
        server.cleanup_expired()
        with server.SessionLocal() as db:
            self.assertIsNone(db.get(server.User, user_id))
            self.assertIsNone(db.get(server.Task, old_id))
        self.assertEqual(len(self.client.get('/api/tasks/', headers=active).json), 3)

    def test_session_rate_limit_and_task_limit(self):
        for _ in range(12):
            self.session()
        self.assertEqual(self.client.post('/api/demo/session', json={}).status_code, 429)
        server.rate_buckets.clear()
        headers = self.session()
        payload = {'title':'Another task','status':'To-Do','priority':'Low'}
        for _ in range(27):
            self.assertEqual(self.client.post('/api/tasks/create', headers=headers, json=payload).status_code, 201)
        self.assertEqual(self.client.post('/api/tasks/create', headers=headers, json=payload).status_code, 409)

    def test_request_boundaries(self):
        self.assertEqual(self.client.post('/api/demo/session', json={}, headers={'Origin':'https://unrelated.example'}).status_code, 403)
        self.assertEqual(self.client.post('/api/demo/session', data='not json').status_code, 415)
        self.assertEqual(self.client.post('/api/tasks/create', json={'title':'x'*20000}, headers=self.session()).status_code, 413)
        self.assertEqual(self.client.post('/users/register', json={}).status_code, 404)
        self.assertEqual(self.client.get('/static/../server.py').status_code, 404)

    def test_old_token_cannot_access_reused_sqlite_user_id(self):
        old_headers = self.session()
        with server.SessionLocal() as db:
            for demo in db.query(server.DemoSession):
                demo.expires_at = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(minutes=1)
            db.commit()
        server.cleanup_expired()
        fresh_headers = self.session()
        self.assertEqual(self.client.get('/api/tasks/', headers=old_headers).status_code, 401)
        self.assertEqual(self.client.get('/api/tasks/', headers=fresh_headers).status_code, 200)


def tearDownModule():
    server.engine.dispose()


if __name__ == '__main__':
    unittest.main()
