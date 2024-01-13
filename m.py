import requests
from bs4 import BeautifulSoup
import json
from multiprocessing import Pool, Manager
import os
import time
import numpy as np
from models import *
from database import Database
        
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

def add_to_database(db: Database, areas: list[Area], breeders: list[Breeder], members: list[Member], breeds: list[Breed]) -> bool:
    for area in areas:
        db.cursor.execute("INSERT OR IGNORE INTO areas VALUES (?,?)", (area.title, area.region))
    for breeder in breeders:
        db.cursor.execute("INSERT OR IGNORE INTO breeders VALUES (?,?,?)", (breeder.title, breeder.owner, breeder.id))
    for breed in breeds:
        db.cursor.execute("INSERT OR IGNORE INTO breeds VALUES (?,?,?,?,?,?)", (breed.code, breed.id, breed.last_litter, breed.description, breed.group_code, breed.group_description))
    for member in members:
        db.cursor.execute("INSERT OR IGNORE INTO members VALUES (?,?,?,?,?)", (member.description, member.id, member.signatory, member.address, member.town))
    for breeder in breeders:
        db.cursor.execute("INSERT OR IGNORE INTO areas_breeders VALUES (?,?)", (breeder.area_region, breeder.id))
        for breed_code in breeder.breeds:
            db.cursor.execute("INSERT OR IGNORE INTO breeders_breeds VALUES (?,?)", (breeder.id, breed_code))
    for member in members:
        for breeder_id in member.breeder_ids:
            db.cursor.execute("INSERT OR IGNORE INTO breeders_members VALUES (?,?)", (breeder_id, member.id))
    db.connection.commit()
    return True

def scrape_area(area: Area) -> list[Breeder]:
    breeders: list[Breeder] = get_breeders(area)
    print(f"Area ({area.region}){area.title} scraped.")
    return breeders

def request_breeder_details(breeder: Breeder, total_breeders: int, completed_breeders: Counter, paused_process_count: Counter,wait_time: float) -> BreedMembers:
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
    percentage = round((float(completed_breeders.value)/float(total_breeders))*100.0, 4)
    print(f"({completed_breeders.value}/{total_breeders}) - {percentage}%")
    return breed_members

if __name__ == "__main__":
    db: Database = Database()
    areas: list[Area] = get_areas()
    pool: Pool = Pool(os.cpu_count())
    breeders: list[Breeder] = pool.starmap(scrape_area, [(area,) for area in areas])
    breeders: list[Breeder] = [breeder for breeder_list in breeders for breeder in breeder_list]
    print("All breeders scraped.")
    print(f"Starting to retrieve breeder details for {len(breeders)} breeders.")
    total_breeder_count = len(breeders)
    manager: Manager = Manager()
    completed_processes = Counter(manager,0)
    paused_process_count = Counter(manager,0)
    pool: Pool = Pool(os.cpu_count())
    pooled_breed_members: list[BreedMembers] = pool.starmap(request_breeder_details, [(breeder, total_breeder_count, completed_processes, paused_process_count,np.random.uniform(0.03,0.43)) for breeder in breeders])
    print("All breeders details retrieved.")
    members: dict[str, Member] = {}
    breeds: list[str, Breed] = {}
    for breed_members in pooled_breed_members:
        for member in breed_members.members:
            if member.id not in members:
                members[member.id] = member
            else:
                for breeder_id in member.breeder_ids:
                    if breeder_id not in members[member.id].breeder_ids:
                        members[member.id].breeder_ids.append(breeder_id)
        for breed in breed_members.breeds:
            if breed.code not in breeds:
                breeds[breed.code] = breed
    members: list[Member] = list(members.values())
    breeds: list[Breed] = list(breeds.values())
    print("All breeders details added to breeders.")
    print(f"{completed_processes.value} breeders completed / {total_breeder_count} breeders total.")
    print("Starting to add all breeders to database.")
    add_to_database(db, areas, breeders, members, breeds)
    print("All breeders added to database.")

    