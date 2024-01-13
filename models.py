class Breed:
    """
    Represents a breed of dog.
    """
    code: str
    id: str
    last_litter: str
    description: str
    group_code: str
    group_description: str
    def __init__(self, code:str, id:str, last_litter:str, description:str, group_code:str, group_description:str):
        self.code = code
        self.id = id
        self.last_litter = last_litter
        self.description = description
        self.group_code = group_code
        self.group_description = group_description
    def __str__(self):
        return f"{self.code}-{self.id}-{self.last_litter}-{self.description}-{self.group_code}-{self.group_description}"
    def __repr__(self):
        return Breed.__str__(self)
    
class Member:
    """
    Represents a member of ENCI.
    """
    description: str
    id: str
    signatory: bool
    address: str
    town: str
    breeder_ids: list[str]
    def __init__(self, description: str, id: str, signatory: bool, address: str, town: str, breeder_ids: list[str] = []):
        self.description = description
        self.id = id
        self.signatory = signatory
        self.address = address
        self.town = town
        self.breeder_ids = breeder_ids
    def __str__(self):
        return f"{self.description}-{self.id}-{self.signatory}-{self.address}-{self.town}"
    def __repr__(self):
        return Member.__str__(self)
    def __hash__(self) -> int:
        return hash(self.id)
    def __eq__(self, __value: object) -> bool:
        return self.id == __value.id
    

class Breeder:
    """
    Represents a breeder of dogs.
    """
    title: str
    owner: str
    id: str
    area_region: str
    breeds: list[str] #breed codes only
    members: list[str] #member ids only
    def __init__(self, title: str, owner: str, id: str, area_region:str, breeds: list[str] = [], members: list[str] = []):
        self.title = title
        self.owner = owner
        self.id = id
        self.area_region = area_region
        self.breeds = breeds
        self.members = members
    def __hash__(self) -> int:
        return hash(self.id)
    def __eq__(self, __value: object) -> bool:
        return self.id == __value.id
    def __str__(self):
        return f"({self.title}){self.owner}-{self.breeds}-{self.id}"
    def __repr__(self):
        return Breeder.__str__(self)
    @staticmethod
    def get_key(obj)->int:
        return int(obj.id)

class Area:
    """
    Represents an area of Italy.
    """
    title: str
    region: str
    breeders: list[Breeder]
    def __init__(self, title, region):
        self.title = title
        self.region = region
        self.breeders = []
    def __str__(self):
        return f"({self.region}){self.title}"
    def __repr__(self):
        return Area.__str__(self)
    def __hash__(self) -> int:
        return hash(self.title, self.region)
    def __eq__(self, o: object) -> bool:
        return self.title == o.title and self.region == o.region
    
class BreedMembers:
    """
    Represents the members and breeds of a breeder.
    """
    breeds: list[Breed]
    members: list[Member]
    def __init__(self, breeds: list[Breed] = [], members: list[Member] = []):
        self.breeds = breeds
        self.members = members