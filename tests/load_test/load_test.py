# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import logging
from locust import HttpUser, between, task

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class MoMoLedgerUser(HttpUser):
    """Simulates a user interacting with the MoMo Ledger API."""

    wait_time = between(1, 3)  # Wait 1-3 seconds between tasks

    @task(3)
    def view_report(self) -> None:
        """Simulates viewing the financial dashboard report."""
        merchant_id = "merchant_123"
        headers = {"Accept": "application/json"}
            
        with self.client.get(
            f"/report/{merchant_id}",
            name="/report/{merchant_id}",
            headers=headers,
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Failed to fetch report, code: {response.status_code}")

    @task(2)
    def view_score(self) -> None:
        """Simulates viewing the credit score profile."""
        merchant_id = "merchant_123"
        headers = {"Accept": "application/json"}
            
        with self.client.get(
            f"/score/{merchant_id}",
            name="/score/{merchant_id}",
            headers=headers,
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Failed to fetch score, code: {response.status_code}")

    @task(1)
    def view_transactions(self) -> None:
        """Simulates viewing the bookkeeping ledger transactions."""
        merchant_id = "merchant_123"
        headers = {"Accept": "application/json"}
            
        with self.client.get(
            f"/transactions/{merchant_id}",
            name="/transactions/{merchant_id}",
            headers=headers,
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Failed to fetch transactions, code: {response.status_code}")
