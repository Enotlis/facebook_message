from argparse import ArgumentParser
import os
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
import selenium.common.exceptions

def parse_cmd_args():
    '''Получение аргументов из командной строки'''
    module_usage = 'get_message.py login password\n необходимо ввести логин и пароль аккаунта'
    parse = ArgumentParser(usage=module_usage,
                           description="Получение сообщений из аккаунта facebook",
                           add_help=True)
    parse.add_argument(dest="login", type=str, help="введите логин аккаунта")
    parse.add_argument(dest="password", type=str, help="введите пароль аккаунта")
    cmd_args = parse.parse_args()
    return cmd_args.login, cmd_args.password

class FacebookCrawler:
    LOGIN_URL = 'https://www.facebook.com/login.php?login_attempt=1&lwv=111'
    USER_AGENT = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                  'AppleWebKit/537.36 (KHTML, like Gecko) '
                  'Chrome/83.0.4103.53 Safari/537.36')
    SCROLL_PAUSE_TIME = 5
    URL_DIALOGS = []
    UNREAD_NUMBER_LIST = []

    def __init__(self, login_account: str, password_account: str):
        chrome_options = webdriver.ChromeOptions()
        prefs = {"profile.default_content_setting_values.notifications": 2}
        chrome_options.add_argument(f'user-agent={self.USER_AGENT}')
        chrome_options.add_experimental_option("prefs", prefs)
        chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])

        self.driver = webdriver.Chrome(os.path.join('.', 'chromedriver.exe'),
                                       chrome_options=chrome_options)
        self.wait = WebDriverWait(self.driver, 10)

        self.login(login_account, password_account)

    def login(self, login_account: str, password_account: str):
        '''Вход в аккаунт под указанным логином'''
        self.driver.get(self.LOGIN_URL)

        #ожидание пока загрузится страница входа
        self.wait.until(EC.visibility_of_element_located((By.ID, "email")))

        self.driver.find_element(By.ID, 'email').send_keys(login_account)
        self.driver.find_element(By.ID, 'pass').send_keys(password_account)
        self.driver.find_element(By.ID, 'loginbutton').click()

        #ожидание пока загрузится главная страница
        self.wait.until(
            EC.visibility_of_element_located(
                (By.XPATH,
                 "//div[@aria-label='Управление аккаунтом и его настройки']/div[2]")
            )
        )

    def receiving_first_chat(self):
        '''получение первого чата и его статуса, переход в него'''
        elem = self.driver.find_element(By.XPATH,
                                        ("//div[@aria-label='Управление аккаунтом и его настройки']"
                                         "/div[2]")
                                        )
        actions = ActionChains(self.driver)
        actions.move_to_element(elem)
        actions.click()
        actions.perform()

        self.wait.until(
            EC.visibility_of_element_located(
                (By.XPATH,
                 "//div[@data-testid='mwthreadlist-item-open']")
            )
        )
        item = self.driver.find_element(By.XPATH,
                                        "//div[@data-testid='mwthreadlist-item-open']")
        url_dialog = item.find_element(By.TAG_NAME, 'a').get_attribute('href')

        try:
            item.find_element(By.TAG_NAME, 'a').find_element(By.XPATH,
                                                             (".//span[@class='pq6dq46d is6700om cyypbtt7 "
                                                              "fwizqjfa s45kfl79 emlxlaya bkmhp75w spb7xbtv "
                                                              "qu0x051f esr5mh6w e9989ue4 r7d6kgcz']")
                                                             )
            self.UNREAD_NUMBER_LIST.append(0)
        except selenium.common.exceptions.NoSuchElementException:
            pass

        #переход в первый диалог
        self.driver.get(url_dialog)
        self.wait.until(
            EC.visibility_of_element_located(
                (By.XPATH,
                 "//div[@data-testid='mwthreadlist-item-open']")
            )
        )

    def find_all_url_messages(self):
        '''сбор всех url чатов'''
        #загрузить все чаты, проскроллив до конца
        try:
            elem = self.driver.find_element(By.XPATH,
                                            "//div[@class='ay7djpcl b5wmifdl hzruof5a pmk7jnqg rfua0xdk kr520xx4']")
            actions = ActionChains(self.driver)
            actions.move_to_element(elem).click().perform()
            actions.click().perform()
            actions.perform()
            last_count = len(self.driver.find_elements(By.XPATH,
                                                       "//div[@data-testid='mwthreadlist-item-open']"))

            while True:
                actions.key_down(Keys.END).perform()
                time.sleep(self.SCROLL_PAUSE_TIME)

                new_count = len(self.driver.find_elements(By.XPATH,
                                                          "//div[@data-testid='mwthreadlist-item-open']"))
                if new_count == last_count:
                    break
                last_count = new_count
        except selenium.common.exceptions.NoSuchElementException:
            pass

        #получение ссылок на диалоги за 2 недели
        items = self.driver.find_elements(By.XPATH,
                                          "//div[@data-testid='mwthreadlist-item-open']")

        for item in items:
            cur_time = item.find_element(By.XPATH,
                                         ".//span[@data-testid='timestamp']").text

            if 'мин.' in cur_time or 'ч.' in cur_time or 'д.' in cur_time:
                url_dialog = item.find_element(By.TAG_NAME, 'a').get_attribute('href')
                self.URL_DIALOGS.append(url_dialog)
                try:
                    item.find_element(By.TAG_NAME, 'a').find_element(By.XPATH,
                                                                     (".//span[@class='pq6dq46d is6700om cyypbtt7 "
                                                                      "fwizqjfa s45kfl79 emlxlaya bkmhp75w spb7xbtv "
                                                                      "qu0x051f esr5mh6w e9989ue4 r7d6kgcz']")
                                                                     )
                    self.UNREAD_NUMBER_LIST.append(items.index(item))
                except selenium.common.exceptions.NoSuchElementException:
                    pass
            elif 'нед.' in cur_time:
                count_week = cur_time.split(' ')
                if count_week <= 2:
                    url_dialog = item.find_element(By.TAG_NAME, 'a').get_attribute('href')
                    self.URL_DIALOGS.append(url_dialog)
                    try:
                        item.find_element(By.TAG_NAME, 'a').find_element(By.XPATH,
                                                                         (".//span[@class='pq6dq46d is6700om cyypbtt7 "
                                                                          "fwizqjfa s45kfl79 emlxlaya bkmhp75w spb7xbtv "
                                                                          "qu0x051f esr5mh6w e9989ue4 r7d6kgcz']")
                                                                         )
                        self.UNREAD_NUMBER_LIST.append(items.index(item))
                    except selenium.common.exceptions.NoSuchElementException:
                        pass

    def parse_messages(self):
        '''получение всех сообщений из чатов'''
        self.receiving_first_chat()
        self.find_all_url_messages()

        with open('messages.txt', 'w+') as file:
            for url_dialog in self.URL_DIALOGS:
                self.driver.get(url_dialog)
                self.wait.until(EC.visibility_of_element_located((By.XPATH,
                                                                  "//div[@class='buofh1pr j83agx80 eg9m0zos ni8dbmo4 cbu4d94t gok29vw1 isf3ygkp']")))
                time.sleep(3)

                try:
                    elem = self.driver.find_element(By.XPATH,
                                                    "//div[@class='buofh1pr j83agx80 eg9m0zos ni8dbmo4 cbu4d94t gok29vw1 isf3ygkp']")
                    last_count_messages = len(self.driver.find_elements(By.XPATH,
                                                                        "//div[@class='__fb-light-mode l9j0dhe7']"))

                    actions = ActionChains(self.driver)
                    actions.move_to_element_with_offset(elem, elem.size["width"] - 5, elem.size["height"] - 5).click().perform()
                    actions.click().perform()
                    actions.perform()

                    while True:
                        actions.key_down(Keys.HOME).perform()
                        time.sleep(self.SCROLL_PAUSE_TIME)

                        new_count_messages = len(self.driver.find_elements(By.XPATH,
                                                                           "//div[@class='__fb-light-mode l9j0dhe7']"))
                        if new_count_messages == last_count_messages:
                            break
                        last_count_messages = new_count_messages
                except selenium.common.exceptions.NoSuchElementException:
                    pass

                string = (f"https://www.facebook.com/profile.php?id={url_dialog.split('/')[5]}\n"
                          + self.driver.find_element(By.XPATH,
                                                     "//div[@class='rj1gh0hx buofh1pr j83agx80 l9j0dhe7 cbu4d94t ni8dbmo4 stjgntxs nwf6jgls']").text
                         )
                file.write(string)
                file.write('\n-------------------------------------------------------------------------\n')

        items = self.driver.find_elements(By.XPATH, "//div[@data-testid='mwthreadlist-item-open']")
        if len(self.UNREAD_NUMBER_LIST) != 0:
            for i in self.UNREAD_NUMBER_LIST:

                #отметить как не прочитанные
                elem = items[i].find_element(By.XPATH, ".//div[@aria-label='Меню']")
                actions = ActionChains(self.driver)
                actions.move_to_element(elem).click().perform()
                actions.move_to_element(items[i].find_element(By.XPATH,
                                                              ("//span[@class='d2edcug0 hpfvmrgz qv66sw1b c1et5uql "
                                                               "lr9zc1uh a8c37x1j fe6kdd0r mau55g9w c8b282yb keod5gw0 "
                                                               "nxhoafnm aigsh9s9 d3f4x2em iv3no6db jq4qci2q a3bd9o3v "
                                                               "ekzkrbhg oo9gr5id hzawbc8m']")
                                                              )
                                        ).click().perform()

        self.driver.quit()


if __name__ == '__main__':
    login, password = parse_cmd_args()
    crawler = FacebookCrawler(login_account=login, password_account=password)

    crawler.parse_messages()
    print('END')
