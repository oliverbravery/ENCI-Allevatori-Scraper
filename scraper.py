from models import *
import requests
from bs4 import BeautifulSoup
import json
import time
import numpy as np
import sys

def get_areas() -> list[Area]:
    URL = f"https://www.enci.it/allevatori/allevatori-con-affisso?codRegione=PIE"
    page = requests.get(URL)
    soup = BeautifulSoup(page.content, "html.parser")
    map = soup.find("map", {"name": "ENCI_italia_Map"})
    area_tags = map.find_all("area")
    areas: list[Area] = []
    for a in area_tags:
        current_area = Area(a["title"], a["data-regione"])
        if current_area not in areas:
            areas.append(current_area)
    return areas

def get_breeder_details(breeder: Breeder) -> BreedMembers:
    url = f"https://www.enci.it/umbraco/enci/AllevatoriApi/TakeAllevatore?idAffisso={breeder.id}"
    payload = {}
    headers = {}
    breed_members: BreedMembers = BreedMembers()
    response = requests.request("GET", url, headers=headers, data=payload, timeout=10)
    breeder_data = json.loads(response.text)
    for current_member in breeder_data["Soci"]:
        member: Member = Member(description=current_member["DesAssociato"],
                                id=current_member["IdAnagrafica"],
                                signatory=True if current_member["FlagFirmatario"]=="S" else False,
                                address=current_member["DesIndirizzoSocio"],
                                town=current_member["DesLocalitaSocio"],
                                breeder_ids=[breeder.id])
        
        if member not in breed_members.members:
            breed_members.members.append(member)
    for current_breed in breeder_data["Razze"]:
        new_breed: Breed = Breed(code=current_breed["CodRazza"],
                                 id=current_breed["IdUmb"],
                                 last_litter=current_breed["UltimaCucciolata"],
                                 description=current_breed["DesRazza"],
                                 group_code=current_breed["CodGruppo"],
                                 group_description=current_breed["DesGruppo"])
        if new_breed not in breed_members.breeds:
            breed_members.breeds.append(new_breed)
    return breed_members

def get_breeders(area:Area) -> list[Breeder]:
    url = "https://www.enci.it/umbraco/enci/AllevatoriApi/GetAllevatori"
    payload = "{\"regioniAttive\":[\""+area.region+"\"],\"filtroRazze\":[]}"
    headers = {
    'Content-Type': 'application/json;charset=utf-8'
    }
    response: requests.Response = requests.request("POST", url, headers=headers, data=payload)
    breeder_data = json.loads(response.text)
    breeders: list[Breeder] = []
    for current_breeder in breeder_data:
        breeder: Breeder = Breeder(title=current_breeder["DesAffisso"], 
                                   owner=current_breeder["Proprietario"], 
                                   id=current_breeder["IdAffisso"], 
                                   area_region=area.region,
                                   breeds=[breed_code for breed_code in current_breeder["Razze"]])
        if breeder not in breeders:
            breeders.append(breeder)
            print(f"\t-Breeder ({breeder.id}){breeder.title} added.")
    return breeders

def scrape_area(area: Area) -> list[Breeder]:
    breeders: list[Breeder] = get_breeders(area)
    print(f"Area ({area.region}){area.title} scraped.")
    return breeders

def display_progress(start_time: float, percentage_complete: float, 
                     completed_breeders: int, total_breeders: int):
    sec = time.time()-start_time
    title = f'{completed_breeders}/{total_breeders} - ({percentage_complete}% {sec//60:02.0f}:{sec%60:02.0f}) '
    bar_width = 20
    full_width = int(bar_width*percentage_complete/100.0)
    empty_width = bar_width - full_width
    sys.stdout.write('\r'+'['+full_width*'#'+empty_width*'.'+'] '+title)
    sys.stdout.flush()

def request_breeder_details(breeder: Breeder, total_breeders: int, completed_breeders: Counter, paused_process_count: Counter, wait_time: float, start_time: float) -> BreedMembers:
    time.sleep(wait_time)
    breed_members: BreedMembers = None
    completed: bool = False
    while not completed:
        try:
            if paused_process_count.value > 10:
                time.sleep(5.0)
            breed_members = get_breeder_details(breeder)
            completed = True
        except Exception as e:
            print(f"({breeder.id})Error: {e} - Retrying in 7.3-11.48 seconds.")
            paused_process_count.increment()
            time.sleep(np.random.uniform(7.3,11.48))
            paused_process_count.decrement()
    completed_breeders.increment()
    percentage = round((float(completed_breeders.value)/float(total_breeders))*100.0, 1)
    display_progress(start_time=start_time,percentage_complete=percentage, 
                     completed_breeders=completed_breeders.value, total_breeders=total_breeders)
    return breed_members