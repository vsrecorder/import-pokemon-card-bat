from dotenv import load_dotenv

import os
import sys
import logging
import time

import requests
import psycopg2

from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

url = "https://www.pokemon-card.com/card-search/details.php/card/"

max_retries = 10
initial_interval = 2


def search(card_id):
    try:
        #logger.info(f"Request start: {url + str(card_id)}")

        res = requests.get(url + str(card_id), timeout=3)
        res.raise_for_status()

        #logger.info(f"Request succeeded: {url + str(card_id)} (status={res.status_code})")
        return res.text

    except requests.exceptions.Timeout:
        logger.warning(f"Timeout occurred: {url + str(card_id)}")
        return ""

    except requests.exceptions.HTTPError as e:
        status = getattr(e.response, "status_code", 500)
        logger.error(f"HTTPError: {url + str(card_id)} -> status {status}")
        return ""

    except requests.exceptions.ConnectionError as e:
        logger.error(f"ConnectionError: {url + str(card_id)} -> {e}")
        return ""

    except requests.exceptions.RequestException as e:
        logger.exception(f"Unexpected RequestException: {url + str(card_id)} -> {e}")
        return ""


def search_with_retry(card_id):
    interval = initial_interval

    for attempt in range(1, max_retries):
        text = search(card_id)

        if text != "":
            return text

        if attempt == max_retries:
            sys.exit(1)

        logger.info(f"Failed to search card (card_id: {str(card_id)})(attempt {str(attempt)}/{str(max_retries)})")

        time.sleep(interval)
        interval *= 2


def insert(conn, card_id):
    html_doc = str(search_with_retry(card_id))

    bs = BeautifulSoup(html_doc, "html.parser")

    section_tag = bs.find_all('section', attrs={"class": "Section"})

    if len(section_tag) != 1:
        return None

    bs = BeautifulSoup(str(section_tag[0]), "html.parser")
    h1_tag = bs.find_all('h1', attrs={"class": "Heading1 mt20"})[0]

    card_name = h1_tag.get_text(strip=True)

    div_tag = bs.find_all('div', attrs={"class": "RightBox"})[0]

    bs = BeautifulSoup(str(div_tag), "html.parser")

    for span in bs.find_all('span', attrs={"class": "f_right Text-fjalla"}):
        span.decompose() 


    h2_tag = bs.find_all('h2', attrs={"class": "mt20"})
    h4_tag = bs.find_all('h4', attrs={"class": ""})                 

    ability = ""
    attack = ""
    if h2_tag[0].get_text() == "特性":
        ability = h4_tag[0].get_text(strip=True)

        for index, value in enumerate(h4_tag[1:]):
            attack += value.get_text(strip=True)

            if index != len(h4_tag[1:])-1:
                attack += "/"

    if h2_tag[0].get_text() == "ワザ":
        if len(h2_tag) >= 2 and h2_tag[1].get_text() == "VSTARパワー":
            for index, value in enumerate(h4_tag): 
                if value.get_text(strip=True) == "ワザ":
                    attack += h4_tag[index+1].get_text(strip=True)
                    break
                elif value.get_text(strip=True) == "特性":
                    ability += h4_tag[index+1].get_text(strip=True)
                    break
                else:
                    attack += value.get_text(strip=True)
                    if h4_tag[index+1].get_text(strip=True) == "ワザ":
                        attack += "/"
        else:
            for index, value in enumerate(h4_tag):
                attack += value.get_text(strip=True)

                if index != len(h4_tag)-1:
                    attack += "/"

    with conn.cursor() as cur:
        insert_sql = "INSERT INTO pokemon_cards (id, card_name, ability, attack) VALUES (%s, %s, %s, %s)"
        try:
            cur.execute(insert_sql, (card_id, card_name, ability, attack))
            conn.commit()
        except psycopg2.errors.UniqueViolation:
            try:
                conn.rollback()
                update_sql = "UPDATE pokemon_cards SET card_name = %s, ability = %s, attack = %s WHERE id = %s"
                cur.execute(update_sql, (card_name, ability, attack, card_id))
                conn.commit()
            except psycopg2.Error as e:
                logger.error(f"Update failed for card_id: {card_id}: {e}")
                conn.rollback()
        except psycopg2.Error as e:
            logger.error(f"Insert failed for card_id: {card_id}: {e}")
            conn.rollback()

    print(card_name)
    print("特性:", ability)
    print("ワザ:", attack)
    print()



if __name__ == "__main__":
    load_dotenv()

    host = os.getenv("DB_HOSTNAME")
    port = os.getenv("DB_PORT")
    user = os.getenv("DB_USER_NAME")
    password = os.getenv("DB_USER_PASSWORD")
    dbname = os.getenv("DB_NAME")
    dsn = "host={} port={} user={} password={} dbname={} sslmode=disable".format(host, port, user, password, dbname)

    conn = psycopg2.connect(dsn)
    cur = conn.cursor()
    cur.execute("SELECT id FROM cards WHERE card_category = 1 AND regulation_mark IN ('H', 'I', 'J') ORDER BY id")

    for row in cur:
        card_id = row[0]
        print(card_id)
        insert(conn, card_id)
        time.sleep(0.3)

    cur.close()
    conn.close()
