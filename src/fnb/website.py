import os
import zipfile
from contextlib import closing

import sys
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

LOCAL_PAGES = False
# LOCAL_PAGES = True


def read_credentials():
    with open(os.path.join(os.path.expanduser("~"), ".fnb"), "r") as f:
        lines = f.readlines()
        assert len(lines) == 2
        username = lines[0]
        password = lines[1]
        return username, password


def debug(page=""):
    def real_decorator(method):
        def wrap(s, *args, **kwargs):
            if LOCAL_PAGES and page:
                cwd = os.getcwd()
                s.driver.get("file:///" + cwd + "/tst/" + page + "/Online Banking.html")
            try:
                method(s, *args, **kwargs)
            finally:
                s.save_screenshot(method.__name__)
        return wrap
    return real_decorator


class FnbWebsite:
    def __init__(self):
        # https://intoli.com/blog/running-selenium-with-headless-chrome/
        self.download_directory = "/tmp/fnb"
        import shutil
        if os.path.exists(self.download_directory):
            shutil.rmtree(self.download_directory)
        os.makedirs(self.download_directory, exist_ok=True)
        options = webdriver.ChromeOptions()

        prefs = {"profile.default_content_settings.popups": 0,
                 "download.default_directory": self.download_directory}

        options.add_experimental_option("prefs", prefs)

        # options.add_argument('headless')
        # options.add_argument('disable-gpu')
        # options.add_argument('remote-debugging-port=9222')
        # options.add_argument('window-size=1920x1080')
        self.driver = webdriver.Chrome(chrome_options=options)

        # workaround for "Element is not currently interactable and may not be manipulated"
        # self.driver.set_window_size(1920, 1080)

        self.wait = WebDriverWait(self.driver, 10)  # wait 10 seconds

    def save_screenshot(self, name):
        self.driver.save_screenshot('debug/%s.png' % name)

    def close(self):
        self.driver.close()

    def downloaded_filename(self):
        import glob
        filenames = glob.glob(os.path.join(self.download_directory, "*.zip"))

        assert filenames != []
        if len(filenames) > 1:
            print("Warning: Got many files in download dir (%s)" % self.download_directory)
            for filename in filenames:
                print("- %s" % filename)
        return os.path.join(self.download_directory, filenames[0])

    @debug()
    def login(self, username, password):
        if LOCAL_PAGES:
            print("Skipping real login since LOCAL_PAGES=True")
            return
        driver = self.driver

        print("Opening webpage")
        driver.get("https://www.fnb.co.za/")
        print("webpage open")

        input_user = driver.find_element_by_id("user")
        input_password = driver.find_element_by_id("pass")

        submit_button = driver.find_element_by_id("OBSubmit")

        input_user.send_keys(username)

        # For some reason send_keys will submit the form, so accept the alert and move on
        driver.switch_to.alert.accept()
        input_password.send_keys(password)

        print("Submitting form")
        # submit_button.click()

    @debug("logged-in")
    def navigate_logged_in(self):
        print("Navigating logged in")
        element = self.wait.until(EC.element_to_be_clickable((By.LINK_TEXT, 'View account balances')))
        print("got element")
        element.click()

    @debug("my-bank-accounts")
    def navigate_my_bank_accounts(self):
        print("Navigating my bank accounts")
        div_row_more = self.wait.until(EC.element_to_be_clickable((By.ID, 'rowMoreButton2')))
        print("got element")
        div_row_more.click()

    @debug("my-bank-accounts-click-on-more")
    def navigate_my_bank_accounts_more_overlay(self):
        print("Navigating my bank accounts more overlay")
        self.wait.until(EC.presence_of_element_located((By.XPATH, "//div[contains(text(),'Transaction History')]")))
        print("got element")

        transaction_history = None
        for i in range(10):
            for element in self.driver.find_elements_by_id("actionMenuButton%i" % i):
                if "TransactionHistory" in element.get_attribute("onclick"):
                    transaction_history = element
                    break
        transaction_history.click()

    @debug("transaction-history")
    def navigate_transaction_history(self):
        print("Navigating transaction history")
        element = self.wait.until(EC.element_to_be_clickable((By.CLASS_NAME, 'downloadButton')))
        print("got element")
        element.click()

    @debug("transaction-history-download")
    def navigate_transaction_history_download_overlay(self):
        print("Navigating transaction history download overlay")
        element = self.wait.until(EC.element_to_be_clickable((By.ID, 'downloadFormat_dropId')))
        print("got element")
        # Open formats
        element.click()

        # select CSV
        formats = self.driver.find_elements_by_class_name("dropdown-item")
        csv = next(element for element in formats if element.get_attribute("data-value") == "csv")
        csv.click()

        download_button = self.driver.find_element_by_id("mainDownloadBtn")
        download_button.click()

    @debug()
    def logout(self):
        print("Logging out")
        element = self.wait.until(EC.element_to_be_clickable((By.CLASS_NAME, 'headerButtonlogoutBtn')))
        element.click()

        if LOCAL_PAGES:
            return

        self.wait.until(EC.presence_of_element_located((By.XPATH, "//*[contains(text(),'You have successfully logged out of banking')]")))
        print("Successfully logged out")


def download_csv_file() -> str:
    with closing(FnbWebsite()) as website:
        try:
            username, password = read_credentials()

            website.login(username, password)
            website.navigate_logged_in()
            website.navigate_my_bank_accounts()
            website.navigate_my_bank_accounts_more_overlay()
            website.navigate_transaction_history()
            website.navigate_transaction_history_download_overlay()

        finally:
            website.logout()
        zip_filename = website.downloaded_filename()

    with zipfile.ZipFile(zip_filename) as zip_file:
        names = zip_file.namelist()
        zip_file.extractall(website.download_directory)
        assert len(names) == 1
        return os.path.join(website.download_directory, names[0])


if __name__ == "__main__":
    if sys.platform.startswith("linux"):
        from pyvirtualdisplay import Display

        display = Display(visible=0, size=(1920, 1080))
        display.start()

    download_csv_file()
