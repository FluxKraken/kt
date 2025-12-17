import os
import json
import tarfile
import tempfile
import shutil
from cli.db.session import get_session
from cli.db.models import Project, Template, Recipe, Asset
from sqlmodel import select

def create_bundle(project_name: str, output_path: str, overwrite: bool = False):
    """
    Export a project and its resources to a .project tarball.
    Structure:
    /project.json
    /templates/name
    /recipes/name.lua
    /assets/name
    """
    if os.path.exists(output_path) and not overwrite:
        raise FileExistsError(f"Output file '{output_path}' exists.")
        
    with get_session() as session:
        proj = session.exec(select(Project).where(Project.name == project_name)).first()
        if not proj:
            raise ValueError(f"Project '{project_name}' not found.")
            
        with tempfile.TemporaryDirectory() as tmpdir:
            # Metadata
            meta = {
                "name": proj.name,
                "created_at": str(proj.created_at)
            }
            with open(os.path.join(tmpdir, "project.json"), 'w') as f:
                json.dump(meta, f)
                
            # Templates
            tmpl_dir = os.path.join(tmpdir, "templates")
            os.makedirs(tmpl_dir)
            
            recipes_dir = os.path.join(tmpdir, "recipes")
            os.makedirs(recipes_dir)
            
            assets_dir = os.path.join(tmpdir, "assets")
            os.makedirs(assets_dir)
            
            # Export Templates
            templates = session.exec(select(Template).where(Template.project_id == proj.id)).all()
            for t in templates:
                # Sanitize filename? assume name is safe or simple
                # Template content is string
                with open(os.path.join(tmpl_dir, t.name), 'w') as f:
                    f.write(t.content)
                    
            # Export Recipes
            recipes = session.exec(select(Recipe).where(Recipe.project_id == proj.id)).all()
            for r in recipes:
                # Add .lua extension if missing for clarity? Or keep exact name. 
                # User asks "name", assuming name is identifier.
                fname = r.name + ".lua" if not r.name.endswith(".lua") else r.name
                # Be careful on import to map back to 'name'
                # Let's save metadata about mapping? 
                # Or just use filename as name.
                with open(os.path.join(recipes_dir, fname), 'w') as f:
                    f.write(r.content)
            
            # Export Assets
            assets = session.exec(select(Asset).where(Asset.project_id == proj.id)).all()
            for a in assets:
                 with open(os.path.join(assets_dir, a.name), 'wb') as f:
                     f.write(a.content)
                     
            # Create Tarball
            with tarfile.open(output_path, "w:gz") as tar:
                tar.add(tmpdir, arcname=os.path.basename(project_name))

def extract_bundle(bundle_path: str, overwrite: bool = False):
    """
    Import a project from a .project tarball.
    """
    if not os.path.exists(bundle_path):
        raise FileNotFoundError(f"Bundle '{bundle_path}' not found.")
        
    with tempfile.TemporaryDirectory() as tmpdir:
        with tarfile.open(bundle_path, "r:gz") as tar:
            tar.extractall(path=tmpdir)
            
        # Find root folder (likely named after project)
        # We need to find 'project.json'
        # Since we tarred 'tmpdir' as arcname=project_name, it's inside a folder.
        root_dir = None
        for item in os.listdir(tmpdir):
            if os.path.isdir(os.path.join(tmpdir, item)):
                if os.path.exists(os.path.join(tmpdir, item, "project.json")):
                    root_dir = os.path.join(tmpdir, item)
                    break
        
        if not root_dir:
             # Try root of tmpdir
             if os.path.exists(os.path.join(tmpdir, "project.json")):
                 root_dir = tmpdir
             else:
                 raise ValueError("Invalid bundle: project.json not found.")
                 
        with open(os.path.join(root_dir, "project.json"), 'r') as f:
            meta = json.load(f)
            
        project_name = meta['name']
        
        with get_session() as session:
            # Check project existence
            existing = session.exec(select(Project).where(Project.name == project_name)).first()
            if existing:
                if not overwrite:
                    raise FileExistsError(f"Project '{project_name}' already exists.")
                # We reuse existing project ID? or delete/recreate?
                # User said "overwrite".
                # Let's keep ID but clear resources?
                # Actually, simpler to verify logic: 
                # If "import path --overwrite", we might merge or replace?
                pass
            else:
                existing = Project(name=project_name)
                session.add(existing)
                session.commit()
                # Reload to get ID
                existing = session.exec(select(Project).where(Project.name == project_name)).first()
                
            project_id = existing.id
            
            # Import Templates
            tmpl_dir = os.path.join(root_dir, "templates")
            if os.path.exists(tmpl_dir):
                for fname in os.listdir(tmpl_dir):
                    fpath = os.path.join(tmpl_dir, fname)
                    with open(fpath, 'r') as f:
                        content = f.read()
                    
                    # Update or Create
                    t = session.exec(select(Template).where(Template.name == fname).where(Template.project_id == project_id)).first()
                    if t:
                        if overwrite:
                            t.content = content
                            session.add(t)
                    else:
                        t = Template(name=fname, content=content, project_id=project_id)
                        session.add(t)
                        
            # Import Recipes
            recipes_dir = os.path.join(root_dir, "recipes")
            if os.path.exists(recipes_dir):
                for fname in os.listdir(recipes_dir):
                    fpath = os.path.join(recipes_dir, fname)
                    with open(fpath, 'r') as f:
                        content = f.read()
                    
                    # Strip .lua for name if we added it
                    rec_name = fname[:-4] if fname.endswith(".lua") else fname
                    
                    r = session.exec(select(Recipe).where(Recipe.name == rec_name).where(Recipe.project_id == project_id)).first()
                    if r:
                        if overwrite:
                            r.content = content
                            session.add(r)
                    else:
                        r = Recipe(name=rec_name, content=content, project_id=project_id)
                        session.add(r)
                        
            # Import Assets
            assets_dir = os.path.join(root_dir, "assets")
            if os.path.exists(assets_dir):
                for fname in os.listdir(assets_dir):
                    fpath = os.path.join(assets_dir, fname)
                    with open(fpath, 'rb') as f:
                         content = f.read()
                    
                    a = session.exec(select(Asset).where(Asset.name == fname).where(Asset.project_id == project_id)).first()
                    if a:
                        if overwrite:
                            a.content = content
                            session.add(a)
                    else:
                        # source_path is lost in bundle, set to "imported"
                        a = Asset(name=fname, source_path="imported", content=content, project_id=project_id)
                        session.add(a)
                        
            session.commit()
