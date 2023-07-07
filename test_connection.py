from selenium import webdriver
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.common.by import By

import unittest

url = 'https://pavics.ouranos.ca/jupyter/user-redirect/proxy/9094/Dashboard'
timeout = 30
class AnalogsExists(unittest.TestCase):
    def setUp(self):
        self.browser = webdriver.Firefox()
        self.browser.implicitly_wait(timeout)
        self.browser.get(url)
        self.addCleanup(self.browser.quit)
    
    def test_page_title(self):
        self.assertIn('Climate Analogues',self.browser.title)
        
    def find_and_assert_sidebar(browser):
        element = browser.find_element(by=By.CLASS_NAME, value='sidebar-title')
        text = element.text
        print(text)
        return 'new search' in text
    
    def test_page_sidebar(self):
        self.element = WebDriverWait(self.browser,timeout).until(AnalogsExists.find_and_assert_sidebar)
        self.assertTrue(self.element)

if __name__ == '__main__':
    unittest.main(verbosity=2)