import unittest
import json
from app import app, db, User, ButcherShop, MeatData

class MeatFreshnessAppTestCase(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.app = app.test_client()
        self.ctx = app.app_context()
        self.ctx.push()
        db.create_all()

        # Create an admin user
        admin = User(username='admin', password='adminpass', user_type='admin')
        db.session.add(admin)
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def test_signup_and_login(self):
        # Sign up a new user (manager)
        response = self.app.post('/signup', data=json.dumps({
            'username': 'manager1',
            'password': 'password123',
            'user_type': 'manager'
        }), content_type='application/json')
        print(response.data)  # Debugging print statement
        self.assertEqual(response.status_code, 201)

        # Login as the new user
        response = self.app.post('/login', data=json.dumps({
            'username': 'manager1',
            'password': 'password123'
        }), content_type='application/json')
        print(response.data)  # Debugging print statement
        self.assertEqual(response.status_code, 200)
        access_token = json.loads(response.data).get('access_token')
        self.assertIsNotNone(access_token)

        # Sign up a new user (customer)
        response = self.app.post('/signup', data=json.dumps({
            'username': 'customer1',
            'password': 'password123',
            'user_type': 'customer'
        }), content_type='application/json')
        print(response.data)  # Debugging print statement
        self.assertEqual(response.status_code, 201)

        # Login as the new user
        response = self.app.post('/login', data=json.dumps({
            'username': 'customer1',
            'password': 'password123'
        }), content_type='application/json')
        print(response.data)  # Debugging print statement
        self.assertEqual(response.status_code, 200)
        access_token = json.loads(response.data).get('access_token')
        self.assertIsNotNone(access_token)

    def test_register_shop(self):
        # Login as manager
        self.app.post('/signup', data=json.dumps({
            'username': 'manager1',
            'password': 'password123',
            'user_type': 'manager'
        }), content_type='application/json')
        response = self.app.post('/login', data=json.dumps({
            'username': 'manager1',
            'password': 'password123'
        }), content_type='application/json')
        access_token = json.loads(response.data).get('access_token')

        # Register a new butcher shop
        response = self.app.post('/register_shop', data=json.dumps({
            'name': 'Best Butcher',
            'location': '123 Meat St',
            'contact': '555-5555',
            'manager_id': 1
        }), headers={'Authorization': f'Bearer {access_token}'}, content_type='application/json')
        self.assertEqual(response.status_code, 201)

    def test_store_and_calculate_meat_data(self):
        # Login as customer
        self.app.post('/signup', data=json.dumps({
            'username': 'customer1',
            'password': 'password123',
            'user_type': 'customer'
        }), content_type='application/json')
        response = self.app.post('/login', data=json.dumps({
            'username': 'customer1',
            'password': 'password123'
        }), content_type='application/json')
        access_token = json.loads(response.data).get('access_token')

        # Register a new butcher shop as a prerequisite
        self.app.post('/signup', data=json.dumps({
            'username': 'manager1',
            'password': 'password123',
            'user_type': 'manager'
        }), content_type='application/json')
        response = self.app.post('/login', data=json.dumps({
            'username': 'manager1',
            'password': 'password123'
        }), content_type='application/json')
        manager_access_token = json.loads(response.data).get('access_token')
        self.app.post('/register_shop', data=json.dumps({
            'name': 'Best Butcher',
            'location': '123 Meat St',
            'contact': '555-5555',
            'manager_id': 1
        }), headers={'Authorization': f'Bearer {manager_access_token}'}, content_type='application/json')

        # Store meat data
        response = self.app.post('/meat_data', data=json.dumps({
            'impedance': 100.0,
            'purchase_date': '2024-07-10T00:00:00',
            'butcher_shop_id': 1,
            'part': 'loin'
        }), headers={'Authorization': f'Bearer {access_token}'}, content_type='application/json')
        self.assertEqual(response.status_code, 201)

        # Calculate quality
        response = self.app.post('/calculate_quality', data=json.dumps({
            'impedance': 110.0,
            'purchase_date': '2024-07-10T00:00:00',
            'butcher_shop_id': 1,
            'part': 'loin'
        }), headers={'Authorization': f'Bearer {access_token}'}, content_type='application/json')
        self.assertEqual(response.status_code, 200)
        quality_degradation = json.loads(response.data).get('quality_degradation')
        self.assertEqual(quality_degradation, 10.0)  # Example formula (110 - 100) / 100 * 100

    def test_admin_functions(self):
        # Login as admin
        response = self.app.post('/login', data=json.dumps({
            'username': 'admin',
            'password': 'adminpass'
        }), content_type='application/json')
        print(response.data)  # Debugging print statement
        access_token = json.loads(response.data).get('access_token')

        # Get user list
        response = self.app.get('/admin/users', headers={'Authorization': f'Bearer {access_token}'})
        self.assertEqual(response.status_code, 200)
        users = json.loads(response.data)
        self.assertGreater(len(users), 0)

        # Get shop list
        response = self.app.get('/admin/shops', headers={'Authorization': f'Bearer {access_token}'})
        self.assertEqual(response.status_code, 200)
        shops = json.loads(response.data)
        self.assertGreater(len(shops), 0)

if __name__ == '__main__':
    unittest.main()
