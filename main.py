from collections import defaultdict
import datetime
import json
import logging
import os
import time

import requests
from selenium import webdriver
from selenium.webdriver.chrome.webdriver import Options

from retry import retry


if os.environ.get('ENV', 'test') == 'test':
    config = 'test'
else:
    config = 'prod'
config_dict = json.load(open(f'config/{config}.json'))

CREDENTIALS = config_dict['credentials']
print(f'Using credentials\n{CREDENTIALS}')
SPREADSHEET_URL = config_dict['spreadsheet_url']
WEEKDAYS = ['ponedelnik', 'vtornik', 'sreda', 'chetverg', 'pyatnica']
WEEKDAYS_EN = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
MINIMAL_SUM = 200


# TODO Check individual sums (whether they are equal to the actual sum computed on the site)


@retry(n_tries=5, time_delta=60)
def make_order(driver, order, inverse_order, reported_sums, total_sum):
    # Filling the order
    prices = defaultdict(int)
    table = driver.find_element_by_xpath('//*[@id="midmid"]/form/table[1]')
    rows = table.find_elements_by_xpath('.//tr')
    for _id, cnt in order.items():
        if not 1 <= _id <= len(rows):
            logging.warning(f'Bad value {_id} in orders of {inverse_order[_id]}')
            continue
        row = rows[_id - 1]
        cells = row.find_elements_by_xpath('.//td')
        cells[5].find_element_by_xpath('.//input').send_keys(cnt)
        price = cells[4].find_element_by_xpath('.//input').get_attribute('value')
        prices[_id] = int(price)

    # Checking individual sums
    _check_sums(inverse_order, reported_sums, prices)

    # Filling the address / name / phone
    form = driver.find_elements_by_class_name('input2')
    for i, val in enumerate(CREDENTIALS):
        form[i].send_keys(val)

    # Computing the final sum of an order
    driver.find_element_by_xpath('//*[@id="midmid"]/form/div/input[1]').click()
    time.sleep(1)
    final_sum = int(driver.find_element_by_xpath('//*[@id="summamokrici"]').text)
    if final_sum != total_sum:
        logging.warning(f'final_sum = {final_sum} not equal to total_sum = {total_sum}')
    if final_sum < MINIMAL_SUM:
        logging.error(f'final_sum = {final_sum} is less than minimal required sum = {MINIMAL_SUM}')
        return

    # Confirming order
    if config == 'prod':
        driver.find_element_by_xpath('//*[@id="midmid"]/form/div/input[2]').click()
    time.sleep(10)


def _check_sums(inverse_order, reported_sums, prices):
    true_sums = defaultdict(int)
    for id, names in inverse_order.items():
        price = prices.get(id, 0)
        for name in names:
            true_sums[name] += price
    for name, true_sum in true_sums.items():
        reported_sum = reported_sums[name]
        if true_sum != reported_sum:
            logging.warning(f'true_sum = {true_sum} not equal to reported_sum = {reported_sum} for {name}')


@retry(n_tries=5, time_delta=60, exceptions=requests.exceptions.RequestException)
def get_orders(tomorrow_num):
    logging.info(f'Making order for {WEEKDAYS_EN[tomorrow_num]}')

    try:
        r = requests.get(SPREADSHEET_URL)
    except requests.exceptions.RequestException as e:
        logging.error(f'Request exception happened: {e}')
        raise

    r.encoding = 'utf-8'
    data = r.text
    lines = [line.strip() for line in data.split('\n')]
    names_line = lines[0].split('\t')
    order_line = lines[2 + tomorrow_num].split('\t')
    assert order_line[0] == WEEKDAYS_EN[tomorrow_num]
    return _extract_order(names_line, order_line)


def _extract_order(names_line, order_line):
    """
    :param names_line:  | Day       |      Ann    |      Bob    |     Carl    |     |
    :param order_line:  | Monday    | order | sum | order | sum | order | sum | SUM |
    :return: order = {position: count},
             inverse_order = {position: [who ordered]},
             individual_sums = {"name": reported sum},
             total_sum
    """
    order = defaultdict(int)
    inverse_order = defaultdict(list)
    reported_sums = dict()
    total_sum = 0
    for i in range(2, len(order_line), 2):
        name = names_line[i].strip()
        if not order_line[i]:
            logging.info(f'Empty order for {name}. Skipping')
            continue

        order_raw = order_line[i].split(',')
        user_order = []
        for entry in order_raw:
            try:
                user_order.append(int(entry))
            except ValueError:
                logging.warning(f'Bad id for {name}: order_line[i] = {order_line[i]}, bad entry = {entry}')

        for entry in user_order:
            order[entry] += 1
            inverse_order[entry].append(name)

        try:
            cur_sum = int(order_line[i + 1])
        except ValueError:
            logging.warning(f'Bad sum for {name}: sum_field = {order_line[i + 1]}')
            cur_sum = 0
        reported_sums[name] = cur_sum
        total_sum += cur_sum

    return order, inverse_order, reported_sums, total_sum


def main():
    today_num = datetime.datetime.now().weekday()  # 0 ~ Monday, 6 ~ Sunday
    tomorrow_num = (today_num + 1) % 7
    tomorrow_name = WEEKDAYS[tomorrow_num]

    order, inverse_order, reported_sums, total_sum = get_orders(tomorrow_num)
    if not order:
        logging.warning('No orders today')
        return

    options = None
    # if config == 'prod':
    #     options = Options()
    #     options.headless = True

    with webdriver.Chrome(executable_path=os.path.abspath('./chromedriver'), chrome_options=options) as driver:
        driver.set_page_load_timeout(3)
        driver.get(f'http://obed.in.ua/menu/{tomorrow_name}/index.php')

        # Selenium doesn't return status code so checking this way
        if 'This site can’t be reached' in driver.page_source:
            logging.error("Page didn't load")
            time.sleep(60)

        make_order(driver, order, inverse_order, reported_sums, total_sum)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, filename='orders.log', format='%(asctime)s :: %(levelname)s :: %(message)s')
    logging.info('START')
    try:
        main()
    except Exception as e:
        logging.error(f'Error in main, {type(e)}')
        logging.error(e)
