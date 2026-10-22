"""Allowlisted demo master fields; unit transfers use their existing dedicated flow."""
from datetime import date
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class MasterInput(BaseModel):
    model_config=ConfigDict(extra="forbid", str_strip_whitespace=True, allow_inf_nan=False)


class UnitCreate(MasterInput):
    unit_code:str=Field(min_length=1,max_length=50)
    unit_name:str=Field(min_length=1,max_length=150)
    unit_type:str=Field(min_length=1,max_length=80)
    parent_unit_id:UUID|None=None
    location_label:str|None=Field(default=None,max_length=150)
    sanctioned_strength:int=Field(ge=0)
    is_active:bool=True


class UnitPatch(MasterInput):
    expected_revision:str=Field(pattern=r"^[a-f0-9]{64}$")
    unit_code:str|None=Field(default=None,min_length=1,max_length=50)
    unit_name:str|None=Field(default=None,min_length=1,max_length=150)
    unit_type:str|None=Field(default=None,min_length=1,max_length=80)
    parent_unit_id:UUID|None=None
    location_label:str|None=Field(default=None,max_length=150)
    sanctioned_strength:int|None=Field(default=None,ge=0)
    is_active:bool|None=None


class PersonnelCreate(MasterInput):
    personnel_code:str=Field(min_length=1,max_length=50)
    pseudo_id:str=Field(min_length=1,max_length=50)
    full_name:str=Field(min_length=1,max_length=150)
    unit_id:UUID
    rank_or_grade:str=Field(min_length=1,max_length=80)
    role_title:str=Field(min_length=1,max_length=100)
    status:str=Field(default="ACTIVE",min_length=1,max_length=40,pattern=r"^[A-Z_]+$")
    joining_date:date|None=None
    service_years:float|None=Field(default=None,ge=0)


class PersonnelPatch(MasterInput):
    expected_revision:str=Field(pattern=r"^[a-f0-9]{64}$")
    personnel_code:str|None=Field(default=None,min_length=1,max_length=50)
    pseudo_id:str|None=Field(default=None,min_length=1,max_length=50)
    full_name:str|None=Field(default=None,min_length=1,max_length=150)
    rank_or_grade:str|None=Field(default=None,min_length=1,max_length=80)
    role_title:str|None=Field(default=None,min_length=1,max_length=100)
    status:str|None=Field(default=None,min_length=1,max_length=40,pattern=r"^[A-Z_]+$")
    joining_date:date|None=None
    service_years:float|None=Field(default=None,ge=0)


class SkillCreate(MasterInput):
    skill_code:str=Field(min_length=1,max_length=50)
    skill_name:str=Field(min_length=1,max_length=120)
    category:str|None=Field(default=None,max_length=80)
    is_active:bool=True


class PersonSkillInput(MasterInput):
    skill_id:UUID
    proficiency_level:int=Field(ge=1,le=5)
    valid_from:date
    valid_until:date|None=None


class PostingInput(MasterInput):
    unit_id:UUID
    posting_start_date:date
    posting_end_date:date|None=None
    posting_type:str=Field(min_length=1,max_length=80)
    location_label:str|None=Field(default=None,max_length=150)
    hardship_level:int|None=Field(default=None,ge=1,le=5)
