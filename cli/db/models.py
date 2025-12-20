from datetime import datetime
from typing import Optional, List
from sqlmodel import Field, SQLModel, Relationship

class Project(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, unique=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    templates: List["Template"] = Relationship(back_populates="project", cascade_delete=True)
    recipes: List["Recipe"] = Relationship(back_populates="project", cascade_delete=True)
    assets: List["Asset"] = Relationship(back_populates="project", cascade_delete=True)
    default_recipe: Optional[str] = Field(default=None)

class Template(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    content: str
    project_id: Optional[int] = Field(default=None, foreign_key="project.id", nullable=True)
    
    project: Optional[Project] = Relationship(back_populates="templates")

class Recipe(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    content: str
    project_id: Optional[int] = Field(default=None, foreign_key="project.id", nullable=True)
    
    project: Optional[Project] = Relationship(back_populates="recipes")

class Asset(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    source_path: str
    content: bytes
    project_id: Optional[int] = Field(default=None, foreign_key="project.id", nullable=True)
    
    project: Optional[Project] = Relationship(back_populates="assets")
