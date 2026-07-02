from locust import HttpUser, task, constant_pacing
import random
from uuid import uuid4

class DeliveryUser(HttpUser):
    token = None
    request_ids = []
    wait_time = constant_pacing(3)

    def on_start(self):
        if DeliveryUser.token is None:
            response = self.client.post("/auth/login", json={
                "email": "admin@sdr.com",
                "password": "admin"
            })
            DeliveryUser.token = response.json()["access_token"]

    @task(1)
    def get_health(self):
        self.client.get("/health")

    @task(5)
    def get_shipping_requests(self):
        self.client.get("/shipping-requests", headers={
            "Authorization": f"Bearer {self.token}"
        })

    @task(1)
    def get_parcels(self):
        self.client.get("/parcels", headers={
            "Authorization": f"Bearer {self.token}"
        })

    @task(1)
    def create_shipping_request(self):
        body = {
            "id": str(uuid4()),
            "external_order_id": f"ORD-{random.randint(1000, 9999)}",
            "seller_id": "550e8400-e29b-41d4-a716-446655440000",
            "pickup_address_text": "123 Nguyen Hue, Q1, TP.HCM",
            "pickup_lat": 10.7769,
            "pickup_lng": 106.7009,
            "delivery_address_text": "456 Le Loi, Q3, TP.HCM",
            "delivery_lat": 10.7800,
            "delivery_lng": 106.7100,
            "receiver_name": "Nguyen Van A",
            "receiver_phone": "0901234567",
            "weight": round(random.uniform(0.5, 10.0), 2),
            "volume": round(random.uniform(0.01, 0.5), 3),
            "service_type": 1,
        }

        with self.client.post(
            "/shipping-requests", 
            headers={"Authorization": f"Bearer {self.token}"},
            json=body,
            catch_response=True
        ) as response:
            if response.status_code == 201:
                DeliveryUser.request_ids.append(response.json()["id"])
                response.success()
            else:
                response.failure(f"Got {response.status_code}")

    @task(3)
    def get_shipping_request_detail(self):
        if not DeliveryUser.request_ids:
            return
        req_id = random.choice(DeliveryUser.request_ids)
        self.client.get(
            f"/shipping-requests/{req_id}",
            headers={"Authorization": f"Bearer {self.token}"},
        )
