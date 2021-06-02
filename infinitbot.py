# Author: Daniel Torres

# Monitor the website https://releases.43einhalb.com/en/ and
# send a message to Slack when a new raffle is published.
# It must use Python and the modul requests (not webdriver).

import requests
import json
import time

# from bs4 import BeautifulSoup
from user_agent import generate_user_agent
from lxml.html import fromstring
from slack_webhook import Slack


AGENT = generate_user_agent(os=('mac', 'linux'))
HEADERS = {'User-Agent': AGENT}


def get_text_from_element(element):
	return element.xpath('./text()')[0]


def get_url_response(url):
	global HEADERS
	response = requests.get(url, headers=HEADERS)
	return response


def response_is_200(response):
	return response.status_code == requests.codes.ok


def get_html_tree(response):
	html_tree = fromstring(response.text)
	return html_tree


def get_list_of_open_raffles(html_tree):
	list_of_open_raffles = html_tree.xpath('//span[@class="display-variation raffle"]')
	return list_of_open_raffles


def get_sibling_element(element, location, tag, attribute, name):
	parent = element.xpath('..')[0]
	sibling = parent.xpath(location + '/' + tag + \
		'[@' + attribute + \
		'="' + name + '"]')[0]
	return sibling


def get_sneaker_raffle_url(sneaker_element):
	global main_url
	sneaker_url = sneaker_element.xpath("./a[contains(@href, '/en/')]")[0].get('href')
	sneaker_url = main_url[:-4] + sneaker_url
	return sneaker_url


def get_picture(sneaker_tree):
	picture_url = sneaker_tree.xpath('//img[@itemprop="associatedMedia"]')[0]
	picture_url = picture_url.get('src')
	return picture_url


def get_model_brand_referenceCode(sneaker_tree):
	brand_and_model_element = sneaker_tree.xpath('//h1[@class="h3"]')[0]
	brand_and_model = get_text_from_element(brand_and_model_element)
	brand = brand_and_model.split('-')[0]
	model = brand_and_model.split('-')[1]
	sibling = get_sibling_element(brand_and_model_element, '/', 'span', 'class', 'text-muted')
	referenceCode = get_text_from_element(sibling)
	return model, brand, referenceCode


def get_price(sneaker_tree):
	price_element = sneaker_tree.xpath('//span[@class="price h3 m-0 py-1"]')[0]
	price = get_text_from_element(price_element)
	if price[0] == '€':
		currency = 'EUR'
	elif price[0] == '$':
		currency = 'USD'
	else:
		raise NameError('CurrencyNotInTheSystem')
	value = price[1:]
	return value, currency


def get_closing_date(sneaker_tree):
	date = sneaker_tree.xpath('//li[contains(text(), "Raffle closes on")]')[0]
	date = get_text_from_element(date)
	month = date.split(',')[0].split()[3]
	day = date.split(',')[0].split()[4][:-2]
	hour = date.split(',')[1].split()[2]
	time_zone = date.split(',')[1].split()[4][:-1]
	return month, day, hour, time_zone


def get_sizes(sneaker_tree):
	parent = sneaker_tree.xpath('//select[@id="selectVariation"]')[0]
	min_size = parent.xpath('./option[@class="text-muted dropdown-item"]')[0]
	min_size = get_text_from_element(min_size)
	country = min_size.split('·')[1].split()[1][:-1]
	min_size = min_size.split('·')[1].split()[0]
	max_size = parent.xpath('./option[@class="text-muted dropdown-item"]')[-1]
	max_size = get_text_from_element(max_size)
	max_size = max_size.split('·')[1].split()[0]
	return min_size, max_size, country


def send_webhook(sneaker_url, picture_url, model, brand, referenceCode, value, currency, month, day, hour, time_zone, min_size, max_size, country):
	slack = Slack(url='https://hooks.slack.com/services/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')
	slack.post(text="Raffle Monitor",
	    attachments = [{
	        "text": '<' + sneaker_url + '>' + '\n' + model + '\n' +\
	        brand + '\n' +\
	        referenceCode + '\n' +\
	        value + ' ' + currency + '\n' +\
	        month + ' ' + day + ' @ ' + hour + ':00 ' + time_zone + '\n' +\
	        min_size + ' - ' + max_size + ' ' + country
	    }]
	)


riffled_sneakers = []
main_url = 'https://releases.43einhalb.com/en/'

while (True):
	main_response = get_url_response(main_url)
	if response_is_200(main_response):
		main_tree = get_html_tree(main_response)
		open_raffles = get_list_of_open_raffles(main_tree)
		for sneaker in open_raffles:
			sibling = get_sibling_element(sneaker, '.', 'div', 'class', 'product-image mb-2 mb-md-3 bg-gray-100')
			sneaker_url = get_sneaker_raffle_url(sibling)
			if sneaker_url not in riffled_sneakers:
				riffled_sneakers.append(sneaker_url)
				sneaker_response = get_url_response(sneaker_url)
				if response_is_200(sneaker_response):
					sneaker_tree = get_html_tree(sneaker_response)
					picture_url = get_picture(sneaker_tree)
					model, brand, referenceCode = get_model_brand_referenceCode(sneaker_tree)
					value, currency = get_price(sneaker_tree)
					month, day, hour, time_zone = get_closing_date(sneaker_tree)
					min_size, max_size, country = get_sizes(sneaker_tree)
					send_webhook(sneaker_url, picture_url, model, brand, referenceCode, value, currency, month, day, hour, time_zone, min_size, max_size, country)
				else:
					sneaker_response.raise_for_status()
		time.sleep(10)
	else:
		main_response.raise_for_status()
