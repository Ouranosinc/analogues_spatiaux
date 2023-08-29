import pytest

from loadwright import LoadTestRunner, LoadTestViewer, User
from playwright.async_api import expect
import asyncio
import panel as pn
import param
import os
if "LOADWRIGHT_HEADLESS" in os.environ:
  HEADLESS = os.environ.get("LOADWRIGHT_HEADLESS")
else:
	HEADLESS = False

if "LOADWRIGHT_HOST" in os.environ:
	HOST = os.environ.get("LOADWRIGHT_HOST")
else:
	HOST = "https://app-spatial-analogs-staging.climatedata.ca"
	# http://localhost:5006
#page.goto("http://localhost:5006/analogs/Dashboard")


class LoadAndClickUser(User):
		"""A custom User that loads a page and clicks a button n_clicks times"""
		check = param.Boolean(default=False)
  
		async def run(self):
				with self.event(name="load_modal", user=self.name):
						await self.page.goto(self.url)
						await self.page.get_by_text("×").wait_for()
				await self.sleep()

				with self.event(name="load_sidebar", user=self.name):
						await self.page.get_by_text("Target cityAB: CalgaryAB: EdmontonAB: Grande PrairieAB: LethbridgeAB: Red DeerBC").wait_for()
						
				await self.sleep()

				wait_time = 0.5
				with self.event(name="setup_search", user=self.name):
						await self.page.get_by_text("×").click()
						await self.page.get_by_text("Target cityAB: CalgaryAB: EdmontonAB: Grande PrairieAB: LethbridgeAB: Red DeerBC").click()
						await asyncio.sleep(wait_time)
						await self.page.get_by_role("option", name="AB: Calgary").click()
						await asyncio.sleep(wait_time)
						await self.page.get_by_text("High (SSP5-8.5)").click()
						await asyncio.sleep(wait_time)
						await self.page.get_by_text("Climate indices (select up to 4)Coldest dayCooling degree daysDays with tmax > 2").click()
						await asyncio.sleep(wait_time)
						await self.page.get_by_role("option", name="Frost days").click()
						await asyncio.sleep(wait_time)
						await self.page.get_by_role("button", name="Run analogues search").click()
				await self.sleep()

				with self.event(name="await_search", user=self.name):
						await self.page.get_by_text("Based on the climate index chosen (Frost days)").wait_for()
				await self.sleep()
    
				if self.check:
					with self.event(name="check_search", user=self.name):
							for i,city in enumerate([
																"Billings",      "Lethbridge",  "Idaho Falls",
																"St.-Jerome",    "Idaho Falls", "Duluth",
																"Salt Lake City","Minneapolis", "Toronto",
																"Idaho Falls",   "St. Paul",    "Billings"]):
								btn = i + 1
								if btn > 1:
									await self.page.get_by_role("button", name=f"#{btn}").click()
								await asyncio.sleep(wait_time*2)
								texts = await self.page.get_by_text("Based on the climate index chosen (Frost days)").all_inner_texts()
								
								assert any(city in text for text in texts),f"{city} not found in {texts}" 
					await self.sleep()

#HOST = "http://localhost:5006"
@pytest.mark.asyncio
async def test_component_2(port=6001):
		"""We can run the LoadTestRunner with 5 users each clicking 5 times"""
		address = "/analogs/Dashboard"
		runner = LoadTestRunner(host=HOST + address, headless=HEADLESS, user=LoadAndClickUser(check=True), n_users=1)
		await runner.run()
  
@pytest.mark.asyncio
async def test_component_3(port=6001):
		"""We can run the LoadTestRunner with 5 users each clicking 5 times"""
		address = "/analogs/Dashboard"
		runner = LoadTestRunner(host=HOST + address, headless=HEADLESS, user=LoadAndClickUser(check=False), n_users=10)
		await runner.run()
  
if pn.state.served:
		import panel as pn
		pn.extension(sizing_mode="stretch_width")
		viewer = LoadTestViewer(data="test_results/loadwright.csv")
		pn.template.FastListTemplate(
				site="LoadWright",
				title="Load Testing with Playwright and Panel",
				main=[viewer]
		).servable()