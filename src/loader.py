import re
from multiprocessing.pool import ThreadPool
from time import sleep
from typing import Iterable, Optional

import requests
from config import config


class Loader:
    URL = "https://api.hh.ru/vacancies"
    alredy_sendet_vacancies = []

    @classmethod
    def _parse(cls, vacancy: dict) -> dict:
        tags = re.findall("[a-zA-Z]{2,}", vacancy["snippet"]["requirement"] + " " + vacancy["name"])
        tags = [t.lower() for t in tags if t != "highlighttext"]
        return dict(
            source_pk=vacancy["id"],
            name=vacancy["name"],
            description=vacancy["snippet"]["requirement"]
            .replace("<highlighttext>", "")
            .replace("</highlighttext>", ""),
            tags=tags,
            source=config["MODULE_UUID"],
            price=vacancy.get("salary", {}).get("from") or 0,
            city=vacancy["area"]["name"],
            remote=vacancy["schedule"]["id"] == "remote",
        )

    @classmethod
    def _get_data(cls) -> Iterable[dict]:
        page = 1
        max_page = 2
        while True:
            if page >= max_page:
                break
            print(f"page {page}", flush=True)
            url = f"{cls.URL}?text={config['SEARCH_WORDS']}&only_with_salary=True&per_page=100&page={page}"
            data = requests.get(url).json()
            # max_page = data["pages"]
            for vacancy in data.get("items", []):
                if not vacancy["snippet"]["requirement"]:
                    continue
                yield cls._parse(vacancy)
            page += 1
            sleep(int(config["SLEEP_BETWEEN_PAGE"]))

    @classmethod
    def _get_description(cls, vacancy_id: int) -> Optional[str]:
        sleep(int(config["SLEEP_BETWEEN_PAGE"]))
        try:
            return requests.get(f"{cls.URL}/{vacancy_id}").json().get("description")
        except:
            return None

    @classmethod
    def _send(cls, data):
        if data["source_pk"] in cls.alredy_sendet_vacancies:
            print(f"{data['source_pk']} already sendet", flush=True)
            return
        data["description"] = cls._get_description(data["source_pk"]) or data["description"]
        cls.alredy_sendet_vacancies.append(data["source_pk"])
        headers = {"Authorization": f"Token {config['TOKEN']}"}
        response = requests.post(config["URL"], json=data, headers=headers)
        print(f"{response.status_code} {response.text}", flush=True)

    @classmethod
    def run(cls):
        while True:
            with open("alredy_sendet_vacancies.txt", "r+") as f:
                cls.alredy_sendet_vacancies = [v for v in f.read().split("\n") if v]
            with ThreadPool(processes=int(config["PROCESSES"])) as pool:
                pool.map(cls._send, cls._get_data())
            with open("alredy_sendet_vacancies.txt", "w") as f:
                if not cls.alredy_sendet_vacancies:
                    sleep(int(config["SLEEP"]))
                    continue
                f.write("\n".join(map(str, cls.alredy_sendet_vacancies)))
            sleep(int(config["SLEEP"]))
