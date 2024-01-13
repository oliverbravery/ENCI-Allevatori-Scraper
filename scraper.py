from models import *
import requests
from bs4 import BeautifulSoup
import json
import time
import numpy as np
from Progress import *

def get_areas() -> list[Area]:
    """
    Gets the areas of Italy from the ENCI website.

    Returns:
        list[Area]: A list of Area objects.
    """
    URL:str = f"https://www.enci.it/allevatori/allevatori-con-affisso?codRegione=PIE"
    # request the page
    page:requests.Response = requests.get(URL)
    soup:BeautifulSoup = BeautifulSoup(page.content, "html.parser")
    # find the map element
    map = soup.find("map", {"name": "ENCI_italia_Map"})
    area_tags = map.find_all("area")
    areas: list[Area] = []
    # create an Area object for each area tag
    for a in area_tags:
        current_area = Area(a["title"], a["data-regione"])
        if current_area not in areas:
            areas.append(current_area)
    return areas

def get_breeder_details(breeder: Breeder) -> BreedMembers:
    """
    Gets the members and breeds of a breeder from the ENCI website.

    Args:
        breeder (Breeder): The breeder to get the details of.

    Returns:
        BreedMembers: A BreedMembers object containing the members and breeds of the breeder.
    """
    url:str = f"https://www.enci.it/umbraco/enci/AllevatoriApi/TakeAllevatore?idAffisso={breeder.id}"
    payload:dict = {}
    headers:dict = {}
    breed_members: BreedMembers = BreedMembers()
    # request the page
    response = requests.request("GET", url, headers=headers, data=payload, timeout=10)
    breeder_data = json.loads(response.text)
    # instantiate a Member object for each member of the breeder
    for current_member in breeder_data["Soci"]:
        member: Member = Member(description=current_member["DesAssociato"],
                                id=current_member["IdAnagrafica"],
                                signatory=True if current_member["FlagFirmatario"]=="S" else False,
                                address=current_member["DesIndirizzoSocio"],
                                town=current_member["DesLocalitaSocio"],
                                breeder_ids=[breeder.id])
        # add the member to the BreedMembers object if they are not already in it
        if member not in breed_members.members:
            breed_members.members.append(member)
    # instantiate a Breed object for each breed of the breeder
    for current_breed in breeder_data["Razze"]:
        new_breed: Breed = Breed(code=current_breed["CodRazza"],
                                 id=current_breed["IdUmb"],
                                 last_litter=current_breed["UltimaCucciolata"],
                                 description=current_breed["DesRazza"],
                                 group_code=current_breed["CodGruppo"],
                                 group_description=current_breed["DesGruppo"])
        # add the breed to the BreedMembers object if it is not already in it
        if new_breed not in breed_members.breeds:
            breed_members.breeds.append(new_breed)
    return breed_members

def get_breeders(area:Area) -> list[Breeder]:
    """
    Gets the breeders in the specified area.

    Args:
        area (Area): The area to get the breeders from.

    Returns:
        list[Breeder]: A list of Breeder objects where the breeders belong to the specified area.
    """
    url:str = "https://www.enci.it/umbraco/enci/AllevatoriApi/GetAllevatori"
    payload:str = "{\"regioniAttive\":[\""+area.region+"\"],\"filtroRazze\":[]}"
    headers:dict[str:any] = {
    'Content-Type': 'application/json;charset=utf-8'
    }
    # request the page
    response: requests.Response = requests.request("POST", url, headers=headers, data=payload)
    breeder_data = json.loads(response.text)
    breeders: list[Breeder] = []
    # instantiate a Breeder object for each breeder in the area
    for current_breeder in breeder_data:
        breeder: Breeder = Breeder(title=current_breeder["DesAffisso"], 
                                   owner=current_breeder["Proprietario"], 
                                   id=current_breeder["IdAffisso"], 
                                   area_region=area.region,
                                   breeds=[breed_code for breed_code in current_breeder["Razze"]])
        # add the breeder to the list if they are not already in it
        if breeder not in breeders:
            breeders.append(breeder)
    return breeders

def scrape_area(area: Area, progress: Progress) -> list[Breeder]:
    """
    Wraps the get_breeders function to allow for tracking progress accross processes.

    Args:
        area (Area): The area to get the breeders from.
        progress (Progress): The progress tracker object.

    Returns:
        list[Breeder]: A list of Breeder objects where the breeders belong to the specified area.
    """
    # get the breeders in the area
    breeders: list[Breeder] = get_breeders(area)
    # increment the amount of completed tasks and display the progress
    progress.increment_amount_completed()
    progress.display_progress()
    return breeders

def request_breeder_details(breeder: Breeder, paused_process_count: Counter, wait_time: float, progress: Progress) -> BreedMembers:
    """
    Wraps the get_breeder_details function to allow for tracking progress accross processes. 
    Handles errors and retries so that the program does not crash upon a failed request.

    Args:
        breeder (Breeder): The breeder to get the details of.
        paused_process_count (Counter): The counter for tracking the number of paused processes.
        wait_time (float): The amount of time to wait before retrying the request.
        progress (Progress): The progress tracker object.

    Returns:
        BreedMembers: A BreedMembers object containing the members and breeds of the breeder.
    """
    # wait for a random amount of time to avoid overloading the server
    time.sleep(wait_time)
    breed_members: BreedMembers = None
    completed: bool = False
    # keep retrying until the request is successful
    while not completed:
        # try to get the breeder details
        try:
            # if there are more than 10 paused processes, wait for 5 seconds to prevent overloading the server
            if paused_process_count.value > 10:
                time.sleep(5.0)
            # get the breeder details
            breed_members = get_breeder_details(breeder)
            completed = True
        # if there is an error, wait for a random amount of time and retry
        except Exception as e:
            print(f"({breeder.id})Error: {e} - Retrying in 7.3-11.48 seconds.")
            # increment the paused process count and wait for a random amount of time
            paused_process_count.increment()
            time.sleep(np.random.uniform(7.3,11.48))
            paused_process_count.decrement()
    # increment the amount of completed tasks and display the progress
    progress.increment_amount_completed()
    progress.display_progress()
    return breed_members