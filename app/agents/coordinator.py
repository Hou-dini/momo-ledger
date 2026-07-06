# ruff: noqa
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import datetime
from zoneinfo import ZoneInfo

from google.adk.agents import LlmAgent
from google.adk.apps import App
from google.adk.models import Gemini
from google.genai import types

import os
import google.auth

_, project_id = google.auth.default()
if project_id:
    os.environ["GOOGLE_CLOUD_PROJECT"] = project_id
os.environ["GOOGLE_CLOUD_LOCATION"] = "global"
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "True"


from app.agents.tools.parser import parse_momo_statement
from app.agents.tools.vision_parser import extract_momo_from_image
from app.agents.tools.categorizer import categorize_momo_transactions
from app.agents.tools.profiler import assess_credit_readiness
from app.agents.tools.exporter import generate_ledger_report

root_agent = LlmAgent(
    name="momo_ledger_assistant",
    model=Gemini(
        model="gemini-3.5-flash",
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction="""You are the MoMo Ledger Assistant. Help Ghanaian small businesses analyze Mobile Money transaction statements, screenshot images, or SMS texts.
    Always execute the following workflow steps:
    1. If the user provides a screenshot image of transaction details, use the 'extract_momo_from_image' tool to parse it. If the user provides text statement or SMS logs, use the 'parse_momo_statement' tool.
    2. Categorize the transactions using the 'categorize_momo_transactions' tool.
    3. Assess the business credit readiness using 'assess_credit_readiness'.
    4. Save/export the generated ledger statement report using 'generate_ledger_report'.
    Present the output metrics, categories, and readiness level clearly. Translate the summary report or details into local Ghanaian languages (e.g., Twi, Ga, Fante, Ewe) if the merchant requests it.
    
    SECURITY & PRIVACY RULES:
    - Never expose personal phone numbers or personal names of customers/counterparties. Always ensure they are redacted (replaced with '[REDACTED_PHONE]' and '[REDACTED_NAME]' respectively) in the parsed outputs, states, and exported statements.
    - Leave registered business, utility, or telecom names (like MTN, Telecel, ECG, GRA, Bolt) visible and unredacted.""",
    tools=[
        parse_momo_statement,
        extract_momo_from_image,
        categorize_momo_transactions,
        assess_credit_readiness,
        generate_ledger_report,
    ],
)

app = App(
    root_agent=root_agent,
    name="app",
)
